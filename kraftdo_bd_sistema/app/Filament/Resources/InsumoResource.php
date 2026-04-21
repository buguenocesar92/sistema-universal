<?php

namespace App\Filament\Resources;

use App\Filament\Resources\InsumoResource\Pages;
use App\Models\Insumo;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class InsumoResource extends Resource
{
    protected static ?string $model = Insumo::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Insumos';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('id')
                ->label('Id').nullable(),
            Forms\Components\TextInput::make('nombre')
                ->label('Nombre').nullable(),
            Forms\Components\TextInput::make('unidad')
                ->label('Unidad').nullable(),
            Forms\Components\TextInput::make('stock')
                ->label('Stock')
                ->numeric().required(),
            Forms\Components\TextInput::make('stock_min')
                ->label('Stock min').nullable(),
            Forms\Components\TextInput::make('alerta')
                ->label('Alerta').nullable(),
            Forms\Components\TextInput::make('costo')
                ->label('Costo')
                ->numeric().required(),
            Forms\Components\TextInput::make('proveedor')
                ->label('Proveedor').nullable(),
            Forms\Components\TextInput::make('actualizado')
                ->label('Actualizado').nullable(),
            Forms\Components\Textarea::make('notas')
                ->label('Notas').nullable(),
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
                Tables\Columns\TextColumn::make('id')
                    ->label('Id')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('nombre')
                    ->label('Nombre')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('unidad')
                    ->label('Unidad')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('stock')
                    ->label('Stock')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('stock_min')
                    ->label('Stock min')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('alerta')
                    ->label('Alerta')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('costo')
                    ->label('Costo')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('proveedor')
                    ->label('Proveedor')
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
            'index'  => Pages\ListInsumos::route('/'),
            'create' => Pages\CreateInsumo::route('/create'),
            'edit'   => Pages\EditInsumo::route('/{record}/edit'),
        ];
    }
}
