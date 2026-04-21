<?php

namespace App\Filament\Resources;

use App\Filament\Resources\ProductoResource\Pages;
use App\Models\Producto;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class ProductoResource extends Resource
{
    protected static ?string $model = Producto::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Productos';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('sku')
                ->label('Sku').nullable(),
            Forms\Components\TextInput::make('categoria')
                ->label('Categoria').nullable(),
            Forms\Components\TextInput::make('nombre')
                ->label('Nombre').nullable(),
            Forms\Components\TextInput::make('variante')
                ->label('Variante').nullable(),
            Forms\Components\TextInput::make('costo_insumo')
                ->label('Costo insumo')
                ->numeric().required(),
            Forms\Components\TextInput::make('costo_prod')
                ->label('Costo prod')
                ->numeric().required(),
            Forms\Components\TextInput::make('costo_total')
                ->label('Costo total')
                ->numeric().required(),
            Forms\Components\TextInput::make('margen')
                ->label('Margen')
                ->numeric().required(),
            Forms\Components\TextInput::make('precio_unit')
                ->label('Precio unit')
                ->numeric().required(),
            Forms\Components\TextInput::make('precio_mayor')
                ->label('Precio mayor')
                ->numeric().required(),
            Forms\Components\Select::make('costo_insumo')
                ->label('Costo insumo')
                ->relationship('costo_insumo', 'id')
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
                Tables\Columns\TextColumn::make('sku')
                    ->label('Sku')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('categoria')
                    ->label('Categoria')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('nombre')
                    ->label('Nombre')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('variante')
                    ->label('Variante')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('costo_insumo')
                    ->label('Costo insumo')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('costo_prod')
                    ->label('Costo prod')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('costo_total')
                    ->label('Costo total')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('margen')
                    ->label('Margen')
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
            'index'  => Pages\ListProductos::route('/'),
            'create' => Pages\CreateProducto::route('/create'),
            'edit'   => Pages\EditProducto::route('/{record}/edit'),
        ];
    }
}
