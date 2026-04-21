<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('bencina', function (Blueprint $table) {
            $table->id();
            $table->timestamp('fecha')->nullable();
            $table->string('vehiculo')->nullable();
            $table->string('obra')->nullable();
            $table->decimal('monto', 10, 2)->default(0);
            $table->string('litros')->nullable();
            $table->string('km')->nullable();
            $table->text('detalle')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('bencina');
    }
};
