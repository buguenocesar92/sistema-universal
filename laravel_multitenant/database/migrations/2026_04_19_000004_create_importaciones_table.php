<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('importaciones', function (Blueprint $table) {
            $table->id();
            $table->string('item')->nullable();
            $table->string('modelo')->nullable();
            $table->string('unidades')->nullable();
            $table->string('pi_numero')->nullable();
            $table->string('empresa')->nullable();
            $table->string('rut')->nullable();
            $table->string('factura')->nullable();
            $table->decimal('costo_china', 10, 2)->default(0);
            $table->string('embarcadero')->nullable();
            $table->string('agente_aduana')->nullable();
            $table->decimal('total_neto', 10, 2)->default(0);
            $table->string('iva_servicio')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('importaciones');
    }
};
