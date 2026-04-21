<?php

namespace App\Filament\Resources\ProveedoreResource\Pages;

use App\Filament\Resources\ProveedoreResource;
use Filament\Actions;
use Filament\Resources\Pages\ListRecords;

class ListProveedores extends ListRecords
{
    protected static string $resource = ProveedoreResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\CreateAction::make()];
    }
}
