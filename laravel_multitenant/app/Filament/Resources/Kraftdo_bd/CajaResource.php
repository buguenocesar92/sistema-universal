<?php

namespace App\Filament\Resources\Kraftdo_bd;

use App\Filament\Resources\CajaResource\Pages;
use App\Models\Kraftdo_bd\Caja;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class CajaResource extends Resource
{
    protected static ?string $model = Caja::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Caja';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('numero')
                ->label('Numero').nullable(),
            Forms\Components\DatePicker::make('fecha')
                ->label('Fecha').nullable(),
            Forms\Components\TextInput::make('tipo')
                ->label('Tipo').nullable(),
            Forms\Components\TextInput::make('subcategoria')
                ->label('Subcategoria').nullable(),
            Forms\Components\TextInput::make('monto')
                ->label('Monto')
                ->numeric().required(),
            Forms\Components\TextInput::make('saldo')
                ->label('Saldo')
                ->numeric().required(),
            Forms\Components\TextInput::make('id_pedido')
                ->label('Id pedido').nullable(),
            Forms\Components\Textarea::make('detalle')
                ->label('Detalle').nullable(),
            Forms\Components\Select::make('id_pedido')
                ->label('Id pedido')
                ->relationship('id_pedido', 'id_pedido')
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
                Tables\Columns\TextColumn::make('tipo')
                    ->label('Tipo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('subcategoria')
                    ->label('Subcategoria')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('monto')
                    ->label('Monto')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('saldo')
                    ->label('Saldo')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('id_pedido')
                    ->label('Id pedido')
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
            'index'  => Pages\ListCajas::route('/'),
            'create' => Pages\CreateCaja::route('/create'),
            'edit'   => Pages\EditCaja::route('/{record}/edit'),
        ];
    }
}
