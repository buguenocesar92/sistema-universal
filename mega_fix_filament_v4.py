#!/usr/bin/env python3
"""
Mega fix para compatibilidad Filament v3 → v4
Aplica todos los parches identificados en la sesión de debug.
Uso: python3 mega_fix_filament_v4.py /tmp/kraftdo_bd_test
"""

import glob, re, sys, os

def fix_resources(base):
    print("\n=== RESOURCES ===")
    for f in glob.glob(f'{base}/app/Filament/Resources/*.php'):
        txt = open(f).read()
        original = txt

        # 1. Add use BackedEnum
        if 'use BackedEnum;' not in txt:
            txt = txt.replace('namespace App\\Filament\\Resources;',
                              'namespace App\\Filament\\Resources;\n\nuse BackedEnum;')

        # 2. navigationIcon type
        txt = txt.replace('protected static ?string $navigationIcon',
                          'protected static string | BackedEnum | null $navigationIcon')

        # 3. Form → Schema
        txt = txt.replace('use Filament\\Forms\\Form;', 'use Filament\\Schemas\\Schema;')
        txt = txt.replace('public static function form(Form $form): Form',
                          'public static function form(Schema $form): Schema')

        # 4. EditAction / DeleteAction
        txt = re.sub(r'[\\A-Za-z]*EditAction::make\(\)',
                     r'\\Filament\\Actions\\EditAction::make()', txt)
        txt = re.sub(r'[\\A-Za-z]*DeleteAction::make\(\)(?!\s*\])',
                     r'\\Filament\\Actions\\DeleteAction::make()', txt)

        # 5. BulkActionGroup
        txt = re.sub(r'[\\A-Za-z]*BulkActionGroup::make\(\[',
                     r'\\Filament\\Actions\\BulkActionGroup::make([', txt)

        # 6. DeleteBulkAction
        txt = re.sub(r'[\\A-Za-z]*DeleteBulkAction::make\(\)',
                     r'\\Filament\\Actions\\DeleteBulkAction::make()', txt)

        if txt != original:
            open(f, 'w').write(txt)
            print(f"  ✅ {os.path.basename(f)}")
        else:
            print(f"  — {os.path.basename(f)} (sin cambios)")


def fix_pages(base):
    print("\n=== PAGES ===")
    for f in glob.glob(f'{base}/app/Filament/Pages/*.php'):
        txt = open(f).read()
        original = txt

        if 'use BackedEnum;' not in txt:
            txt = txt.replace('namespace App\\Filament\\Pages;',
                              'namespace App\\Filament\\Pages;\n\nuse BackedEnum;')
        txt = txt.replace('protected static ?string $navigationIcon',
                          'protected static string | BackedEnum | null $navigationIcon')

        if txt != original:
            open(f, 'w').write(txt)
            print(f"  ✅ {os.path.basename(f)}")
        else:
            print(f"  — {os.path.basename(f)} (sin cambios)")


def fix_models(base):
    print("\n=== MODELS ===")
    for f in glob.glob(f'{base}/app/Models/*.php'):
        txt = open(f).read()
        original = txt

        # 1. Eliminar $casts vacíos
        txt = re.sub(r'protected \$casts = \[\s*,?\s*\];', '', txt)

        # 2. Eliminar métodos duplicados
        seen = set()
        def dedup(m):
            name = m.group(1)
            if name in seen:
                return ''
            seen.add(name)
            return m.group(0)
        txt = re.sub(r'public function (\w+)\([^)]*\)\s*\{[^}]*\}',
                     dedup, txt, flags=re.DOTALL)

        # 3. Fórmulas Excel inválidas en accessors
        txt = re.sub(
            r'return \(\$this->fecha<>""\) \? \(IF\([^)]+\) : \([^)]+\),""\);',
            r'return ($this->fecha != "") ? ($this->tipo === "Ingreso" ? $this->monto : -$this->monto) : "";',
            txt
        )

        if txt != original:
            open(f, 'w').write(txt)
            print(f"  ✅ {os.path.basename(f)}")
        else:
            print(f"  — {os.path.basename(f)} (sin cambios)")


def fix_observers(base):
    print("\n=== OBSERVERS ===")
    for f in glob.glob(f'{base}/app/Observers/*.php'):
        txt = open(f).read()
        original = txt

        # Eliminar backslashes incorrectos antes de $model
        txt = txt.replace('\\$model', '$model')

        if txt != original:
            open(f, 'w').write(txt)
            print(f"  ✅ {os.path.basename(f)}")
        else:
            print(f"  — {os.path.basename(f)} (sin cambios)")


def fix_providers(base):
    print("\n=== PROVIDERS ===")
    f = f'{base}/app/Providers/AppServiceProvider.php'
    if not os.path.exists(f):
        print("  — AppServiceProvider no encontrado")
        return

    txt = open(f).read()
    # Si tiene modelos plurales que no existen, limpiar boot()
    if 'Productos::observe' in txt or 'Clientes::observe' in txt:
        txt = re.sub(r'public function boot\(\): void\s*\{[^}]*\}',
                     'public function boot(): void {}', txt, flags=re.DOTALL)
        open(f, 'w').write(txt)
        print(f"  ✅ AppServiceProvider.php (boot() limpiado)")
    else:
        print(f"  — AppServiceProvider.php (sin cambios)")


def remove_junk_widgets(base):
    print("\n=== WIDGETS (limpiar duplicados) ===")
    junk = [
        f'{base}/app/Filament/Widgets/KraftDoStatsWidget.php',
    ]
    for f in junk:
        if os.path.exists(f):
            # Verificar que tiene namespace corrupto
            txt = open(f).read()
            if 'namespace App\\Filament\\Widgets\\;' in txt or 'namespace App\\Filament\\Widgets\n' in txt:
                os.remove(f)
                print(f"  🗑️  {os.path.basename(f)} eliminado (namespace corrupto)")
            else:
                print(f"  — {os.path.basename(f)} (OK, no eliminado)")


if __name__ == '__main__':
    base = sys.argv[1] if len(sys.argv) > 1 else '/tmp/kraftdo_bd_test'
    print(f"🔧 Aplicando mega-fix en: {base}")

    fix_resources(base)
    fix_pages(base)
    fix_models(base)
    fix_observers(base)
    fix_providers(base)
    remove_junk_widgets(base)

    print("\n✅ Mega-fix aplicado. Ejecutar:")
    print(f"  cd {base} && php artisan view:clear && php artisan config:clear")
