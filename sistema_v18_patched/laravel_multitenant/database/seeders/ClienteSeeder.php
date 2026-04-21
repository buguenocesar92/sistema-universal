<?php

namespace Database\Seeders;

use App\Models\Kraftdo_bd\Cliente;
use Illuminate\Database\Seeder;

class ClienteSeeder extends Seeder
{
    public function run(): void
    {
        Cliente::factory(10)->create();
        // O datos de ejemplo fijos:
        // Cliente::create([
            'nombre' => fake()->words(3, true),
            'tipo' => fake()->word(),
            'whatsapp' => fake()->phoneNumber(),
            'ciudad' => fake()->word(),
            'correo' => fake()->email(),
            'rubro' => fake()->word(),
            'canal' => fake()->word(),
        // ]);
    }
}
