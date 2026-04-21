<?php

namespace App\Filament\Resources;

use App\Filament\Resources\VentaResource\Pages;
use App\Models\Venta;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class VentaResource extends Resource
{
    protected static ?string $model = Venta::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Ventas';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('item')
                ->label('Item').nullable(),
            Forms\Components\TextInput::make('contacto')
                ->label('Contacto').nullable(),
            Forms\Components\TextInput::make('tipo_estructura')
                ->label('Tipo estructura').nullable(),
            Forms\Components\TextInput::make('empresa')
                ->label('Empresa').nullable(),
            Forms\Components\TextInput::make('rut')
                ->label('Rut').nullable(),
            Forms\Components\TextInput::make('factura')
                ->label('Factura').nullable(),
            Forms\Components\DatePicker::make('fecha')
                ->label('Fecha').nullable(),
            Forms\Components\TextInput::make('modelo')
                ->label('Modelo').nullable(),
            Forms\Components\TextInput::make('cantidad')
                ->label('Cantidad')
                ->numeric().required(),
            Forms\Components\TextInput::make('neto')
                ->label('Neto').nullable(),
            Forms\Components\Select::make('item')
                ->label('Item')
                ->relationship('item', 'item')
                ->searchable()->preload()->nullable(),
            Forms\Components\Select::make('item')
                ->label('Item')
                ->relationship('item', 'item')
                ->searchable()->preload()->nullable(),
            Forms\Components\Select::make('modelo')
                ->label('Modelo')
                ->relationship('modelo', 'modelo')
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
                Tables\Columns\TextColumn::make('item')
                    ->label('Item')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('contacto')
                    ->label('Contacto')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('tipo_estructura')
                    ->label('Tipo estructura')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('empresa')
                    ->label('Empresa')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('rut')
                    ->label('Rut')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('factura')
                    ->label('Factura')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('fecha')
                    ->label('Fecha')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('modelo')
                    ->label('Modelo')
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
            'index'  => Pages\ListVentas::route('/'),
            'create' => Pages\CreateVenta::route('/create'),
            'edit'   => Pages\EditVenta::route('/{record}/edit'),
        ];
    }
}
