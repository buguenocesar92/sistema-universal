<?php

namespace App\Filament\Resources\MaterialeResource\Pages;

use App\Filament\Resources\MaterialeResource;
use Filament\Actions;
use Filament\Resources\Pages\ListRecords;

class ListMateriales extends ListRecords
{
    protected static string $resource = MaterialeResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\CreateAction::make()];
    }
}
