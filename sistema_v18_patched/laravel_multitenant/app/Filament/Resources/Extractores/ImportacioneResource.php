<?php

namespace App\Filament\Resources\Extractores;

use App\Filament\Resources\ImportacioneResource\Pages;
use App\Models\Extractores\Importacione;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class ImportacioneResource extends Resource
{
    protected static ?string $model = Importacione::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Importaciones';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('item')
                ->label('Item').nullable(),
            Forms\Components\TextInput::make('modelo')
                ->label('Modelo').nullable(),
            Forms\Components\TextInput::make('unidades')
                ->label('Unidades').nullable(),
            Forms\Components\TextInput::make('pi_numero')
                ->label('Pi numero').nullable(),
            Forms\Components\TextInput::make('empresa')
                ->label('Empresa').nullable(),
            Forms\Components\TextInput::make('rut')
                ->label('Rut').nullable(),
            Forms\Components\TextInput::make('factura')
                ->label('Factura').nullable(),
            Forms\Components\TextInput::make('costo_china')
                ->label('Costo china')
                ->numeric().required(),
            Forms\Components\TextInput::make('embarcadero')
                ->label('Embarcadero').nullable(),
            Forms\Components\TextInput::make('agente_aduana')
                ->label('Agente aduana').nullable(),
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
                Tables\Columns\TextColumn::make('modelo')
                    ->label('Modelo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('unidades')
                    ->label('Unidades')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('pi_numero')
                    ->label('Pi numero')
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
                Tables\Columns\TextColumn::make('costo_china')
                    ->label('Costo china')
                    ->numeric()->sortable()->searchable(),
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
            'index'  => Pages\ListImportaciones::route('/'),
            'create' => Pages\CreateImportacione::route('/create'),
            'edit'   => Pages\EditImportacione::route('/{record}/edit'),
        ];
    }
}
