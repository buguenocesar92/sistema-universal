<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('kraftdo_bd_insumos', function (Blueprint $table) {
            $table->id();
            $table->string('nombre')->nullable();
            $table->string('unidad')->nullable();
            $table->integer('stock')->default(0);
            $table->string('stock_min')->nullable();
            $table->string('alerta')->nullable();
            $table->decimal('costo', 10, 2)->default(0);
            $table->string('proveedor')->nullable();
            $table->string('actualizado')->nullable();
            $table->text('notas')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('insumos');
    }
};
