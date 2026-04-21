<?php

namespace Database\Seeders;

use App\Models\Extractores\Stock;
use Illuminate\Database\Seeder;

class StockSeeder extends Seeder
{
    public function run(): void
    {
        Stock::factory(10)->create();
        // O datos de ejemplo fijos:
        // Stock::create([
            'modelo' => fake()->word(),
            'importacion' => fake()->word(),
            'ventas' => fake()->word(),
            'promociones' => fake()->word(),
            'stock_disponible' => fake()->word(),
        // ]);
    }
}
