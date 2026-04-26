<?php

namespace App\Filament\Pages;

use Filament\Pages\Dashboard as BaseDashboard;

class Dashboard extends BaseDashboard
{
    protected static ?string $navigationIcon = 'heroicon-o-home';
    protected static ?string $title = 'Dashboard — Extractores Chile Ltda';

    public function getWidgets(): array
    {
        return [
            \App\Filament\Widgets\ExtractoresStatsWidget::class,
        ];
    }
}
