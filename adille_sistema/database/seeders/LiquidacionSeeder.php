<?php

namespace Database\Seeders;

use App\Models\Liquidacion;
use Illuminate\Database\Seeder;

class LiquidacionSeeder extends Seeder
{
    public function run(): void
    {
        Liquidacion::factory(10)->create();
        // O datos de ejemplo fijos:
        // Liquidacion::create([
            'codigo' => strtoupper(fake()->lexify('???##')),
            'obra' => fake()->word(),
            'trabajador' => fake()->word(),
            'sueldo_base' => fake()->word(),
            'dias_laborales' => fake()->numberBetween(1000, 100000),
            'dias_trabajados' => fake()->numberBetween(1000, 100000),
            'faltas' => fake()->word(),
            'valor_dia' => fake()->word(),
        // ]);
    }
}
