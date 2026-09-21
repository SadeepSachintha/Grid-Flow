<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Plant extends Model
{
    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = [
        'id',
        'name',
        'solar_capacity_mw',
        'wind_capacity_mw',
        'total_capacity_mw',
        'latitude',
        'longitude',
        'interconnection_limit_mw',
    ];

    public function inverters(): HasMany
    {
        return $this->hasMany(Inverter::class, 'plant_id');
    }

    public function bessUnits(): HasMany
    {
        return $this->hasMany(BessUnit::class, 'plant_id');
    }

    public function dispatchSchedules(): HasMany
    {
        return $this->hasMany(DispatchSchedule::class, 'plant_id');
    }

    public function alerts(): HasMany
    {
        return $this->hasMany(InverterAlert::class, 'plant_id');
    }
}
