<?php

namespace Database\Seeders;

use App\Models\Adille\Bencina;
use Illuminate\Database\Seeder;

class BencinaSeeder extends Seeder
{
    public function run(): void
    {
        Bencina::factory(10)->create();
        // O datos de ejemplo fijos:
        // Bencina::create([
            'fecha' => fake()->dateTimeBetween('-1 year', 'now'),
            'vehiculo' => fake()->word(),
            'obra' => fake()->word(),
            'monto' => fake()->numberBetween(1000, 100000),
            'litros' => fake()->word(),
            'km' => fake()->word(),
            'detalle' => fake()->word(),
        // ]);
    }
}
