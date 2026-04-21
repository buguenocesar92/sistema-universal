<?php

namespace Database\Seeders;

use App\Models\Materiale;
use Illuminate\Database\Seeder;

class MaterialeSeeder extends Seeder
{
    public function run(): void
    {
        Materiale::factory(10)->create();
        // O datos de ejemplo fijos:
        // Materiale::create([
            'obra' => fake()->word(),
            'fecha' => fake()->dateTimeBetween('-1 year', 'now'),
            'detalle' => fake()->word(),
            'costo_gym' => fake()->numberBetween(1000, 100000),
            'costo_nogales' => fake()->numberBetween(1000, 100000),
            'gastos_generales' => fake()->word(),
        // ]);
    }
}
