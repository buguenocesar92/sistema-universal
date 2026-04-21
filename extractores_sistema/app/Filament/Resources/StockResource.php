<?php

namespace App\Filament\Resources;

use App\Filament\Resources\StockResource\Pages;
use App\Models\Stock;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class StockResource extends Resource
{
    protected static ?string $model = Stock::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Stock';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('modelo')
                ->label('Modelo').nullable(),
            Forms\Components\TextInput::make('importacion')
                ->label('Importacion').nullable(),
            Forms\Components\TextInput::make('ventas')
                ->label('Ventas').nullable(),
            Forms\Components\TextInput::make('promociones')
                ->label('Promociones').nullable(),
            Forms\Components\TextInput::make('stock_disponible')
                ->label('Stock disponible').nullable(),
            Forms\Components\Select::make('modelo')
                ->label('Modelo')
                ->relationship('modelo', 'modelo')
                ->searchable()->preload()->nullable(),
            Forms\Components\Select::make('ventas')
                ->label('Ventas')
                ->relationship('venta', 'item')
                ->searchable()->preload()->nullable(),
            Forms\Components\Select::make('promociones')
                ->label('Promociones')
                ->relationship('promocione', 'item')
                ->searchable()->preload()->nullable(),
        ]);
    }

    public static function table(Table $table): Table
    {
        return $table
            ->headerActions([
            \pxlrbt\FilamentExcel\Actions\Tables\ExportAction::make()
                ->exports([
                    \pxlrbt\FilamentExcel\Exports\ExcelExport::make()->fromTable(),
                ]),
            ])
            ->columns([
                Tables\Columns\TextColumn::make('modelo')
                    ->label('Modelo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('importacion')
                    ->label('Importacion')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('ventas')
                    ->label('Ventas')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('promociones')
                    ->label('Promociones')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('stock_disponible')
                    ->label('Stock disponible')
                    ->sortable()->searchable(),
            ])
            ->filters([
            ])
            ->actions([
                Tables\Actions\EditAction::make(),
                Tables\Actions\DeleteAction::make(),
            ])
            ->bulkActions([
                Tables\Actions\BulkActionGroup::make([
                    Tables\Actions\DeleteBulkAction::make(),
                ]),
            ]);
    }

    public static function getPages(): array
    {
        return [
            'index'  => Pages\ListStocks::route('/'),
            'create' => Pages\CreateStock::route('/create'),
            'edit'   => Pages\EditStock::route('/{record}/edit'),
        ];
    }
}
