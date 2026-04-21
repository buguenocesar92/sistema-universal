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
