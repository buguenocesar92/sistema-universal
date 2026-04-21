<?php

namespace Database\Seeders;

use App\Models\Facturacion;
use Illuminate\Database\Seeder;

class FacturacionSeeder extends Seeder
{
    public function run(): void
    {
        Facturacion::factory(10)->create();
        // O datos de ejemplo fijos:
        // Facturacion::create([
            'concepto' => fake()->word(),
            'abril' => fake()->word(),
            'mayo' => fake()->word(),
            'julio' => fake()->word(),
            'agosto' => fake()->word(),
            'septiembre' => fake()->word(),
            'octubre' => fake()->word(),
            'noviembre' => fake()->word(),
        // ]);
    }
}
