import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from scipy.optimize import linprog
from stream_engine.config import settings

class ModelPredictiveController:
    """
    Industrial Model Predictive Control (MPC) Engine for BESS.
    Solves a rolling 4-hour forward-looking optimization horizon (16 intervals of 15 min)
    balancing multi-quantile forecasts, day-ahead tariffs, grid deviation penalties,
    and lithium-ion battery degradation throughput costs.
    """
    def __init__(
        self,
        capacity_kwh: float = 10000.0,      # 10 MWh
        max_power_kw: float = 5000.0,        # 5 MW
        min_soc_pct: float = 10.0,
        max_soc_pct: float = 90.0,
        roundtrip_efficiency: float = 0.92,
        penalty_rate_usd_kwh: float = 0.075,
        degradation_cost_usd_kwh: float = 0.022, # $22/MWh cell degradation
        horizon_intervals: int = 16,        # 4 hours at 15m intervals
        interval_hours: float = 0.25        # 15 minutes = 0.25 h
    ):
        self.capacity_kwh = capacity_kwh
        self.max_power_kw = max_power_kw
        self.min_soc_pct = min_soc_pct
        self.max_soc_pct = max_soc_pct
        self.eta_chg = math.sqrt(roundtrip_efficiency)
        self.eta_dis = math.sqrt(roundtrip_efficiency)
        self.penalty_rate = penalty_rate_usd_kwh
        self.deg_cost = degradation_cost_usd_kwh
        self.T = horizon_intervals
        self.dt = interval_hours

    def _get_tariff(self, hour: float) -> float:
        if 14.0 <= hour < 19.0:
            return 0.32  # Peak ($/kWh)
        elif (7.0 <= hour < 14.0) or (19.0 <= hour < 22.0):
            return 0.14  # Shoulder ($/kWh)
        else:
            return 0.06  # Off-Peak ($/kWh)

    def _get_schedule(self, hour: float) -> float:
        if 6.0 <= hour <= 18.5:
            solar = 17500.0 * math.sin(math.pi * (hour - 6.0) / 12.5)
            return round(max(0.0, solar + 2800.0), 2)
        return 2800.0

    def optimize_4h_horizon(
        self,
        start_time: datetime,
        current_soc_pct: float,
        current_forecast_p50_kw: float
    ) -> Dict[str, Any]:
        """
        Solves the 16-step forward-looking MPC problem.
        Variables per step t:
          x[0*T + t]: P_dis[t] >= 0 (Discharge power kW)
          x[1*T + t]: P_chg[t] >= 0 (Charge power kW)
          x[2*T + t]: Shortfall[t] >= 0 (Unexcused generation deficit kW)
          x[3*T + t]: Surplus[t] >= 0 (Unexcused generation surplus kW)
        Total variables = 4 * T = 64 variables.
        """
        T = self.T
        dt = self.dt
        n_vars = 4 * T

        # Forward generation forecasts, schedules, and tariffs over 4 hours
        time_steps = []
        forecasts_kw = []
        schedules_kw = []
        tariffs = []

        start_hour = start_time.hour + start_time.minute / 60.0
        for step in range(T):
            t_dt = start_time + timedelta(minutes=step * 15)
            h = (start_hour + step * dt) % 24.0
            time_steps.append(t_dt)
            
            # Simulated forward curve based on diurnal cycle
            if 6.0 <= h <= 18.5:
                solar_est = 18000.0 * math.sin(math.pi * (h - 6.0) / 12.5)
                gen_kw = max(0.0, solar_est) + 2600.0
            else:
                gen_kw = 2600.0
            
            # Blend current live forecast into step 0
            if step == 0:
                gen_kw = current_forecast_p50_kw

            forecasts_kw.append(gen_kw)
            schedules_kw.append(self._get_schedule(h))
            tariffs.append(self._get_tariff(h))

        # Objective Function: MINIMIZE Cost (Negative Revenue + Penalties + Degradation)
        # Cost = - sum( P_inj * Tariff * dt ) + sum( Penalty * dt ) + sum( Deg * (P_dis + P_chg) * dt )
        # where P_inj = P_ren + P_dis - P_chg
        # So coeff for P_dis[t] = - Tariff[t]*dt + Deg*dt
        # coeff for P_chg[t] = + Tariff[t]*dt + Deg*dt
        # coeff for Shortfall[t] = PenaltyRate * dt
        # coeff for Surplus[t] = PenaltyRate * dt
        c = np.zeros(n_vars)
        for t in range(T):
            c[0*T + t] = - tariffs[t] * dt + self.deg_cost * dt  # P_dis
            c[1*T + t] = + tariffs[t] * dt + self.deg_cost * dt  # P_chg
            c[2*T + t] = self.penalty_rate * dt                  # Shortfall penalty
            c[3*T + t] = self.penalty_rate * dt                  # Surplus penalty

        # Bounds:
        # 0 <= P_dis <= max_power_kw
        # 0 <= P_chg <= max_power_kw
        # 0 <= Shortfall <= 25000
        # 0 <= Surplus <= 25000
        bounds = []
        for t in range(T):
            bounds.append((0, self.max_power_kw))
        for t in range(T):
            bounds.append((0, self.max_power_kw))
        for t in range(T):
            bounds.append((0, 25000.0))
        for t in range(T):
            bounds.append((0, 25000.0))

        # Inequality Constraints A_ub * x <= b_ub:
        # 1. State of Charge upper and lower bounds for each cumulative step:
        # E(t) = E_init - sum_{i=0}^t [ P_dis[i]*dt / eta_dis - P_chg[i]*dt * eta_chg ]
        # E(t) <= E_max  -->  - sum(P_dis/eta_dis) + sum(P_chg * eta_chg) <= (E_max - E_init) / dt
        # E(t) >= E_min  -->  sum(P_dis/eta_dis) - sum(P_chg * eta_chg) <= (E_init - E_min) / dt
        E_init = (current_soc_pct / 100.0) * self.capacity_kwh
        E_max = (self.max_soc_pct / 100.0) * self.capacity_kwh
        E_min = (self.min_soc_pct / 100.0) * self.capacity_kwh

        A_ub = []
        b_ub = []

        for t in range(T):
            # Upper bound: E(t) <= E_max
            row_max = np.zeros(n_vars)
            for i in range(t + 1):
                row_max[0*T + i] = - (dt / self.eta_dis)
                row_max[1*T + i] = + (dt * self.eta_chg)
            A_ub.append(row_max)
            b_ub.append(E_max - E_init)

            # Lower bound: E(t) >= E_min  => -E(t) <= -E_min
            row_min = np.zeros(n_vars)
            for i in range(t + 1):
                row_min[0*T + i] = + (dt / self.eta_dis)
                row_min[1*T + i] = - (dt * self.eta_chg)
            A_ub.append(row_min)
            b_ub.append(E_init - E_min)

            # Substation Injection Limit: P_inj <= 25000
            # P_ren + P_dis - P_chg <= 25000  => P_dis - P_chg <= 25000 - P_ren
            row_inj = np.zeros(n_vars)
            row_inj[0*T + t] = 1.0
            row_inj[1*T + t] = -1.0
            A_ub.append(row_inj)
            b_ub.append(25000.0 - forecasts_kw[t])

        # Equality Constraints A_eq * x == b_eq:
        # Grid deviation slack balance:
        # P_inj[t] + Shortfall[t] - Surplus[t] = P_sched[t]
        # (P_ren[t] + P_dis[t] - P_chg[t]) + Shortfall[t] - Surplus[t] = P_sched[t]
        # P_dis[t] - P_chg[t] + Shortfall[t] - Surplus[t] = P_sched[t] - P_ren[t]
        A_eq = []
        b_eq = []
        for t in range(T):
            row_eq = np.zeros(n_vars)
            row_eq[0*T + t] = 1.0   # P_dis
            row_eq[1*T + t] = -1.0  # P_chg
            row_eq[2*T + t] = 1.0   # Shortfall
            row_eq[3*T + t] = -1.0  # Surplus
            A_eq.append(row_eq)
            b_eq.append(schedules_kw[t] - forecasts_kw[t])

        # Solve Linear Program using HiGHS solver
        res = linprog(
            c=c,
            A_ub=np.array(A_ub),
            b_ub=np.array(b_ub),
            A_eq=np.array(A_eq),
            b_eq=np.array(b_eq),
            bounds=bounds,
            method="highs"
        )

        # Parse solution
        intervals = []
        total_projected_revenue = 0.0
        total_projected_penalties = 0.0
        total_projected_deg = 0.0

        if res.success:
            p_dis_opt = res.x[0*T : 1*T]
            p_chg_opt = res.x[1*T : 2*T]
            shortfall_opt = res.x[2*T : 3*T]
            surplus_opt = res.x[3*T : 4*T]
        else:
            # Fallback heuristic if unbounded/infeasible
            p_dis_opt = np.zeros(T)
            p_chg_opt = np.zeros(T)
            shortfall_opt = np.zeros(T)
            surplus_opt = np.zeros(T)

        e_curr = E_init
        for t in range(T):
            p_bess = p_dis_opt[t] - p_chg_opt[t]
            p_inj = max(0.0, forecasts_kw[t] + p_bess)
            
            # Update SoC
            if p_bess > 0:
                e_curr = max(E_min, e_curr - (p_bess * dt / self.eta_dis))
            else:
                e_curr = min(E_max, e_curr + (abs(p_bess) * dt * self.eta_chg))
            soc_pct = (e_curr / self.capacity_kwh) * 100.0

            rev = p_inj * tariffs[t] * dt
            pen = (shortfall_opt[t] + surplus_opt[t]) * self.penalty_rate * dt
            deg = (p_dis_opt[t] + p_chg_opt[t]) * self.deg_cost * dt

            total_projected_revenue += rev
            total_projected_penalties += pen
            total_projected_deg += deg

            intervals.append({
                "step_index": t,
                "time": time_steps[t].strftime("%H:%M"),
                "timestamp": time_steps[t].isoformat(),
                "forecast_generation_kw": round(forecasts_kw[t], 2),
                "committed_schedule_kw": round(schedules_kw[t], 2),
                "tariff_usd_kwh": round(tariffs[t], 4),
                "optimal_bess_kw": round(p_bess, 2),
                "optimal_injected_kw": round(p_inj, 2),
                "predicted_soc_pct": round(soc_pct, 1),
                "projected_revenue_usd": round(rev, 2),
                "projected_degradation_usd": round(deg, 2)
            })

        instantaneous_setpoint = intervals[0]["optimal_bess_kw"] if intervals else 0.0

        return {
            "status": "OPTIMAL" if res.success else "FALLBACK",
            "solver_message": res.message if hasattr(res, "message") else "OK",
            "horizon_hours": 4.0,
            "intervals_count": T,
            "instantaneous_setpoint_kw": instantaneous_setpoint,
            "summary": {
                "projected_revenue_usd": round(total_projected_revenue, 2),
                "projected_penalties_usd": round(total_projected_penalties, 2),
                "projected_degradation_usd": round(total_projected_deg, 2),
                "net_profit_usd": round(total_projected_revenue - total_projected_penalties - total_projected_deg, 2)
            },
            "intervals": intervals
        }

mpc_controller = ModelPredictiveController()
