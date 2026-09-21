from typing import Dict, Any

class BatteryDispatchOptimizer:
    """
    Optimizes Battery Energy Storage System (BESS) dispatch in real-time.
    Balances fluctuating renewable generation against committed grid schedules
    and dynamic time-of-use tariffs to eliminate penalties and maximize revenue.
    """
    def __init__(
        self,
        capacity_kwh: float = 10000.0,     # 10 MWh
        max_power_kw: float = 5000.0,       # 5 MW C-rate (0.5C)
        min_soc_pct: float = 10.0,
        max_soc_pct: float = 90.0,
        roundtrip_efficiency: float = 0.92,
        penalty_rate_usd_kwh: float = 0.075
    ):
        self.capacity_kwh = capacity_kwh
        self.max_power_kw = max_power_kw
        self.min_soc_pct = min_soc_pct
        self.max_soc_pct = max_soc_pct
        self.roundtrip_efficiency = roundtrip_efficiency
        self.penalty_rate_usd_kwh = penalty_rate_usd_kwh

    def optimize_dispatch(
        self,
        renewable_gen_kw: float,
        forecast_15m_kw: float,
        committed_schedule_kw: float,
        current_soc_pct: float,
        tariff_usd_kwh: float,
        deadband_pct: float = 5.0,
        time_step_hours: float = 2.0 / 3600.0,  # 2-second time step
        p90_conservative_kw: float = 0.0,
        p10_optimistic_kw: float = 0.0
    ) -> Dict[str, Any]:
        """
        Determines optimal battery power setpoint (kW) and assesses P90 shortfall risk.
        Positive = Discharging (injecting power into grid).
        Negative = Charging (absorbing power from renewables/grid).
        """
        # Shortfall risk analysis using P90 (90% exceedance level)
        risk_level = "BALANCED"
        shortfall_risk_kw = 0.0
        if committed_schedule_kw > 0 and p90_conservative_kw > 0:
            if committed_schedule_kw > p90_conservative_kw:
                shortfall_risk_kw = max(0.0, committed_schedule_kw - p90_conservative_kw)
                risk_level = "HIGH_SHORTFALL_RISK" if shortfall_risk_kw > (committed_schedule_kw * 0.10) else "MODERATE_SHORTFALL_RISK"
            elif committed_schedule_kw < p10_optimistic_kw:
                risk_level = "SURPLUS_UPSIDE"
        # Calculate available charge/discharge energy headroom
        current_kwh = (current_soc_pct / 100.0) * self.capacity_kwh
        max_kwh = (self.max_soc_pct / 100.0) * self.capacity_kwh
        min_kwh = (self.min_soc_pct / 100.0) * self.capacity_kwh
        
        available_discharge_kwh = max(0.0, current_kwh - min_kwh)
        available_charge_kwh = max(0.0, max_kwh - current_kwh)
        
        # Max instantaneous power limited by C-rate and SoC bounds
        max_discharge_kw = min(self.max_power_kw, available_discharge_kwh / max(0.0001, time_step_hours))
        max_charge_kw = min(self.max_power_kw, available_charge_kwh / max(0.0001, time_step_hours))
        
        # Deficit/Surplus relative to committed schedule
        raw_deficit_kw = committed_schedule_kw - renewable_gen_kw
        tolerance_kw = committed_schedule_kw * (deadband_pct / 100.0)
        
        battery_dispatch_kw = 0.0
        dispatch_mode = "STANDBY"
        
        # 1. Deficit Compensation (Renewables < Committed Schedule)
        if raw_deficit_kw > 0:
            # Need discharge
            needed_kw = raw_deficit_kw
            battery_dispatch_kw = min(needed_kw, max_discharge_kw)
            dispatch_mode = "DISCHARGING_DEFICIT_COMPENSATION"
            
        # 2. Surplus Absorption (Renewables > Committed Schedule)
        elif raw_deficit_kw < -tolerance_kw:
            # Over-injecting beyond tolerance deadband -> absorb into battery
            surplus_kw = abs(raw_deficit_kw)
            battery_dispatch_kw = -min(surplus_kw, max_charge_kw)
            dispatch_mode = "CHARGING_SURPLUS_ABSORPTION"
            
        # 3. Tariff Arbitrage when schedule is satisfied
        elif tariff_usd_kwh >= 0.28 and available_discharge_kwh > (self.capacity_kwh * 0.3):
            # Peak tariff: discharge discretionary power if grid capacity permits
            headroom_kw = max(0.0, 25000.0 - (renewable_gen_kw + battery_dispatch_kw))
            discretionary_kw = min(headroom_kw, max_discharge_kw * 0.4)
            battery_dispatch_kw += discretionary_kw
            dispatch_mode = "PEAK_TARIFF_ARBITRAGE"
        elif tariff_usd_kwh <= 0.07 and available_charge_kwh > (self.capacity_kwh * 0.2):
            # Off-peak tariff: top up battery
            charge_kw = min(1500.0, max_charge_kw)
            battery_dispatch_kw = -charge_kw
            dispatch_mode = "OFF_PEAK_CHARGING"

        # Final net injection into the grid
        final_injected_kw = max(0.0, renewable_gen_kw + battery_dispatch_kw)
        
        # Check if remaining deviation incurs a penalty
        final_deviation_kw = final_injected_kw - committed_schedule_kw
        is_penalty = abs(final_deviation_kw) > tolerance_kw and committed_schedule_kw > 0
        
        unexcused_deviation_kw = max(0.0, abs(final_deviation_kw) - tolerance_kw) if is_penalty else 0.0
        penalty_cost_rate_usd_h = unexcused_deviation_kw * self.penalty_rate_usd_kwh
        
        # Compute new SoC after this step
        if battery_dispatch_kw > 0:
            # Discharging
            energy_used_kwh = (battery_dispatch_kw / self.roundtrip_efficiency) * time_step_hours
            new_kwh = max(min_kwh, current_kwh - energy_used_kwh)
        else:
            # Charging
            energy_stored_kwh = (abs(battery_dispatch_kw) * self.roundtrip_efficiency) * time_step_hours
            new_kwh = min(max_kwh, current_kwh + energy_stored_kwh)
            
        updated_soc_pct = max(0.0, min(100.0, (new_kwh / self.capacity_kwh) * 100.0))
        
        # Financial benefit from avoiding penalty
        raw_penalty_rate_usd_h = max(0.0, abs(raw_deficit_kw) - tolerance_kw) * self.penalty_rate_usd_kwh
        penalty_avoided_usd_h = max(0.0, raw_penalty_rate_usd_h - penalty_cost_rate_usd_h)
        revenue_rate_usd_h = (final_injected_kw * tariff_usd_kwh) - penalty_cost_rate_usd_h
        
        return {
            "battery_dispatch_kw": round(battery_dispatch_kw, 2),
            "final_injected_kw": round(final_injected_kw, 2),
            "deviation_kw": round(final_deviation_kw, 2),
            "dispatch_mode": dispatch_mode,
            "is_penalty": is_penalty,
            "penalty_cost_rate_usd_h": round(penalty_cost_rate_usd_h, 2),
            "penalty_avoided_usd_h": round(penalty_avoided_usd_h, 2),
            "revenue_rate_usd_h": round(revenue_rate_usd_h, 2),
            "updated_soc_pct": round(updated_soc_pct, 2),
            "available_discharge_kw": round(max_discharge_kw, 2),
            "available_charge_kw": round(max_charge_kw, 2),
            "risk_level": risk_level,
            "shortfall_risk_kw": round(shortfall_risk_kw, 2)
        }
