<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\InverterAlert;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AlertController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $query = InverterAlert::orderBy('detected_at', 'desc');

        if ($request->has('status')) {
            $query->where('status', $request->query('status'));
        }

        if ($request->has('severity')) {
            $query->where('severity', $request->query('severity'));
        }

        return response()->json($query->limit(100)->get());
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'plant_id' => 'required|string',
            'inverter_id' => 'nullable|string',
            'string_id' => 'nullable|string',
            'alert_type' => 'required|string',
            'severity' => 'required|string|in:CRITICAL,WARNING,INFO',
            'message' => 'required|string',
            'metric_value' => 'nullable|numeric',
            'threshold_value' => 'nullable|numeric',
        ]);

        $alert = InverterAlert::create($validated);
        return response()->json($alert, 201);
    }

    public function acknowledge(int $id): JsonResponse
    {
        $alert = InverterAlert::find($id);

        if (!$alert) {
            return response()->json(['message' => 'Alert not found'], 404);
        }

        $alert->update(['status' => 'ACKNOWLEDGED']);
        return response()->json(['status' => 'SUCCESS', 'alert' => $alert]);
    }
}
