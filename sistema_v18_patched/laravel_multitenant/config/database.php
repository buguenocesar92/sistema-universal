<?php

return [

    'default' => env('DB_CONNECTION', 'kraftdo_bd'),

    'connections' => [

        // ── KraftDo SpA — BD Maestra (productos, pedidos, caja) ──────────────
        'kraftdo_bd' => [
            'driver'    => 'mysql',
            'host'      => env('DB_HOST', 'mysql'),
            'port'      => env('DB_PORT', '3306'),
            'database'  => env('DB_DATABASE_KRAFTDO', 'kraftdo_bd'),
            'username'  => env('DB_USERNAME_KRAFTDO', env('DB_USERNAME', 'kraftdo')),
            'password'  => env('DB_PASSWORD_KRAFTDO', env('DB_PASSWORD', '')),
            'charset'   => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix'    => '',
            'strict'    => true,
            'engine'    => null,
        ],

        // ── Constructora Adille ───────────────────────────────────────────────
        'adille' => [
            'driver'    => 'mysql',
            'host'      => env('DB_HOST', 'mysql'),
            'port'      => env('DB_PORT', '3306'),
            'database'  => env('DB_DATABASE_ADILLE', 'kraftdo_adille'),
            'username'  => env('DB_USERNAME_ADILLE', env('DB_USERNAME', 'kraftdo')),
            'password'  => env('DB_PASSWORD_ADILLE', env('DB_PASSWORD', '')),
            'charset'   => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix'    => '',
            'strict'    => true,
            'engine'    => null,
        ],

        // ── Extractores Chile Ltda ────────────────────────────────────────────
        'extractores' => [
            'driver'    => 'mysql',
            'host'      => env('DB_HOST', 'mysql'),
            'port'      => env('DB_PORT', '3306'),
            'database'  => env('DB_DATABASE_EXTRACTORES', 'kraftdo_extractores'),
            'username'  => env('DB_USERNAME_EXTRACTORES', env('DB_USERNAME', 'kraftdo')),
            'password'  => env('DB_PASSWORD_EXTRACTORES', env('DB_PASSWORD', '')),
            'charset'   => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix'    => '',
            'strict'    => true,
            'engine'    => null,
        ],


        'test_empresa_steps' => [
            'driver'    => 'mysql',
            'host'      => env('DB_HOST', 'mysql'),
            'port'      => env('DB_PORT', '3306'),
            'database'  => env('DB_DATABASE_TEST_EMPRESA_STEPS', 'kraftdo_test_empresa_steps'),
            'username'  => env('DB_USERNAME', 'kraftdo'),
            'password'  => env('DB_PASSWORD', ''),
            'charset'   => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix'    => '',
            'strict'    => true,
            'engine'    => null,
        ],
    ],

    'migrations' => 'migrations',

    'redis' => [
        'client'  => env('REDIS_CLIENT', 'phpredis'),
        'default' => [
            'host'     => env('REDIS_HOST', 'redis'),
            'password' => env('REDIS_PASSWORD', null),
            'port'     => env('REDIS_PORT', '6379'),
            'database' => env('REDIS_DB', '0'),
        ],
        'cache' => [
            'host'     => env('REDIS_HOST', 'redis'),
            'password' => env('REDIS_PASSWORD', null),
            'port'     => env('REDIS_PORT', '6379'),
            'database' => env('REDIS_CACHE_DB', '1'),
        ],
    ],

];
