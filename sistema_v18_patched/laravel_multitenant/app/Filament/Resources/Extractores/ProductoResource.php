<?php

namespace App\Filament\Resources\Extractores;

use App\Filament\Resources\ProductoResource\Pages;
use App\Models\Extractores\Producto;
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
            Forms\Components\TextInput::make('modelo')
                ->label('Modelo').nullable(),
            Forms\Components\TextInput::make('sku')
                ->label('Sku').nullable(),
            Forms\Components\TextInput::make('precio')
                ->label('Precio')
                ->numeric().required(),
            Forms\Components\TextInput::make('panel')
                ->label('Panel').nullable(),
            Forms\Components\TextInput::make('flujo_aire')
                ->label('Flujo aire').nullable(),
            Forms\Components\TextInput::make('cobertura')
                ->label('Cobertura').nullable(),
            Forms\Components\TextInput::make('motor')
                ->label('Motor').nullable(),
            Forms\Components\TextInput::make('garantia')
                ->label('Garantia').nullable(),
            Forms\Components\TextInput::make('aplicaciones')
                ->label('Aplicaciones').nullable(),
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
                Tables\Columns\TextColumn::make('modelo')
                    ->label('Modelo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('sku')
                    ->label('Sku')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('precio')
                    ->label('Precio')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('panel')
                    ->label('Panel')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('flujo_aire')
                    ->label('Flujo aire')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('cobertura')
                    ->label('Cobertura')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('motor')
                    ->label('Motor')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('garantia')
                    ->label('Garantia')
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
            'index'  => Pages\ListProductos::route('/'),
            'create' => Pages\CreateProducto::route('/create'),
            'edit'   => Pages\EditProducto::route('/{record}/edit'),
        ];
    }
}
