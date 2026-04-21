<?php

namespace Database\Seeders;

use App\Models\Extractores\Importacione;
use Illuminate\Database\Seeder;

class ImportacioneSeeder extends Seeder
{
    public function run(): void
    {
        Importacione::factory(10)->create();
        // O datos de ejemplo fijos:
        // Importacione::create([
            'item' => fake()->word(),
            'modelo' => fake()->word(),
            'unidades' => fake()->word(),
            'pi_numero' => fake()->word(),
            'empresa' => fake()->word(),
            'rut' => fake()->word(),
            'factura' => fake()->word(),
            'costo_china' => fake()->numberBetween(1000, 100000),
        // ]);
    }
}
