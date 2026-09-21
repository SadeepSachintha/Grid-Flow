<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Jobs\DispatchWorkOrderNotificationJob;
use App\Models\WorkOrder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class WorkOrderController extends Controller
{
    // GPS Coordinates for plant inverters in Mojave High-Desert
    private array $inverterGps = [
        'INV-01' => ['lat' => 34.925500, 'lng' => -116.895000],
        'INV-02' => ['lat' => 34.924200, 'lng' => -116.895000],
        'INV-03' => ['lat' => 34.925500, 'lng' => -116.889000],
        'INV-04' => ['lat' => 34.924200, 'lng' => -116.889000],
    ];

    public function index(Request $request): JsonResponse
    {
        $query = WorkOrder::orderBy('dispatched_at', 'desc');

        if ($request->has('status') && $request->query('status') !== 'ALL') {
            $query->where('status', $request->query('status'));
        }

        if ($request->has('priority') && $request->query('priority') !== 'ALL') {
            $query->where('priority', $request->query('priority'));
        }

        return response()->json($query->limit(50)->get());
    }

    public function storeFromAlert(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'plant_id' => 'required|string',
            'inverter_id' => 'required|string',
            'string_id' => 'nullable|string',
            'alert_type' => 'required|string',
            'message' => 'required|string',
            'severity' => 'nullable|string',
        ]);

        $invId = $validated['inverter_id'];
        $strId = $validated['string_id'] ?? null;
        $alertType = $validated['alert_type'];
        $woId = 'WO-' . date('Y') . '-' . sprintf('%04d', rand(100, 9999));

        // Tailor diagnostic steps and safety protocol
        $diagnosticSteps = [];
        $safetyProtocol = [
            'PPE: Arc-flash face shield (Category 2, 8 cal/cm²)',
            '1000V/1500V Class 0 insulating rubber gloves',
            'Lockout / Tagout (LOTO) key station on main DC disconnect',
            'Two-person buddy system mandatory for 1500V DC bus access'
        ];

        if (str_contains($alertType, 'FUSE') || str_contains($alertType, 'OPEN_CIRCUIT')) {
            $title = "Investigate Blown Fuse on {$invId}" . ($strId ? ":{$strId}" : "");
            $diagnosticSteps = [
                ['step' => 1, 'task' => 'Perform Lockout/Tagout (LOTO) on DC disconnect switch of inverter ' . $invId, 'completed' => false],
                ['step' => 2, 'task' => 'Verify zero energy state on DC bus with 1500V CAT IV multimeter', 'completed' => false],
                ['step' => 3, 'task' => 'Locate string combiner box and inspect 32A gPV 1500V DC cartridge fuse for string ' . $strId, 'completed' => false],
                ['step' => 4, 'task' => 'Perform continuity check across fuse terminals using digital multimeter (DMM)', 'completed' => false],
                ['step' => 5, 'task' => 'Replace defective fuse with certified Cooper Bussmann / Littelfuse 32A 1500V gPV element', 'completed' => false],
                ['step' => 6, 'task' => 'Measure string Voc (~850V) and Isc (~18A) with DC clamp meter before re-energizing', 'completed' => false],
                ['step' => 7, 'task' => 'Re-engage DC disconnect and verify telemetry normal status in SCADA', 'completed' => false],
            ];
        } elseif (str_contains($alertType, 'OVERHEAT')) {
            $title = "Emergency Thermal Inspection for Inverter {$invId}";
            $diagnosticSteps = [
                ['step' => 1, 'task' => 'Inspect external heat exchanger fan rotation and clear dust accumulation from intake louvers', 'completed' => false],
                ['step' => 2, 'task' => 'Measure heatsink surface temperature with calibrated FLIR infrared thermal camera', 'completed' => false],
                ['step' => 3, 'task' => 'Verify liquid cooling loop pressure (nominal: 2.2 bar) and coolant reservoir level', 'completed' => false],
                ['step' => 4, 'task' => 'Inspect IGBT power block thermal interface paste and torque all busbar connections', 'completed' => false],
            ];
        } else {
            $title = "String Mismatch & Degradation Check: {$invId}" . ($strId ? ":{$strId}" : "");
            $diagnosticSteps = [
                ['step' => 1, 'task' => 'Perform aerial drone / visual inspection of string modules for dust soiling or physical damage', 'completed' => false],
                ['step' => 2, 'task' => 'Measure forward voltage drop across bypass diodes in string junction boxes', 'completed' => false],
                ['step' => 3, 'task' => 'Perform string insulation resistance megohmmeter test (Riso > 1.0 MΩ @ 1000V DC)', 'completed' => false],
                ['step' => 4, 'task' => 'Verify MC4 connector crimp integrity and check for thermal discoloration', 'completed' => false],
            ];
        }

        $gps = $this->inverterGps[$invId] ?? ['lat' => 34.924200, 'lng' => -116.895000];

        $workOrder = WorkOrder::create([
            'id' => $woId,
            'plant_id' => $validated['plant_id'],
            'inverter_id' => $invId,
            'string_id' => $strId,
            'title' => $title,
            'description' => $validated['message'],
            'priority' => ($validated['severity'] ?? 'CRITICAL') === 'CRITICAL' ? 'CRITICAL' : 'HIGH',
            'status' => 'DISPATCHED',
            'assigned_technician' => 'Marcus Vance (Senior PV Specialist #4)',
            'technician_phone' => '+1 (760) 555-0194',
            'gps_latitude' => $gps['lat'],
            'gps_longitude' => $gps['lng'],
            'safety_protocol' => $safetyProtocol,
            'diagnostic_steps' => $diagnosticSteps,
            'dispatched_at' => now(),
        ]);

        // Dispatch background notification job
        DispatchWorkOrderNotificationJob::dispatch($workOrder);

        return response()->json($workOrder, 201);
    }

    public function updateStatus(Request $request, string $id): JsonResponse
    {
        $workOrder = WorkOrder::find($id);

        if (!$workOrder) {
            return response()->json(['message' => 'Work Order not found'], 404);
        }

        $validated = $request->validate([
            'status' => 'required|string|in:ASSIGNED,IN_PROGRESS,RESOLVED',
            'step_index' => 'nullable|integer',
            'step_completed' => 'nullable|boolean',
        ]);

        $workOrder->status = $validated['status'];

        if ($validated['status'] === 'RESOLVED') {
            $workOrder->resolved_at = now();
        }

        // Update diagnostic step checkbox if supplied
        if (isset($validated['step_index']) && isset($validated['step_completed'])) {
            $steps = $workOrder->diagnostic_steps ?? [];
            if (isset($steps[$validated['step_index']])) {
                $steps[$validated['step_index']]['completed'] = $validated['step_completed'];
                $workOrder->diagnostic_steps = $steps;
            }
        }

        $workOrder->save();
        return response()->json($workOrder);
    }

    public function ticket(string $id): JsonResponse
    {
        $workOrder = WorkOrder::with(['plant', 'inverter'])->find($id);

        if (!$workOrder) {
            return response()->json(['message' => 'Work Order not found'], 404);
        }

        return response()->json([
            'ticket_id' => $workOrder->id,
            'title' => $workOrder->title,
            'plant' => $workOrder->plant_id,
            'asset' => "{$workOrder->inverter_id}" . ($workOrder->string_id ? ":{$workOrder->string_id}" : ""),
            'priority' => $workOrder->priority,
            'status' => $workOrder->status,
            'assigned_technician' => $workOrder->assigned_technician,
            'technician_contact' => $workOrder->technician_phone,
            'gps_coordinates' => "{$workOrder->gps_latitude}, {$workOrder->gps_longitude}",
            'google_maps_nav' => "https://www.google.com/maps/dir/?api=1&destination={$workOrder->gps_latitude},{$workOrder->gps_longitude}",
            'safety_requirements' => $workOrder->safety_protocol,
            'diagnostic_checklist' => $workOrder->diagnostic_steps,
            'dispatched_at' => $workOrder->dispatched_at?->toIso8601String(),
            'resolved_at' => $workOrder->resolved_at?->toIso8601String(),
        ]);
    }
}
