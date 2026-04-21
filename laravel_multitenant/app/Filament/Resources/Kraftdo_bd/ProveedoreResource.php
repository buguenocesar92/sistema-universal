<?php

namespace App\Filament\Resources\Kraftdo_bd;

use App\Filament\Resources\ProveedoreResource\Pages;
use App\Models\Kraftdo_bd\Proveedore;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class ProveedoreResource extends Resource
{
    protected static ?string $model = Proveedore::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Proveedores';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('id')
                ->label('Id').nullable(),
            Forms\Components\TextInput::make('nombre')
                ->label('Nombre').nullable(),
            Forms\Components\TextInput::make('contacto')
                ->label('Contacto').nullable(),
            Forms\Components\TextInput::make('tipo')
                ->label('Tipo').nullable(),
            Forms\Components\TextInput::make('despacho')
                ->label('Despacho').nullable(),
            Forms\Components\TextInput::make('minimo')
                ->label('Minimo').nullable(),
            Forms\Components\TextInput::make('envio_gratis')
                ->label('Envio gratis').nullable(),
            Forms\Components\Textarea::make('notas')
                ->label('Notas').nullable(),
            Forms\Components\TextInput::make('actualizado')
                ->label('Actualizado').nullable(),
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
                Tables\Columns\TextColumn::make('contacto')
                    ->label('Contacto')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('tipo')
                    ->label('Tipo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('despacho')
                    ->label('Despacho')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('minimo')
                    ->label('Minimo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('envio_gratis')
                    ->label('Envio gratis')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('notas')
                    ->label('Notas')
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
            'index'  => Pages\ListProveedores::route('/'),
            'create' => Pages\CreateProveedore::route('/create'),
            'edit'   => Pages\EditProveedore::route('/{record}/edit'),
        ];
    }
}
