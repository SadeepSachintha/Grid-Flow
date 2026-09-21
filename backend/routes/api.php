<?php

use App\Http\Controllers\Api\AlertController;
use App\Http\Controllers\Api\DispatchController;
use App\Http\Controllers\Api\PlantController;
use App\Http\Controllers\Api\WorkOrderController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function () {
    // Plant & Inverter Registries
    Route::get('/plants', [PlantController::class, 'index']);
    Route::get('/plants/{id}', [PlantController::class, 'show']);

    // Inverter Health & SCADA Alerts
    Route::get('/alerts', [AlertController::class, 'index']);
    Route::post('/alerts', [AlertController::class, 'store']);
    Route::post('/alerts/{id}/acknowledge', [AlertController::class, 'acknowledge']);

    // Grid Dispatch Schedules & Penalties
    Route::get('/plants/{plantId}/schedules', [DispatchController::class, 'schedules']);
    Route::post('/dispatch/evaluate', [DispatchController::class, 'evaluate']);

    // Automated Field Technician Work Orders
    Route::get('/work-orders', [WorkOrderController::class, 'index']);
    Route::post('/work-orders/from-alert', [WorkOrderController::class, 'storeFromAlert']);
    Route::patch('/work-orders/{id}/status', [WorkOrderController::class, 'updateStatus']);
    Route::get('/work-orders/{id}/ticket', [WorkOrderController::class, 'ticket']);
});
