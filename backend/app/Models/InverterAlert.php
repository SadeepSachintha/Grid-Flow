<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class InverterAlert extends Model
{
    protected $fillable = [
        'plant_id',
        'inverter_id',
        'string_id',
        'alert_type',
        'severity',
        'message',
        'metric_value',
        'threshold_value',
        'status',
        'detected_at',
        'resolved_at',
    ];

    protected $casts = [
        'detected_at' => 'datetime',
        'resolved_at' => 'datetime',
    ];

    public function plant(): BelongsTo
    {
        return $this->belongsTo(Plant::class, 'plant_id');
    }

    public function inverter(): BelongsTo
    {
        return $this->belongsTo(Inverter::class, 'inverter_id');
    }
}
