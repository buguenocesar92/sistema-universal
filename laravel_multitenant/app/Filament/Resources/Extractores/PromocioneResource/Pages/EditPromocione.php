<?php

namespace App\Filament\Resources\PromocioneResource\Pages;

use App\Filament\Resources\PromocioneResource;
use Filament\Actions;
use Filament\Resources\Pages\EditRecord;

class EditPromocione extends EditRecord
{
    protected static string $resource = PromocioneResource::class;

    protected function getHeaderActions(): array
    {
        return [Actions\DeleteAction::make()];
    }
}
