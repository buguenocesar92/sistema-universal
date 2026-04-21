<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('extractores_ventas', function (Blueprint $table) {
            $table->id();
            $table->string('item')->nullable();
            $table->string('contacto')->nullable();
            $table->string('tipo_estructura')->nullable();
            $table->string('empresa')->nullable();
            $table->string('rut')->nullable();
            $table->string('factura')->nullable();
            $table->timestamp('fecha')->nullable();
            $table->string('modelo')->nullable();
            $table->integer('cantidad')->default(0);
            $table->string('neto')->nullable();
            $table->string('neto_dsto')->nullable();
            $table->decimal('iva', 5, 4)->default(0);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('ventas');
    }
};
