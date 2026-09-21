<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Plant;
use Illuminate\Http\JsonResponse;

class PlantController extends Controller
{
    public function index(): JsonResponse
    {
        $plants = Plant::with(['inverters.strings', 'bessUnits', 'dispatchSchedules'])->get();
        return response()->json($plants);
    }

    public function show(string $id): JsonResponse
    {
        $plant = Plant::with(['inverters.strings', 'bessUnits', 'dispatchSchedules'])->find($id);

        if (!$plant) {
            return response()->json(['message' => 'Plant not found'], 404);
        }

        return response()->json($plant);
    }
}
