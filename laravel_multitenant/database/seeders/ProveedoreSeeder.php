<?php

namespace Database\Seeders;

use App\Models\Kraftdo_bd\Proveedore;
use Illuminate\Database\Seeder;

class ProveedoreSeeder extends Seeder
{
    public function run(): void
    {
        Proveedore::factory(10)->create();
        // O datos de ejemplo fijos:
        // Proveedore::create([
            'nombre' => fake()->words(3, true),
            'contacto' => fake()->word(),
            'tipo' => fake()->word(),
            'despacho' => fake()->word(),
            'minimo' => fake()->word(),
            'envio_gratis' => fake()->word(),
            'notas' => fake()->word(),
        // ]);
    }
}
