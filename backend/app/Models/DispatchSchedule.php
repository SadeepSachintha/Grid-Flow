<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DispatchSchedule extends Model
{
    protected $fillable = [
        'plant_id',
        'hour_of_day',
        'committed_kw',
        'tolerance_pct',
        'penalty_rate_per_kwh',
    ];

    public function plant(): BelongsTo
    {
        return $this->belongsTo(Plant::class, 'plant_id');
    }
}
