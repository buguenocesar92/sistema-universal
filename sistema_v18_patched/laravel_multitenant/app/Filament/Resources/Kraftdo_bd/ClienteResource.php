<?php

namespace App\Filament\Resources\Kraftdo_bd;

use App\Filament\Resources\ClienteResource\Pages;
use App\Models\Kraftdo_bd\Cliente;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class ClienteResource extends Resource
{
    protected static ?string $model = Cliente::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Clientes';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('id')
                ->label('Id').nullable(),
            Forms\Components\TextInput::make('nombre')
                ->label('Nombre').nullable(),
            Forms\Components\TextInput::make('tipo')
                ->label('Tipo').nullable(),
            Forms\Components\TextInput::make('whatsapp')
                ->label('Whatsapp').nullable(),
            Forms\Components\TextInput::make('ciudad')
                ->label('Ciudad').nullable(),
            Forms\Components\TextInput::make('correo')
                ->label('Correo').nullable(),
            Forms\Components\TextInput::make('rubro')
                ->label('Rubro').nullable(),
            Forms\Components\TextInput::make('canal')
                ->label('Canal').nullable(),
            Forms\Components\DatePicker::make('fecha')
                ->label('Fecha').nullable(),
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
                Tables\Columns\TextColumn::make('tipo')
                    ->label('Tipo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('whatsapp')
                    ->label('Whatsapp')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('ciudad')
                    ->label('Ciudad')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('correo')
                    ->label('Correo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('rubro')
                    ->label('Rubro')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('canal')
                    ->label('Canal')
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
            'index'  => Pages\ListClientes::route('/'),
            'create' => Pages\CreateCliente::route('/create'),
            'edit'   => Pages\EditCliente::route('/{record}/edit'),
        ];
    }
}
