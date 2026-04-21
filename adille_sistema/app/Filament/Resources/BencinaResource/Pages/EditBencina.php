<?php

namespace App\Filament\Resources\BencinaResource\Pages;

use App\Filament\Resources\BencinaResource;
use Filament\Actions;
use Filament\Resources\Pages\EditRecord;

class EditBencina extends EditRecord
{
    protected static string $resource = BencinaResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\DeleteAction::make()];
    }
}
