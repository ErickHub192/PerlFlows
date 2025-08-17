#!/bin/bash

# 🔥 QYRAL AUTO LOG CLEANER - Se ejecuta cada 10 segundos
# Usage: ./auto_clear_logs.sh &

echo "🤖 AUTO LOG CLEANER INICIADO - Limpieza cada 10 segundos"
echo "💀 Para detener: Ctrl+C o kill -9 $$"
echo ""

while true; do
    echo "🧹 $(date '+%H:%M:%S') - Limpiando logs..."
    
    # Clear logs
    find /mnt/c/kyraProyecto -name "*.log" -type f -exec truncate -s 0 {} \; 2>/dev/null
    
    # Quick verification
    log_count=$(find /mnt/c/kyraProyecto -name "*.log" -type f | wc -l)
    echo "✅ $(date '+%H:%M:%S') - $log_count log files cleared"
    
    # Wait 10 seconds
    sleep 10
done