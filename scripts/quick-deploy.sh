#!/bin/bash
# Quick deployment script for PerlFlows

echo "========================================"
echo "🚀 PERLFLOWS QUICK DEPLOY"
echo "========================================"

# Check if we're on VPS
if [[ "$HOSTNAME" == *"srv"* ]]; then
    echo "🖥️  Ejecutando en VPS: $HOSTNAME"
    IS_VPS=true
else
    echo "❌ Este script debe ejecutarse en el VPS"
    exit 1
fi

echo ""
echo "Selecciona la acción:"
echo "1) 🔄 Update code from GitHub"
echo "2) 🔃 Restart service"
echo "3) 📊 Check service status"
echo "4) 🧪 Run tests"
echo "5) 📋 View recent logs"
echo "6) 🛠️  Full redeploy (update + restart)"
echo ""
read -p "Opción (1-6): " choice

case $choice in
    1)
        echo "🔄 Actualizando código desde GitHub..."
        cd /home/perlflow/PerlFlows
        sudo -u perlflow git stash
        sudo -u perlflow git config pull.rebase false
        sudo -u perlflow git pull origin vps-backend-only --allow-unrelated-histories
        echo "✅ Código actualizado"
        ;;
    2)
        echo "🔃 Reiniciando servicio..."
        systemctl restart perlflow
        sleep 2
        systemctl status perlflow --no-pager -l
        ;;
    3)
        echo "📊 Estado del servicio:"
        systemctl status perlflow --no-pager -l
        echo ""
        echo "🌐 Estado de Nginx:"
        systemctl status nginx --no-pager -l
        ;;
    4)
        echo "🧪 Ejecutando tests..."
        echo ""
        echo "Health check:"
        curl -s http://perlflow.com/api/health | jq '.' || curl -s http://perlflow.com/api/health
        echo ""
        echo "Connectors:"
        curl -s http://perlflow.com/api/connectors | jq 'length' || echo "Error"
        echo ""
        echo "Frontend:"
        if curl -s http://perlflow.com | grep -q "QYRAL"; then
            echo "✅ Frontend OK"
        else
            echo "❌ Frontend error"
        fi
        ;;
    5)
        echo "📋 Últimos logs (20 líneas):"
        sudo -u perlflow tail -20 /home/perlflow/PerlFlows/logs/qyral_app_$(date +%Y-%m-%d).log
        ;;
    6)
        echo "🛠️  Full redeploy..."
        echo "🔄 1. Actualizando código..."
        cd /home/perlflow/PerlFlows
        sudo -u perlflow git stash
        sudo -u perlflow git config pull.rebase false
        sudo -u perlflow git pull origin vps-backend-only --allow-unrelated-histories
        
        echo "🔃 2. Reiniciando servicio..."
        systemctl restart perlflow
        sleep 3
        
        echo "📊 3. Verificando estado..."
        systemctl status perlflow --no-pager -l
        
        echo "🧪 4. Probando endpoints..."
        sleep 2
        curl -s http://perlflow.com/api/health | jq '.' || curl -s http://perlflow.com/api/health
        
        echo ""
        echo "✅ Deploy completado"
        ;;
    *)
        echo "❌ Opción no válida"
        ;;
esac