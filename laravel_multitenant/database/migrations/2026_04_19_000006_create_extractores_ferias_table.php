<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('extractores_ferias', function (Blueprint $table) {
            $table->id();
            $table->string('evento')->nullable();
            $table->timestamp('fecha')->nullable();
            $table->string('lugar')->nullable();
            $table->string('region')->nullable();
            $table->string('tipo')->nullable();
            $table->string('relevancia')->nullable();
            $table->string('publico')->nullable();
            $table->decimal('costo_stand', 10, 2)->default(0);
            $table->string('contacto')->nullable();
            $table->string('estado')->nullable();
            $table->index('estado');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('ferias');
    }
};
