<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('productos', function (Blueprint $table) {
            $table->id();
            $table->string('sku', 50)->nullable();
            $table->string('categoria')->nullable();
            $table->string('nombre')->nullable();
            $table->string('variante')->nullable();
            $table->decimal('costo_insumo', 10, 2)->default(0);
            $table->decimal('costo_prod', 10, 2)->default(0);
            $table->decimal('costo_total', 10, 2)->default(0);
            $table->decimal('margen', 5, 4)->default(0);
            $table->decimal('precio_unit', 10, 2)->default(0);
            $table->decimal('precio_mayor', 10, 2)->default(0);
            $table->integer('stock')->default(0);
            $table->integer('dias_prod')->default(0);
            $table->index('sku');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('productos');
    }
};
