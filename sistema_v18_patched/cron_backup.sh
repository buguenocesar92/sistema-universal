#!/bin/bash
# cron_backup.sh — backup diario automatico
# Cron: 0 3 * * * /opt/kraftdo-sistema/cron_backup.sh >> /var/log/kraftdo_backup.log 2>&1

# PATH explicito porque cron no lo hereda
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

FECHA=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$FECHA] Iniciando backup diario"

# -T evita requerir TTY (crucial para cron)
docker compose exec -T worker python3 -c "
from jobs.queue import JobQueue
q = JobQueue()
job_id = q.enqueue('backup', {})
print(f'Backup encolado: {job_id}')
" < /dev/null

if [ $? -eq 0 ]; then
    echo "[$FECHA] Backup encolado exitosamente"
else
    # Fallback: ejecutar backup directamente si la cola falla
    echo "[$FECHA] Cola fallo, ejecutando backup directo..."
    docker compose exec -T worker python3 jobs/backup.py < /dev/null
fi

echo "[$FECHA] Finalizado"
echo "---"
