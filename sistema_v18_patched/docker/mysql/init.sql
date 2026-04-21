-- KraftDo Sistema Universal — inicialización MySQL
-- Crea las 3 bases de datos separadas con el mismo usuario

CREATE DATABASE IF NOT EXISTS kraftdo_bd
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS kraftdo_adille
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS kraftdo_extractores
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- También la BD de n8n
CREATE DATABASE IF NOT EXISTS n8n
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Dar permisos al usuario kraftdo sobre todas las BDs
GRANT ALL PRIVILEGES ON kraftdo_bd.*         TO 'kraftdo'@'%';
GRANT ALL PRIVILEGES ON kraftdo_adille.*     TO 'kraftdo'@'%';
GRANT ALL PRIVILEGES ON kraftdo_extractores.* TO 'kraftdo'@'%';
GRANT ALL PRIVILEGES ON n8n.*                TO 'kraftdo'@'%';


CREATE DATABASE IF NOT EXISTS kraftdo_gym_flo
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON kraftdo_gym_flo.* TO 'kraftdo'@'%';

FLUSH PRIVILEGES;
