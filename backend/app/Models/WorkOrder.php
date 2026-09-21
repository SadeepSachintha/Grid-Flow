<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class WorkOrder extends Model
{
    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = [
        'id',
        'plant_id',
        'inverter_id',
        'string_id',
        'alert_id',
        'title',
        'description',
        'priority',
        'status',
        'assigned_technician',
        'technician_phone',
        'gps_latitude',
        'gps_longitude',
        'safety_protocol',
        'diagnostic_steps',
        'dispatched_at',
        'resolved_at',
    ];

    protected $casts = [
        'safety_protocol' => 'array',
        'diagnostic_steps' => 'array',
        'dispatched_at' => 'datetime',
        'resolved_at' => 'datetime',
        'gps_latitude' => 'float',
        'gps_longitude' => 'float',
    ];

    public function plant(): BelongsTo
    {
        return $this->belongsTo(Plant::class, 'plant_id');
    }

    public function inverter(): BelongsTo
    {
        return $this->belongsTo(Inverter::class, 'inverter_id');
    }

    public function alert(): BelongsTo
    {
        return $this->belongsTo(InverterAlert::class, 'alert_id');
    }

    public function scopeActive($query)
    {
        return $query->whereIn('status', ['DISPATCHED', 'ASSIGNED', 'IN_PROGRESS']);
    }

    public function scopeResolved($query)
    {
        return $query->where('status', 'RESOLVED');
    }
}
