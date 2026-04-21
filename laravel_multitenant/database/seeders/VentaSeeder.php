<?php

namespace Database\Seeders;

use App\Models\Extractores\Venta;
use Illuminate\Database\Seeder;

class VentaSeeder extends Seeder
{
    public function run(): void
    {
        Venta::factory(10)->create();
        // O datos de ejemplo fijos:
        // Venta::create([
            'item' => fake()->word(),
            'contacto' => fake()->word(),
            'tipo_estructura' => fake()->word(),
            'empresa' => fake()->word(),
            'rut' => fake()->word(),
            'factura' => fake()->word(),
            'fecha' => fake()->dateTimeBetween('-1 year', 'now'),
            'modelo' => fake()->word(),
        // ]);
    }
}
