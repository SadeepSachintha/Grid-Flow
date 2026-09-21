<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class InverterString extends Model
{
    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = [
        'id',
        'inverter_id',
        'string_code',
        'nominal_voltage_v',
        'nominal_current_a',
        'panel_count',
        'status',
    ];

    public function inverter(): BelongsTo
    {
        return $this->belongsTo(Inverter::class, 'inverter_id');
    }
}
