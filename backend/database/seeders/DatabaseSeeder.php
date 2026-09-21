<?php

namespace Database\Seeders;

use App\Models\BessUnit;
use App\Models\DispatchSchedule;
use App\Models\Inverter;
use App\Models\InverterString;
use App\Models\Plant;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // 1. Plant
        $plant = Plant::create([
            'id' => 'PLANT-SOLARIA-01',
            'name' => 'Solaria West Microgrid & Wind Farm',
            'solar_capacity_mw' => 20.0,
            'wind_capacity_mw' => 5.0,
            'total_capacity_mw' => 25.0,
            'latitude' => 34.924000,
            'longitude' => -116.892000,
            'interconnection_limit_mw' => 25.0,
        ]);

        // 2. Inverters & Strings
        $inverters = ['INV-01', 'INV-02', 'INV-03', 'INV-04'];
        foreach ($inverters as $invId) {
            $inverter = Inverter::create([
                'id' => $invId,
                'plant_id' => $plant->id,
                'model' => 'SMA Sunny Central 5000UP',
                'rated_ac_kw' => 5000.0,
                'strings_count' => 8,
                'status' => 'NORMAL',
            ]);

            for ($s = 1; $s <= 8; $s++) {
                $code = sprintf('STR-%02d', $s);
                InverterString::create([
                    'id' => "{$invId}:{$code}",
                    'inverter_id' => $inverter->id,
                    'string_code' => $code,
                    'nominal_voltage_v' => 850.0,
                    'nominal_current_a' => 18.5,
                    'panel_count' => 20,
                    'status' => 'NORMAL',
                ]);
            }
        }

        // 3. BESS Unit
        BessUnit::create([
            'id' => 'BESS-01',
            'plant_id' => $plant->id,
            'capacity_mwh' => 10.0,
            'max_power_mw' => 5.0,
            'current_soc_pct' => 65.0,
            'roundtrip_efficiency' => 0.92,
            'chemistry' => 'LiFePO4',
        ]);

        // 4. 24-Hour Dispatch Schedule
        for ($h = 0; $h < 24; $h++) {
            $committedKw = 2800.0; // Baseline wind
            if ($h >= 6 && $h <= 18) {
                $solarPeak = 17500.0 * sin(pi() * ($h - 6) / 12.0);
                $committedKw += max(0.0, $solarPeak);
            }

            DispatchSchedule::create([
                'plant_id' => $plant->id,
                'hour_of_day' => $h,
                'committed_kw' => round($committedKw, 2),
                'tolerance_pct' => 5.0,
                'penalty_rate_per_kwh' => 0.0750,
            ]);
        }
    }
}
