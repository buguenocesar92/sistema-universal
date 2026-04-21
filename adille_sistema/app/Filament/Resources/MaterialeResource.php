<?php

namespace App\Filament\Resources;

use App\Filament\Resources\MaterialeResource\Pages;
use App\Models\Materiale;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class MaterialeResource extends Resource
{
    protected static ?string $model = Materiale::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Materiales';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('obra')
                ->label('Obra').nullable(),
            Forms\Components\DatePicker::make('fecha')
                ->label('Fecha').nullable(),
            Forms\Components\Textarea::make('detalle')
                ->label('Detalle').nullable(),
            Forms\Components\TextInput::make('costo_gym')
                ->label('Costo gym')
                ->numeric().required(),
            Forms\Components\TextInput::make('costo_nogales')
                ->label('Costo nogales')
                ->numeric().required(),
            Forms\Components\TextInput::make('gastos_generales')
                ->label('Gastos generales').nullable(),
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
                Tables\Columns\TextColumn::make('obra')
                    ->label('Obra')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('fecha')
                    ->label('Fecha')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('detalle')
                    ->label('Detalle')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('costo_gym')
                    ->label('Costo gym')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('costo_nogales')
                    ->label('Costo nogales')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('gastos_generales')
                    ->label('Gastos generales')
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
            'index'  => Pages\ListMateriales::route('/'),
            'create' => Pages\CreateMateriale::route('/create'),
            'edit'   => Pages\EditMateriale::route('/{record}/edit'),
        ];
    }
}
