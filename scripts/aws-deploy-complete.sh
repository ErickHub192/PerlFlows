#!/bin/bash
# Complete AWS deployment script for PerlFlows
# Actualiza tanto backend como frontend desde GitHub

echo "========================================"
echo "🚀 PERLFLOWS AWS DEPLOYMENT"
echo "========================================"

# Variables
REPO_URL="https://github.com/ErickHub192/PerlFlows.git"
DEPLOY_DIR="/home/perlflow/PerlFlows"
SERVICE_NAME="perlflow"
BRANCH="master"  # Cambiar según necesites

echo "📋 Configuración:"
echo "   Repository: $REPO_URL"
echo "   Deploy Dir: $DEPLOY_DIR"
echo "   Branch: $BRANCH"
echo "   Service: $SERVICE_NAME"
echo ""

# Función para verificar comando exitoso
check_success() {
    if [ $? -eq 0 ]; then
        echo "   ✅ $1"
    else
        echo "   ❌ $1 - FAILED"
        exit 1
    fi
}

# 1. BACKUP ACTUAL
echo "💾 1. Creando backup..."
cd /home/perlflow
sudo -u perlflow cp -r PerlFlows PerlFlows_backup_$(date +%Y%m%d_%H%M%S)
check_success "Backup creado"

# 2. ACTUALIZAR CÓDIGO
echo ""
echo "🔄 2. Actualizando código desde GitHub..."
cd $DEPLOY_DIR

# Guardar cambios locales si los hay
sudo -u perlflow git stash push -m "Pre-deploy stash $(date)"
check_success "Stash de cambios locales"

# Cambiar a branch correcto
sudo -u perlflow git checkout $BRANCH
check_success "Checkout a $BRANCH"

# Pull últimos cambios
sudo -u perlflow git pull origin $BRANCH
check_success "Pull desde GitHub"

# 3. INSTALAR DEPENDENCIAS
echo ""
echo "📦 3. Instalando dependencias..."

# Backend dependencies
echo "   Backend dependencies..."
sudo -u perlflow pip install -r requirements.txt
check_success "Dependencias Python instaladas"

# Frontend dependencies y build
echo "   Frontend dependencies..."
cd $DEPLOY_DIR/Client/my-preact-app
sudo -u perlflow npm install
check_success "Dependencias NPM instaladas"

echo "   Building frontend..."
sudo -u perlflow npm run build
check_success "Frontend build"

# 4. CONFIGURAR NGINX PARA SERVIR FRONTEND
echo ""
echo "🌐 4. Configurando Nginx..."

# Copiar build a directorio de Nginx
sudo cp -r $DEPLOY_DIR/Client/my-preact-app/dist/* /var/www/html/
check_success "Frontend copiado a Nginx"

# Verificar configuración Nginx
sudo nginx -t
check_success "Configuración Nginx válida"

# 5. APLICAR MIGRACIONES DE BD
echo ""
echo "🗄️ 5. Aplicando migraciones..."
cd $DEPLOY_DIR
sudo -u perlflow python -m alembic upgrade head
check_success "Migraciones aplicadas"

# 6. REINICIAR SERVICIOS
echo ""
echo "🔃 6. Reiniciando servicios..."

# Reiniciar backend
sudo systemctl restart $SERVICE_NAME
check_success "Servicio $SERVICE_NAME reiniciado"

# Reload Nginx
sudo systemctl reload nginx
check_success "Nginx recargado"

# 7. VERIFICACIONES
echo ""
echo "🧪 7. Verificando deployment..."

# Esperar que el servicio arranque
sleep 5

# Verificar estado del servicio
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "   ✅ Servicio $SERVICE_NAME activo"
else
    echo "   ❌ Servicio $SERVICE_NAME no está activo"
    sudo systemctl status $SERVICE_NAME --no-pager -l
    exit 1
fi

# Test health endpoint
echo "   Probando health endpoint..."
if curl -s http://perlflow.com/api/health | grep -q "healthy"; then
    echo "   ✅ API health OK"
else
    echo "   ❌ API health failed"
    curl -s http://perlflow.com/api/health
fi

# Test frontend
echo "   Probando frontend..."
if curl -s http://perlflow.com | grep -q "PerlFlow"; then
    echo "   ✅ Frontend OK"
else
    echo "   ❌ Frontend error"
fi

# Test connectors
echo "   Probando connectors..."
CONNECTORS=$(curl -s http://perlflow.com/api/connectors | jq '. | length' 2>/dev/null)
if [ "$CONNECTORS" -gt 0 ] 2>/dev/null; then
    echo "   ✅ Connectors OK ($CONNECTORS encontrados)"
else
    echo "   ⚠️  Connectors warning"
fi

# 8. LIMPIAR BACKUPS ANTIGUOS
echo ""
echo "🧹 8. Limpiando backups antiguos..."
cd /home/perlflow
sudo find . -name "PerlFlows_backup_*" -mtime +7 -exec rm -rf {} + 2>/dev/null
echo "   ✅ Backups antiguos limpiados"

# 9. LOGS FINALES
echo ""
echo "📋 9. Estado final:"
echo "   Servicio: $(sudo systemctl is-active $SERVICE_NAME)"
echo "   Nginx: $(sudo systemctl is-active nginx)"
echo "   Última actualización: $(date)"

echo ""
echo "🎉 DEPLOYMENT COMPLETADO"
echo "========================================"
echo "🌐 Frontend: http://perlflow.com"
echo "🔗 API: http://perlflow.com/api"
echo "📊 Health: http://perlflow.com/api/health"
echo "========================================"

# Mostrar últimos logs
echo ""
echo "📜 Últimos logs del servicio:"
sudo -u perlflow tail -10 $DEPLOY_DIR/logs/qyral_app_$(date +%Y-%m-%d).log 2>/dev/null || echo "No hay logs disponibles"