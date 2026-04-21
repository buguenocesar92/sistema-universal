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
            $table->string('modelo')->nullable();
            $table->string('sku', 50)->nullable();
            $table->decimal('precio', 10, 2)->default(0);
            $table->string('panel')->nullable();
            $table->string('flujo_aire')->nullable();
            $table->string('cobertura')->nullable();
            $table->string('motor')->nullable();
            $table->string('garantia')->nullable();
            $table->string('aplicaciones')->nullable();
            $table->index('sku');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('productos');
    }
};
