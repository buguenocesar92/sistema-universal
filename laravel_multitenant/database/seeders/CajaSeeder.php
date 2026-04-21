<?php

namespace Database\Seeders;

use App\Models\Kraftdo_bd\Caja;
use Illuminate\Database\Seeder;

class CajaSeeder extends Seeder
{
    public function run(): void
    {
        Caja::factory(10)->create();
        // O datos de ejemplo fijos:
        // Caja::create([
            'fecha' => fake()->dateTimeBetween('-1 year', 'now'),
            'tipo' => fake()->word(),
            'subcategoria' => fake()->word(),
            'monto' => fake()->numberBetween(1000, 100000),
            'saldo' => fake()->numberBetween(1000, 100000),
            'id_pedido' => fake()->word(),
            'detalle' => fake()->word(),
        // ]);
    }
}
