#!/bin/bash

# 🔥 QYRAL LOG CLEANER - Automatiza limpieza de logs
# Usage: ./clear_logs.sh

echo "🧹 LIMPIANDO LOGS DE QYRAL..."

# Find and clear all log files
find /mnt/c/kyraProyecto -name "*.log" -type f -exec truncate -s 0 {} \;

# Verify they're empty
echo "📊 VERIFICANDO LIMPIEZA:"
find /mnt/c/kyraProyecto -name "*.log" -type f -exec wc -l {} \;

echo "✅ LOGS LIMPIADOS! Ready for testing 🔥"
echo ""
echo "💡 TIP: Puedes usar 'watch ./clear_logs.sh' para ejecutar cada 2 segundos"