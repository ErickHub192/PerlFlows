#!/bin/bash
# Monitor PerlFlows logs in production VPS

echo "========================================"
echo "🔍 PERLFLOWS LOG MONITOR"
echo "========================================"
echo "💡 Tip: Ctrl+C para salir"
echo ""

# Function to show colored output
show_section() {
    echo -e "\n\033[1;34m📋 $1\033[0m"
    echo "----------------------------------------"
}

# Check if we're on VPS or local
if [[ "$HOSTNAME" == *"srv"* ]]; then
    echo "🖥️  Ejecutando en VPS: $HOSTNAME"
    LOG_PATH="/home/perlflow/PerlFlows/logs"
    IS_VPS=true
else
    echo "💻 Ejecutando en Local: $HOSTNAME"
    LOG_PATH="./logs"
    IS_VPS=false
fi

# Menu selection
echo ""
echo "Selecciona qué logs monitorear:"
echo "1) 📊 Logs de aplicación (en vivo)"
echo "2) ❌ Solo errores (en vivo)"
echo "3) 🌐 Logs de Nginx (solo VPS)"
echo "4) ⚙️  Logs de systemd service (solo VPS)"
echo "5) 📈 Resumen del sistema"
echo "6) 🧪 Test rápido de APIs"
echo ""
read -p "Opción (1-6): " choice

case $choice in
    1)
        show_section "LOGS DE APLICACIÓN EN VIVO"
        if [ "$IS_VPS" = true ]; then
            sudo -u perlflow tail -f $LOG_PATH/qyral_app_$(date +%Y-%m-%d).log
        else
            tail -f $LOG_PATH/qyral_app_$(date +%Y-%m-%d).log 2>/dev/null || echo "❌ No hay logs de hoy"
        fi
        ;;
    2)
        show_section "SOLO ERRORES EN VIVO"
        if [ "$IS_VPS" = true ]; then
            sudo -u perlflow tail -f $LOG_PATH/errors_$(date +%Y-%m-%d).log
        else
            tail -f $LOG_PATH/errors_$(date +%Y-%m-%d).log 2>/dev/null || echo "❌ No hay errores de hoy"
        fi
        ;;
    3)
        if [ "$IS_VPS" = true ]; then
            show_section "LOGS DE NGINX EN VIVO"
            echo "Presiona Ctrl+C para salir"
            tail -f /var/log/nginx/access.log
        else
            echo "❌ Nginx logs solo disponibles en VPS"
        fi
        ;;
    4)
        if [ "$IS_VPS" = true ]; then
            show_section "LOGS DE SYSTEMD SERVICE"
            journalctl -u perlflow.service -f
        else
            echo "❌ Systemd logs solo disponibles en VPS"
        fi
        ;;
    5)
        show_section "RESUMEN DEL SISTEMA"
        echo "🕐 Timestamp: $(date)"
        echo ""
        
        if [ "$IS_VPS" = true ]; then
            echo "🔧 Estado del servicio:"
            systemctl status perlflow.service --no-pager -l | head -10
            echo ""
            
            echo "🌐 Estado de Nginx:"
            systemctl status nginx --no-pager -l | head -5
            echo ""
            
            echo "📊 Uso de recursos:"
            echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
            echo "RAM: $(free -h | awk 'NR==2{printf "%.1f/%.1f GB (%.2f%%)", $3/1024/1024, $2/1024/1024, $3*100/$2}')"
            echo "Disco: $(df -h / | awk 'NR==2{print $3"/"$2" ("$5")"}')"
        fi
        
        echo ""
        echo "📈 Últimos errores (últimas 10 líneas):"
        if [ -f "$LOG_PATH/errors_$(date +%Y-%m-%d).log" ]; then
            sudo -u perlflow tail -10 $LOG_PATH/errors_$(date +%Y-%m-%d).log 2>/dev/null || tail -10 $LOG_PATH/errors_$(date +%Y-%m-%d).log 2>/dev/null || echo "✅ No hay errores recientes"
        else
            echo "✅ No hay errores de hoy"
        fi
        ;;
    6)
        show_section "TEST RÁPIDO DE APIs"
        echo "🧪 Probando endpoints principales..."
        echo ""
        
        # Test health endpoint
        echo "1. Health check:"
        curl -s http://perlflow.com/api/health | jq '.' 2>/dev/null || curl -s http://perlflow.com/api/health || echo "❌ Error en health"
        echo ""
        
        # Test connectors
        echo "2. Connectors:"
        curl -s http://perlflow.com/api/connectors | jq 'length' 2>/dev/null || echo "❌ Error en connectors"
        echo ""
        
        # Test frontend
        echo "3. Frontend:"
        if curl -s http://perlflow.com | grep -q "QYRAL"; then
            echo "✅ Frontend cargando correctamente"
        else
            echo "❌ Frontend no responde correctamente"
        fi
        echo ""
        
        # Response time test
        echo "4. Tiempo de respuesta:"
        echo "Health: $(curl -w "%{time_total}s" -s -o /dev/null http://perlflow.com/api/health)"
        echo "Frontend: $(curl -w "%{time_total}s" -s -o /dev/null http://perlflow.com)"
        ;;
    *)
        echo "❌ Opción no válida"
        ;;
esac