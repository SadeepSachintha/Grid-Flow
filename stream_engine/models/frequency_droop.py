import math
import random
from datetime import datetime
from typing import Dict, Any, List

class FrequencyDroopEngine:
    """
    Fast Frequency Response (FFR), Synthetic Inertia & Primary Droop Control Engine.
    Models grid frequency dynamics (nominal 60.00 Hz for WECC/CAISO) and calculates
    BESS sub-second frequency containment reserves (FCR) and synthetic inertia.
    
    Grid Code Parameters:
    - Nominal Frequency (f0): 60.00 Hz
    - Governor Deadband: +/- 0.03 Hz ([59.97 Hz, 60.03 Hz])
    - Synthetic Inertia Constant (H): 4.5 seconds
    - Droop Slope (s): 4.0% (0.04)
    - Critical FFR Threshold: 59.80 Hz (triggers max 5,000 kW burst)
    - Over-Frequency Curtailment/Charge Threshold: 60.20 Hz
    - Ancillary Market Rate: $38.50 / MW-h capacity reservation + $0.045 / delta-MW mileage
    """
    def __init__(self, f0: float = 60.00, rated_power_kw: float = 5000.0, droop_s: float = 0.04, h_constant_s: float = 4.5):
        self.f0 = f0
        self.rated_power_kw = rated_power_kw
        self.droop_s = droop_s
        self.h_constant_s = h_constant_s
        self.deadband_hz = 0.03
        self.ffr_threshold_hz = 59.80
        
        # State
        self.current_freq_hz = 60.000
        self.previous_freq_hz = 60.000
        self.rocof_hz_s = 0.0
        self.accumulated_ancillary_usd = 1240.50
        
        # Disturbance State
        self.active_event = None  # None | "GENERATOR_TRIP" | "LOAD_SHED"
        self.event_remaining_sec = 0.0
        self.event_nadir_hz = 60.000

    def trigger_generator_trip(self, loss_mw: float = 1200.0):
        """
        Simulates a major thermal/nuclear generator trip (1,200 MW loss) on the grid.
        Causes a steep frequency drop to ~59.68 Hz with a -0.45 Hz/s RoCoF nadir.
        """
        self.active_event = "GENERATOR_TRIP"
        self.event_remaining_sec = 24.0
        self.event_nadir_hz = 59.680
        self.current_freq_hz = 59.720
        self.rocof_hz_s = -0.450

    def trigger_load_shed(self, load_mw: float = 800.0):
        """
        Simulates sudden transmission line trip or industrial load rejection.
        Causes an over-frequency surge up to ~60.32 Hz with a +0.35 Hz/s RoCoF.
        """
        self.active_event = "LOAD_SHED"
        self.event_remaining_sec = 20.0
        self.event_nadir_hz = 60.320
        self.current_freq_hz = 60.280
        self.rocof_hz_s = 0.350

    def reset_frequency(self):
        """Restores nominal grid frequency conditions."""
        self.active_event = None
        self.event_remaining_sec = 0.0
        self.current_freq_hz = 60.000
        self.previous_freq_hz = 60.000
        self.rocof_hz_s = 0.0

    def update(self, dt_seconds: float = 2.0) -> Dict[str, Any]:
        """
        Advances frequency dynamics and computes synthetic inertia, droop response,
        and FFR burst setpoints.
        """
        self.previous_freq_hz = self.current_freq_hz

        if self.active_event == "GENERATOR_TRIP":
            self.event_remaining_sec -= dt_seconds
            if self.event_remaining_sec > 16.0:
                # Plunging to nadir
                self.current_freq_hz = max(self.event_nadir_hz, self.current_freq_hz - 0.04 * dt_seconds)
            else:
                # Secondary governor and FFR recovery back towards 60.00 Hz
                recovery_step = (60.000 - self.current_freq_hz) * 0.25 * dt_seconds
                self.current_freq_hz = min(60.000, self.current_freq_hz + recovery_step)
            
            if self.event_remaining_sec <= 0.0:
                self.active_event = None

        elif self.active_event == "LOAD_SHED":
            self.event_remaining_sec -= dt_seconds
            if self.event_remaining_sec > 14.0:
                # Surging to peak
                self.current_freq_hz = min(self.event_nadir_hz, self.current_freq_hz + 0.03 * dt_seconds)
            else:
                # Recovery back towards 60.00 Hz
                recovery_step = (self.current_freq_hz - 60.000) * 0.25 * dt_seconds
                self.current_freq_hz = max(60.000, self.current_freq_hz - recovery_step)
            
            if self.event_remaining_sec <= 0.0:
                self.active_event = None

        else:
            # Normal small stochastic grid fluctuations (Ornstein-Uhlenbeck mean-reverting drift)
            drift = (60.000 - self.current_freq_hz) * 0.4 * dt_seconds
            noise = random.gauss(0, 0.006)
            self.current_freq_hz = round(self.current_freq_hz + drift + noise, 3)

        # Rate of Change of Frequency (RoCoF)
        self.rocof_hz_s = round((self.current_freq_hz - self.previous_freq_hz) / max(0.1, dt_seconds), 3)

        # 1. Synthetic Inertia (Virtual Synchronous Machine)
        # P_inertia = -2 * H * RoCoF / f0 * P_rated
        p_inertia_kw = 0.0
        if abs(self.rocof_hz_s) > 0.005:
            p_inertia_kw = -2.0 * self.h_constant_s * (self.rocof_hz_s / self.f0) * self.rated_power_kw
            p_inertia_kw = max(-self.rated_power_kw, min(self.rated_power_kw, p_inertia_kw))

        # 2. Primary Frequency Droop Control
        # Governed by droop slope s = 4% with deadband
        delta_f = self.current_freq_hz - self.f0
        p_droop_kw = 0.0

        if delta_f < -self.deadband_hz:
            # Under-frequency: discharge battery to inject power
            effective_delta = delta_f + self.deadband_hz
            p_droop_kw = -(1.0 / self.droop_s) * (effective_delta / self.f0) * self.rated_power_kw
        elif delta_f > self.deadband_hz:
            # Over-frequency: charge battery to absorb surplus power
            effective_delta = delta_f - self.deadband_hz
            p_droop_kw = -(1.0 / self.droop_s) * (effective_delta / self.f0) * self.rated_power_kw

        p_droop_kw = max(-self.rated_power_kw, min(self.rated_power_kw, p_droop_kw))

        # 3. Fast Frequency Response (FFR) Burst Trigger
        ffr_active = False
        p_ffr_burst_kw = 0.0

        if self.current_freq_hz <= self.ffr_threshold_hz:
            ffr_active = True
            p_ffr_burst_kw = self.rated_power_kw  # Full 5,000 kW injection

        # Total Frequency Containment Reserve (FCR) response
        total_fcr_kw = max(-self.rated_power_kw, min(self.rated_power_kw, p_inertia_kw + p_droop_kw + p_ffr_burst_kw))

        # 4. Ancillary Services Financial Settlement
        # Capacity reservation: $38.50 / MW-h -> ~$0.0107 / MW-s for 3 MW reserved
        capacity_earnings = (3.0 * 38.50 / 3600.0) * dt_seconds
        # Mileage payment for actual active regulation
        mileage_earnings = abs(total_fcr_kw / 1000.0) * 0.045 * (dt_seconds / 60.0)
        self.accumulated_ancillary_usd += (capacity_earnings + mileage_earnings)

        # Status text
        if ffr_active:
            status = "CRITICAL_FFR_BURST"
        elif self.current_freq_hz < 59.95:
            status = "UNDER_FREQUENCY_DISPATCH"
        elif self.current_freq_hz > 60.05:
            status = "OVER_FREQUENCY_CURTAILMENT"
        else:
            status = "DEADBAND_NORMAL"

        return {
            "grid_frequency_hz": round(self.current_freq_hz, 3),
            "rocof_hz_s": round(self.rocof_hz_s, 3),
            "frequency_status": status,
            "p_inertia_kw": round(p_inertia_kw, 1),
            "p_droop_kw": round(p_droop_kw, 1),
            "p_ffr_burst_kw": round(p_ffr_burst_kw, 1),
            "total_fcr_kw": round(total_fcr_kw, 1),
            "ffr_active": ffr_active,
            "active_event": self.active_event,
            "event_remaining_sec": round(max(0.0, self.event_remaining_sec), 1),
            "ancillary_revenue_usd": round(self.accumulated_ancillary_usd, 2),
            "grid_deadband_hz": self.deadband_hz,
            "droop_slope_pct": self.droop_s * 100.0,
            "inertia_constant_h": self.h_constant_s
        }
