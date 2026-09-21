<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // 1. Renewable Plants
        Schema::create('plants', function (Blueprint $table) {
            $table->string('id')->primary(); // e.g. PLANT-SOLARIA-01
            $table->string('name');
            $table->decimal('solar_capacity_mw', 8, 2);
            $table->decimal('wind_capacity_mw', 8, 2);
            $table->decimal('total_capacity_mw', 8, 2);
            $table->decimal('latitude', 10, 6);
            $table->decimal('longitude', 10, 6);
            $table->decimal('interconnection_limit_mw', 8, 2)->default(25.0);
            $table->timestamps();
        });

        // 2. Central Inverters
        Schema::create('inverters', function (Blueprint $table) {
            $table->string('id')->primary(); // e.g. INV-01
            $table->string('plant_id');
            $table->string('model')->default('SMA Sunny Central 5000UP');
            $table->decimal('rated_ac_kw', 8, 2)->default(5000.0);
            $table->integer('strings_count')->default(8);
            $table->string('status')->default('NORMAL'); // NORMAL, WARNING, FAULT
            $table->timestamps();

            $table->foreign('plant_id')->references('id')->on('plants')->onDelete('cascade');
        });

        // 3. PV Strings
        Schema::create('inverter_strings', function (Blueprint $table) {
            $table->string('id')->primary(); // e.g. INV-01:STR-01
            $table->string('inverter_id');
            $table->string('string_code'); // STR-01
            $table->decimal('nominal_voltage_v', 8, 2)->default(850.0);
            $table->decimal('nominal_current_a', 8, 2)->default(18.5);
            $table->integer('panel_count')->default(20);
            $table->string('status')->default('NORMAL');
            $table->timestamps();

            $table->foreign('inverter_id')->references('id')->on('inverters')->onDelete('cascade');
        });

        // 4. BESS Units
        Schema::create('bess_units', function (Blueprint $table) {
            $table->string('id')->primary(); // BESS-01
            $table->string('plant_id');
            $table->decimal('capacity_mwh', 8, 2)->default(10.0);
            $table->decimal('max_power_mw', 8, 2)->default(5.0);
            $table->decimal('current_soc_pct', 5, 2)->default(65.0);
            $table->decimal('roundtrip_efficiency', 5, 2)->default(0.92);
            $table->string('chemistry')->default('LiFePO4');
            $table->timestamps();

            $table->foreign('plant_id')->references('id')->on('plants')->onDelete('cascade');
        });

        // 5. Committed Dispatch Schedules
        Schema::create('dispatch_schedules', function (Blueprint $table) {
            $table->id();
            $table->string('plant_id');
            $table->integer('hour_of_day'); // 0 - 23
            $table->decimal('committed_kw', 10, 2);
            $table->decimal('tolerance_pct', 5, 2)->default(5.0);
            $table->decimal('penalty_rate_per_kwh', 6, 4)->default(0.0750);
            $table->timestamps();

            $table->foreign('plant_id')->references('id')->on('plants')->onDelete('cascade');
        });

        // 6. Inverter & SCADA Alerts
        Schema::create('inverter_alerts', function (Blueprint $table) {
            $table->id();
            $table->string('plant_id');
            $table->string('inverter_id')->nullable();
            $table->string('string_id')->nullable();
            $table->string('alert_type');
            $table->string('severity'); // CRITICAL, WARNING, INFO
            $table->text('message');
            $table->decimal('metric_value', 10, 2)->nullable();
            $table->decimal('threshold_value', 10, 2)->nullable();
            $table->string('status')->default('OPEN'); // OPEN, ACKNOWLEDGED, RESOLVED
            $table->timestamp('detected_at')->useCurrent();
            $table->timestamp('resolved_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('inverter_alerts');
        Schema::dropIfExists('dispatch_schedules');
        Schema::dropIfExists('bess_units');
        Schema::dropIfExists('inverter_strings');
        Schema::dropIfExists('inverters');
        Schema::dropIfExists('plants');
    }
};
