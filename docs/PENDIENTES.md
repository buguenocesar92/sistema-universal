## Generator — Laravel completo (Opción B)

### Problema
generator.py genera solo app/, database/, routes/ pero no el proyecto Laravel base.
laravel_multitenant/ está incompleto — le faltan bootstrap/, public/, resources/, storage/, artisan, package.json.

### Solución propuesta
Agregar en generator.py un paso previo:
1. composer create-project laravel/laravel {output_dir}
2. composer require filament/filament --working-dir={output_dir}
3. php artisan filament:install --panels --working-dir={output_dir}
4. Copiar los archivos generados (app/, database/, routes/) encima
5. Configurar .env automáticamente con los datos de la empresa

### Archivos a modificar
- generator.py — agregar metodo _crear_base_laravel()
- Dockerfile.laravel — ya está correcto, el problema es el input

### Resultado esperado
docker compose -f docker-compose.dev.yml up -d
→ Panel Filament en http://localhost:8080/admin
→ Datos del Excel visibles en el panel

## Generator — Bugs conocidos (pendiente fix)

### formula_parser.py — IFs anidados generan PHP inválido
Estado: DESACTIVADO en generator.py
Ejemplo: =IF(B7<>"",IF(D7="Ingreso",E7,-E7),"") → genera PHP con IF() inválido
Fix requerido: reescribir _expr_a_php() para manejar IFs anidados recursivamente
Archivo: formula_parser.py línea 48 (formula_a_php)

### relations.py — genera métodos duplicados en modelos
Estado: DESACTIVADO en generator.py
Ejemplo: pedidos() declarado 2 veces en Producto.php
Fix requerido: deduplicar métodos antes de escribir el modelo
Archivo: generator.py línea 290 (gen_modelo → rels_str)

### SyntaxWarning: \BackedEnum escape inválido
Estado: solo warning, no rompe nada
Fix requerido: usar r'\BackedEnum' o '\\BackedEnum' correctamente
Archivo: generator.py línea 460
