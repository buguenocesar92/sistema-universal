<?php

namespace App\Filament\Resources\MaterialeResource\Pages;

use App\Filament\Resources\MaterialeResource;
use Filament\Actions;
use Filament\Resources\Pages\EditRecord;

class EditMateriale extends EditRecord
{
    protected static string $resource = MaterialeResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\DeleteAction::make()];
    }
}
