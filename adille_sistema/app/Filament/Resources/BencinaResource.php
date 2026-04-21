<?php

namespace App\Filament\Resources;

use App\Filament\Resources\BencinaResource\Pages;
use App\Models\Bencina;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class BencinaResource extends Resource
{
    protected static ?string $model = Bencina::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Bencina';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('numero')
                ->label('Numero').nullable(),
            Forms\Components\DatePicker::make('fecha')
                ->label('Fecha').nullable(),
            Forms\Components\TextInput::make('vehiculo')
                ->label('Vehiculo').nullable(),
            Forms\Components\TextInput::make('obra')
                ->label('Obra').nullable(),
            Forms\Components\TextInput::make('monto')
                ->label('Monto')
                ->numeric().required(),
            Forms\Components\TextInput::make('litros')
                ->label('Litros').nullable(),
            Forms\Components\TextInput::make('km')
                ->label('Km').nullable(),
            Forms\Components\Textarea::make('detalle')
                ->label('Detalle').nullable(),
            Forms\Components\Select::make('detalle')
                ->label('Detalle')
                ->relationship('detalle', 'detalle')
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
                Tables\Columns\TextColumn::make('numero')
                    ->label('Numero')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('fecha')
                    ->label('Fecha')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('vehiculo')
                    ->label('Vehiculo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('obra')
                    ->label('Obra')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('monto')
                    ->label('Monto')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('litros')
                    ->label('Litros')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('km')
                    ->label('Km')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('detalle')
                    ->label('Detalle')
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
            'index'  => Pages\ListBencinas::route('/'),
            'create' => Pages\CreateBencina::route('/create'),
            'edit'   => Pages\EditBencina::route('/{record}/edit'),
        ];
    }
}
