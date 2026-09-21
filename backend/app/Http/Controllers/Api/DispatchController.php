<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\DispatchSchedule;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DispatchController extends Controller
{
    public function schedules(string $plantId): JsonResponse
    {
        $schedules = DispatchSchedule::where('plant_id', $plantId)
            ->orderBy('hour_of_day', 'asc')
            ->get();

        return response()->json($schedules);
    }

    public function evaluate(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'plant_id' => 'required|string',
            'actual_injected_kw' => 'required|numeric',
            'hour_of_day' => 'required|integer|min:0|max:23',
        ]);

        $schedule = DispatchSchedule::where('plant_id', $validated['plant_id'])
            ->where('hour_of_day', $validated['hour_of_day'])
            ->first();

        if (!$schedule) {
            return response()->json(['message' => 'No schedule found for this hour'], 404);
        }

        $committed = (float) $schedule->committed_kw;
        $actual = (float) $validated['actual_injected_kw'];
        $toleranceKw = $committed * ($schedule->tolerance_pct / 100.0);
        $deviation = $actual - $committed;
        $isPenalty = abs($deviation) > $toleranceKw && $committed > 0;

        $penaltyCost = 0.0;
        if ($isPenalty) {
            $unexcusedKw = abs($deviation) - $toleranceKw;
            $penaltyCost = $unexcusedKw * (float) $schedule->penalty_rate_per_kwh;
        }

        return response()->json([
            'committed_kw' => $committed,
            'actual_kw' => $actual,
            'deviation_kw' => round($deviation, 2),
            'tolerance_kw' => round($toleranceKw, 2),
            'is_penalty' => $isPenalty,
            'penalty_rate_per_kwh' => (float) $schedule->penalty_rate_per_kwh,
            'penalty_cost_rate_usd_h' => round($penaltyCost, 2),
        ]);
    }
}
