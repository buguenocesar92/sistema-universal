<?php

namespace App\Filament\Resources;

use App\Filament\Resources\LiquidacionResource\Pages;
use App\Models\Liquidacion;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class LiquidacionResource extends Resource
{
    protected static ?string $model = Liquidacion::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Liquidacion';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('codigo')
                ->label('Codigo').nullable(),
            Forms\Components\TextInput::make('obra')
                ->label('Obra').nullable(),
            Forms\Components\TextInput::make('trabajador')
                ->label('Trabajador').nullable(),
            Forms\Components\TextInput::make('sueldo_base')
                ->label('Sueldo base').nullable(),
            Forms\Components\TextInput::make('dias_laborales')
                ->label('Dias laborales')
                ->numeric().required(),
            Forms\Components\TextInput::make('dias_trabajados')
                ->label('Dias trabajados')
                ->numeric().required(),
            Forms\Components\TextInput::make('faltas')
                ->label('Faltas').nullable(),
            Forms\Components\TextInput::make('valor_dia')
                ->label('Valor dia').nullable(),
            Forms\Components\TextInput::make('descuento_faltas')
                ->label('Descuento faltas')
                ->numeric().required(),
            Forms\Components\TextInput::make('a_pagar')
                ->label('A pagar').nullable(),
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
                Tables\Columns\TextColumn::make('codigo')
                    ->label('Codigo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('obra')
                    ->label('Obra')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('trabajador')
                    ->label('Trabajador')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('sueldo_base')
                    ->label('Sueldo base')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('dias_laborales')
                    ->label('Dias laborales')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('dias_trabajados')
                    ->label('Dias trabajados')
                    ->numeric()->sortable()->searchable(),
                Tables\Columns\TextColumn::make('faltas')
                    ->label('Faltas')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('valor_dia')
                    ->label('Valor dia')
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
            'index'  => Pages\ListLiquidacions::route('/'),
            'create' => Pages\CreateLiquidacion::route('/create'),
            'edit'   => Pages\EditLiquidacion::route('/{record}/edit'),
        ];
    }
}
