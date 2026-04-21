<?php

namespace App\Filament\Resources\Extractores;

use App\Filament\Resources\FeriaResource\Pages;
use App\Models\Extractores\Feria;
use Filament\Forms;
use Filament\Forms\Form;
use Filament\Resources\Resource;
use Filament\Tables;
use Filament\Tables\Table;

class FeriaResource extends Resource
{
    protected static ?string $model = Feria::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = 'Ferias';

    public static function form(Form $form): Form
    {
        return $form->schema([
            Forms\Components\TextInput::make('evento')
                ->label('Evento').nullable(),
            Forms\Components\DatePicker::make('fecha')
                ->label('Fecha').nullable(),
            Forms\Components\TextInput::make('lugar')
                ->label('Lugar').nullable(),
            Forms\Components\TextInput::make('region')
                ->label('Region').nullable(),
            Forms\Components\TextInput::make('tipo')
                ->label('Tipo').nullable(),
            Forms\Components\TextInput::make('relevancia')
                ->label('Relevancia').nullable(),
            Forms\Components\TextInput::make('publico')
                ->label('Publico').nullable(),
            Forms\Components\TextInput::make('costo_stand')
                ->label('Costo stand')
                ->numeric().required(),
            Forms\Components\TextInput::make('contacto')
                ->label('Contacto').nullable(),
            Forms\Components\TextInput::make('estado')
                ->label('Estado').nullable(),
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
                Tables\Columns\TextColumn::make('evento')
                    ->label('Evento')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('fecha')
                    ->label('Fecha')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('lugar')
                    ->label('Lugar')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('region')
                    ->label('Region')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('tipo')
                    ->label('Tipo')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('relevancia')
                    ->label('Relevancia')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('publico')
                    ->label('Publico')
                    ->sortable()->searchable(),
                Tables\Columns\TextColumn::make('costo_stand')
                    ->label('Costo stand')
                    ->numeric()->sortable()->searchable(),
            ])
            ->filters([
                Tables\Filters\SelectFilter::make('estado')
                    ->options(fn() => \App\Models\Feria::distinct()->pluck('estado', 'estado')->toArray()),
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
            'index'  => Pages\ListFerias::route('/'),
            'create' => Pages\CreateFeria::route('/create'),
            'edit'   => Pages\EditFeria::route('/{record}/edit'),
        ];
    }
}
