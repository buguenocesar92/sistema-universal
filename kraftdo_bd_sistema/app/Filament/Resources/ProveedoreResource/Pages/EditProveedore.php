<?php

namespace App\Filament\Resources\ProveedoreResource\Pages;

use App\Filament\Resources\ProveedoreResource;
use Filament\Actions;
use Filament\Resources\Pages\EditRecord;

class EditProveedore extends EditRecord
{
    protected static string $resource = ProveedoreResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\DeleteAction::make()];
    }
}
