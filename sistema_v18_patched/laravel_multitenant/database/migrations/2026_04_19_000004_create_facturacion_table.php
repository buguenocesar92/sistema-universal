<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('facturacion', function (Blueprint $table) {
            $table->id();
            $table->string('concepto')->nullable();
            $table->string('abril')->nullable();
            $table->string('mayo')->nullable();
            $table->string('julio')->nullable();
            $table->string('agosto')->nullable();
            $table->string('septiembre')->nullable();
            $table->string('octubre')->nullable();
            $table->string('noviembre')->nullable();
            $table->string('diciembre')->nullable();
            $table->string('enero')->nullable();
            $table->string('febrero')->nullable();
            $table->string('marzo')->nullable();
            $table->string('acumulado')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('facturacion');
    }
};
