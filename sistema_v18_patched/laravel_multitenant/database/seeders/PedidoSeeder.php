<?php

namespace Database\Seeders;

use App\Models\Kraftdo_bd\Pedido;
use Illuminate\Database\Seeder;

class PedidoSeeder extends Seeder
{
    public function run(): void
    {
        Pedido::factory(10)->create();
        // O datos de ejemplo fijos:
        // Pedido::create([
            'id_pedido' => fake()->word(),
            'fecha' => fake()->dateTimeBetween('-1 year', 'now'),
            'id_cliente' => fake()->name(),
            'cliente' => fake()->name(),
            'sku' => strtoupper(fake()->lexify('???##')),
            'producto' => fake()->words(3, true),
            'cantidad' => fake()->numberBetween(1000, 100000),
            'precio_unit' => fake()->numberBetween(1000, 100000),
        // ]);
    }
}
