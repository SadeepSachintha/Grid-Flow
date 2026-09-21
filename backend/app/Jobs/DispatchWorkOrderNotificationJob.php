<?php

namespace App\Jobs;

use App\Models\WorkOrder;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class DispatchWorkOrderNotificationJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(public WorkOrder $workOrder)
    {
    }

    public function handle(): void
    {
        $wo = $this->workOrder;

        $payload = [
            'event' => 'WORK_ORDER_DISPATCHED',
            'work_order_id' => $wo->id,
            'priority' => $wo->priority,
            'title' => $wo->title,
            'plant' => $wo->plant_id,
            'asset' => "{$wo->inverter_id}" . ($wo->string_id ? ":{$wo->string_id}" : ""),
            'technician' => [
                'name' => $wo->assigned_technician,
                'phone' => $wo->technician_phone,
            ],
            'coordinates' => [
                'latitude' => $wo->gps_latitude,
                'longitude' => $wo->gps_longitude,
                'google_maps_url' => "https://maps.google.com/?q={$wo->gps_latitude},{$wo->gps_longitude}",
            ],
            'dispatched_at' => $wo->dispatched_at?->toIso8601String(),
        ];

        // Simulated PagerDuty / Slack Webhook dispatch
        Log::info("[PAGERDUTY / SLACK DISPATCH] Work Order {$wo->id} routed to field technician {$wo->assigned_technician}", $payload);
    }
}
