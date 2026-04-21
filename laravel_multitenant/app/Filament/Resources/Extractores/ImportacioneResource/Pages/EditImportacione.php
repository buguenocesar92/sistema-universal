<?php

namespace App\Filament\Resources\ImportacioneResource\Pages;

use App\Filament\Resources\ImportacioneResource;
use Filament\Actions;
use Filament\Resources\Pages\EditRecord;

class EditImportacione extends EditRecord
{
    protected static string $resource = ImportacioneResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\DeleteAction::make()];
    }
}
