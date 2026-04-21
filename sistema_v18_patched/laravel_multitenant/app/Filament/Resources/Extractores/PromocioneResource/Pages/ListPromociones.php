<?php

namespace App\Filament\Resources\PromocioneResource\Pages;

use App\Filament\Resources\PromocioneResource;
use Filament\Actions;
use Filament\Resources\Pages\ListRecords;

class ListPromociones extends ListRecords
{
    protected static string $resource = PromocioneResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\CreateAction::make()];
    }
}
