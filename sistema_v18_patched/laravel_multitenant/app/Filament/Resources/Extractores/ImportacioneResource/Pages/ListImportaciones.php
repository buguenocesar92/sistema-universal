<?php

namespace App\Filament\Resources\ImportacioneResource\Pages;

use App\Filament\Resources\ImportacioneResource;
use Filament\Actions;
use Filament\Resources\Pages\ListRecords;

class ListImportaciones extends ListRecords
{
    protected static string $resource = ImportacioneResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\CreateAction::make()];
    }
}
