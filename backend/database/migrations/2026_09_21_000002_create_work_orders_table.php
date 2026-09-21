<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('work_orders', function (Blueprint $table) {
            $table->string('id')->primary(); // e.g. WO-2026-0041
            $table->string('plant_id');
            $table->string('inverter_id')->nullable();
            $table->string('string_id')->nullable();
            $table->unsignedBigInteger('alert_id')->nullable();
            $table->string('title');
            $table->text('description')->nullable();
            $table->string('priority')->default('HIGH'); // CRITICAL, HIGH, MEDIUM, LOW
            $table->string('status')->default('DISPATCHED'); // DISPATCHED, ASSIGNED, IN_PROGRESS, RESOLVED
            $table->string('assigned_technician')->default('Marcus Vance (PV Specialist)');
            $table->string('technician_phone')->default('+1 (760) 555-0194');
            $table->decimal('gps_latitude', 10, 6)->default(34.924200);
            $table->decimal('gps_longitude', 10, 6)->default(-116.895000);
            $table->json('safety_protocol')->nullable();
            $table->json('diagnostic_steps')->nullable();
            $table->timestamp('dispatched_at')->useCurrent();
            $table->timestamp('resolved_at')->nullable();
            $table->timestamps();

            $table->foreign('plant_id')->references('id')->on('plants')->onDelete('cascade');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('work_orders');
    }
};
