<?php

namespace App\Filament\Resources\FacturacionResource\Pages;

use App\Filament\Resources\FacturacionResource;
use Filament\Actions;
use Filament\Resources\Pages\EditRecord;

class EditFacturacion extends EditRecord
{
    protected static string $resource = FacturacionResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\DeleteAction::make()];
    }
}
