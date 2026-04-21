<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('caja', function (Blueprint $table) {
            $table->id();
            $table->timestamp('fecha')->nullable();
            $table->string('tipo')->nullable();
            $table->string('subcategoria')->nullable();
            $table->decimal('monto', 10, 2)->default(0);
            $table->decimal('saldo', 10, 2)->default(0);
            $table->string('id_pedido')->nullable();
            $table->text('detalle')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('caja');
    }
};
