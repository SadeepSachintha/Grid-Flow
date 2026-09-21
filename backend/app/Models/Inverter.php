<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Inverter extends Model
{
    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = [
        'id',
        'plant_id',
        'model',
        'rated_ac_kw',
        'strings_count',
        'status',
    ];

    public function plant(): BelongsTo
    {
        return $this->belongsTo(Plant::class, 'plant_id');
    }

    public function strings(): HasMany
    {
        return $this->hasMany(InverterString::class, 'inverter_id');
    }

    public function alerts(): HasMany
    {
        return $this->hasMany(InverterAlert::class, 'inverter_id');
    }
}
