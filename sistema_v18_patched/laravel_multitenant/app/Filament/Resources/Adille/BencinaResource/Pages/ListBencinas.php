<?php

namespace App\Filament\Resources\BencinaResource\Pages;

use App\Filament\Resources\BencinaResource;
use Filament\Actions;
use Filament\Resources\Pages\ListRecords;

class ListBencinas extends ListRecords
{
    protected static string $resource = BencinaResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\CreateAction::make()];
    }
}
