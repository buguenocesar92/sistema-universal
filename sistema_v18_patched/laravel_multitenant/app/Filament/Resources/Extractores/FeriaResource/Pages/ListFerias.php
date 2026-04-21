<?php

namespace App\Filament\Resources\FeriaResource\Pages;

use App\Filament\Resources\FeriaResource;
use Filament\Actions;
use Filament\Resources\Pages\ListRecords;

class ListFerias extends ListRecords
{
    protected static string $resource = FeriaResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\CreateAction::make()];
    }
}
