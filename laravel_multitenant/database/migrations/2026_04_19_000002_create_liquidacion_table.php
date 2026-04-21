<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('liquidacion', function (Blueprint $table) {
            $table->id();
            $table->string('codigo', 50)->nullable();
            $table->string('obra')->nullable();
            $table->string('trabajador')->nullable();
            $table->string('sueldo_base')->nullable();
            $table->integer('dias_laborales')->default(0);
            $table->integer('dias_trabajados')->default(0);
            $table->string('faltas')->nullable();
            $table->string('valor_dia')->nullable();
            $table->decimal('descuento_faltas', 5, 4)->default(0);
            $table->string('a_pagar')->nullable();
            $table->string('quincena_pagada')->nullable();
            $table->decimal('saldo', 10, 2)->default(0);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('liquidacion');
    }
};
