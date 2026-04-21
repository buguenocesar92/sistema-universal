<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('kraftdo_bd_clientes', function (Blueprint $table) {
            $table->id();
            $table->string('nombre')->nullable();
            $table->string('tipo')->nullable();
            $table->string('whatsapp', 20)->nullable();
            $table->string('ciudad')->nullable();
            $table->string('correo')->nullable();
            $table->string('rubro')->nullable();
            $table->string('canal')->nullable();
            $table->timestamp('fecha')->nullable();
            $table->text('notas')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('clientes');
    }
};
