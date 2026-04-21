<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('materiales', function (Blueprint $table) {
            $table->id();
            $table->string('obra')->nullable();
            $table->timestamp('fecha')->nullable();
            $table->text('detalle')->nullable();
            $table->decimal('costo_gym', 10, 2)->default(0);
            $table->decimal('costo_nogales', 10, 2)->default(0);
            $table->string('gastos_generales')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('materiales');
    }
};
