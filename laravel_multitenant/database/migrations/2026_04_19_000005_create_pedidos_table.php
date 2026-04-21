<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('pedidos', function (Blueprint $table) {
            $table->id();
            $table->string('id_pedido')->nullable();
            $table->timestamp('fecha')->nullable();
            $table->string('id_cliente')->nullable();
            $table->string('cliente')->nullable();
            $table->string('sku', 50)->nullable();
            $table->string('producto')->nullable();
            $table->integer('cantidad')->default(0);
            $table->decimal('precio_unit', 10, 2)->default(0);
            $table->decimal('costo_unit', 10, 2)->default(0);
            $table->decimal('total', 10, 2)->default(0);
            $table->decimal('ganancia', 10, 2)->default(0);
            $table->decimal('margen', 5, 4)->default(0);
            $table->index('sku');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('pedidos');
    }
};
