<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('proveedores', function (Blueprint $table) {
            $table->id();
            $table->string('nombre')->nullable();
            $table->string('contacto')->nullable();
            $table->string('tipo')->nullable();
            $table->string('despacho')->nullable();
            $table->string('minimo')->nullable();
            $table->string('envio_gratis')->nullable();
            $table->text('notas')->nullable();
            $table->string('actualizado')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('proveedores');
    }
};
