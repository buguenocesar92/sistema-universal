<?php

namespace App\Filament\Resources;

use App\Filament\Resources\PedidoResource\Pages;
use App\Models\Pedido;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class PedidoResource extends Resource
{
    protected static ?string $model = Pedido::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Pedidos';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('id_pedido')
                ->label('Id pedido').nullable(),
            Forms\Components\DatePicker::make('fecha')
                ->label('Fecha').nullable(),
            Forms\Components\TextInput::make('id_cliente')
                ->label('Id cliente').nullable(),
            Forms\Components\TextInput::make('cliente')
                ->label('Cliente').nullable(),
            Forms\Components\TextInput::make('sku')
                ->label('Sku').nullable(),
            Forms\Components\TextInput::make('producto')
                ->label('Producto').nullable(),
            Forms\Components\TextInput::make('cantidad')
                ->label('Cantidad')
                ->numeric().required(),
            Forms\Components\TextInput::make('precio_unit')
                ->label('Precio unit')
                ->numeric().required(),
            Forms\Components\TextInput::make('costo_unit')
                ->label('Costo unit')
                ->numeric().required(),
            Forms\Components\TextInput::make('total')
                ->label('Total')
                ->numeric().required(),
            Forms\Components\Select::make('id_cliente')
                ->label('Id cliente')
                ->relationship('id_cliente', 'id')
                ->searchable()->preload()->nullable(),
            Forms\Components\Select::make('cliente')
                ->label('Cliente')
                ->relationship('cliente', 'id')
                ->searchable()->preload()->nullable(),
            Forms\Components\Select::make('sku')
                ->label('Sku')
                ->relationship('sku', 'sku')
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
                Tables\Columns\TextColumn::make('id_pedido')
                    ->label('Id pedido')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('fecha')
                    ->label('Fecha')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('id_cliente')
                    ->label('Id cliente')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('cliente')
                    ->label('Cliente')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('sku')
                    ->label('Sku')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('producto')
                    ->label('Producto')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('cantidad')
                    ->label('Cantidad')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('precio_unit')
                    ->label('Precio unit')
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
            'index'  => Pages\ListPedidos::route('/'),
            'create' => Pages\CreatePedido::route('/create'),
            'edit'   => Pages\EditPedido::route('/{record}/edit'),
        ];
    }
}
