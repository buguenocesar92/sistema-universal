<?php

namespace App\Traits;

use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;

/**
 * Trait que aplica activitylog automáticamente a todos los modelos KraftDo.
 * Registra quién cambió qué, cuándo, desde qué IP.
 *
 * Uso en los modelos generados:
 *   use App\Traits\LogsKraftDoActivity;
 *
 *   class Materiale extends Model {
 *       use LogsKraftDoActivity;
 *   }
 */
trait LogsKraftDoActivity
{
    use LogsActivity;

    public function getActivitylogOptions(): LogOptions
    {
        return LogOptions::defaults()
            ->logAll()
            ->logOnlyDirty()
            ->dontSubmitEmptyLogs()
            ->useLogName(class_basename($this))
            ->setDescriptionForEvent(
                fn(string $eventName) => "{$eventName} " . class_basename($this)
            );
    }
}
