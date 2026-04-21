<?php

namespace App\Filament\Resources;

use App\Filament\Resources\FacturacionResource\Pages;
use App\Models\Facturacion;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class FacturacionResource extends Resource
{
    protected static ?string $model = Facturacion::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Facturacion';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('concepto')
                ->label('Concepto').nullable(),
            Forms\Components\TextInput::make('abril')
                ->label('Abril').nullable(),
            Forms\Components\TextInput::make('mayo')
                ->label('Mayo').nullable(),
            Forms\Components\TextInput::make('julio')
                ->label('Julio').nullable(),
            Forms\Components\TextInput::make('agosto')
                ->label('Agosto').nullable(),
            Forms\Components\TextInput::make('septiembre')
                ->label('Septiembre').nullable(),
            Forms\Components\TextInput::make('octubre')
                ->label('Octubre').nullable(),
            Forms\Components\TextInput::make('noviembre')
                ->label('Noviembre').nullable(),
            Forms\Components\TextInput::make('diciembre')
                ->label('Diciembre').nullable(),
            Forms\Components\TextInput::make('enero')
                ->label('Enero').nullable(),
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
                Tables\Columns\TextColumn::make('concepto')
                    ->label('Concepto')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('abril')
                    ->label('Abril')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('mayo')
                    ->label('Mayo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('julio')
                    ->label('Julio')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('agosto')
                    ->label('Agosto')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('septiembre')
                    ->label('Septiembre')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('octubre')
                    ->label('Octubre')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('noviembre')
                    ->label('Noviembre')
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
            'index'  => Pages\ListFacturacions::route('/'),
            'create' => Pages\CreateFacturacion::route('/create'),
            'edit'   => Pages\EditFacturacion::route('/{record}/edit'),
        ];
    }
}
