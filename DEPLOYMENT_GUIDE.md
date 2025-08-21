# 🚀 GUÍA COMPLETA DE DEPLOYMENT - PERLFLOWS AWS

## 📋 INFORMACIÓN DE LA INSTANCIA
- **Instance ID**: `i-0ff7677d576a679b0`
- **Nombre**: Perlflow
- **DNS Público**: `ec2-54-224-27-126.compute-1.amazonaws.com`
- **Clave SSH**: `Perflow-ssh.pem`
- **Usuario**: `ubuntu`
- **Directorio del proyecto**: `/home/ubuntu/PerlFlows` (NO /home/perlflow/)
- **Servicio**: `perlflow-backend.service`

## 🔑 PASO 1: PREPARAR CONEXIÓN SSH

### 1.1 Localizar archivo de clave
```bash
# Buscar el archivo Perflow-ssh.pem en tu sistema
# Normalmente está en Downloads o donde lo descargaste
find ~ -name "Perflow-ssh.pem" 2>/dev/null
```

### 1.2 Configurar permisos de clave
```bash
# Cambiar permisos para seguridad (OBLIGATORIO)
chmod 400 "Perflow-ssh.pem"
```

### 1.3 Probar conexión SSH
```bash
# Conectar a la instancia AWS
ssh -i "Perflow-ssh.pem" ubuntu@ec2-54-224-27-126.compute-1.amazonaws.com
```

**Solución si falla conexión:**
```bash
# Si da error de conexión, verificar security group
# En AWS Console: EC2 > Security Groups > Abrir puerto 22 (SSH)

# Si dice "Host key verification failed":
ssh-keygen -R ec2-54-224-27-126.compute-1.amazonaws.com
```

## 🔄 PASO 2: ACTUALIZACIÓN MANUAL (RECOMENDADO)

### 2.1 Conectar al servidor
```bash
ssh -i "Perflow-ssh.pem" ubuntu@ec2-54-224-27-126.compute-1.amazonaws.com
```

### 2.2 Actualizar código backend
```bash
# Ir al directorio del proyecto
cd /home/ubuntu/PerlFlows

# Ver estado actual
git status

# Si hay cambios locales, guardarlos
git stash push -m "Changes before update"

# Actualizar código
git pull origin master

# Ver que se actualizó
git log --oneline -5

# Restart del servicio
sudo systemctl restart perlflow-backend

# Verificar que arrancó bien
sudo systemctl status perlflow-backend
```

### 2.3 Actualizar frontend
```bash
# Ir al directorio del frontend
cd /home/ubuntu/PerlFlows/Client/my-preact-app

# IMPORTANTE: Limpiar dependencias si hay errores de plataforma
# Si npm install falla con errores de Windows/Linux:
rm -rf node_modules
rm -f package-lock.json
npm cache clean --force

# Instalar dependencias (usar --force si persisten errores de plataforma)
npm install
# O si falla: npm install --force

# Build del frontend
npm run build

# Verificar que el build se creó
ls -la dist/

# IMPORTANTE: Copiar al directorio correcto que usa Nginx
sudo mkdir -p /var/www/perlflow
sudo cp -r dist/* /var/www/perlflow/

# Verificar que se copió al directorio correcto
ls -la /var/www/perlflow/

# Reload Nginx
sudo systemctl reload nginx
```

## 📊 PASO 3: VERIFICACIÓN POST-DEPLOYMENT

### 3.1 Verificar servicios
```bash
# Estado del servicio backend
sudo systemctl status perlflow

# Estado de Nginx
sudo systemctl status nginx

# Logs en tiempo real
sudo tail -f /home/perlflow/PerlFlows/logs/qyral_app_$(date +%Y-%m-%d).log
```

### 3.2 Probar endpoints
```bash
# Health check
curl http://perlflow.com/api/health

# Connectors
curl http://perlflow.com/api/connectors

# Frontend
curl -I http://perlflow.com
```

## 🔧 PASO 4: COMANDOS DE MANTENIMIENTO

### ⚠️ IMPORTANTE: El servicio se llama `perlflow-backend.service`

### 4.1 Reiniciar servicios
```bash
# Reiniciar backend (NOMBRE CORRECTO)
sudo systemctl restart perlflow-backend

# Reiniciar Nginx
sudo systemctl restart nginx

# Reiniciar ambos
sudo systemctl restart perlflow-backend nginx
```

### 4.2 Ver logs
```bash
# Estado del servicio (NOMBRE CORRECTO)
sudo systemctl status perlflow-backend

# Logs del backend (DIRECTORIO CORRECTO)
sudo tail -50 /home/ubuntu/PerlFlows/logs/qyral_app_$(date +%Y-%m-%d).log

# Logs del sistema (NOMBRE CORRECTO)
sudo journalctl -u perlflow-backend -f

# Logs de Nginx
sudo tail -50 /var/log/nginx/error.log
```

### 4.3 Actualizar código manualmente
```bash
cd /home/ubuntu/PerlFlows
git stash push -m "Pre-update changes"
git pull origin master
sudo systemctl restart perlflow-backend
```

## 🌐 PASO 5: CONFIGURAR GMAIL OAUTH PARA PRODUCCIÓN

### 5.1 Verificar variables de entorno
```bash
# Conectado al servidor, verificar .env (DIRECTORIO CORRECTO)
cat /home/ubuntu/PerlFlows/.env | grep GOOGLE
```

### 5.2 Si faltan credenciales OAuth
```bash
# Editar archivo .env (DIRECTORIO CORRECTO)
nano /home/ubuntu/PerlFlows/.env

# Agregar:
# GOOGLE_CLIENT_ID=tu_client_id_aqui
# GOOGLE_CLIENT_SECRET=tu_client_secret_aqui

# Restart después de cambios
sudo systemctl restart perlflow-backend
```

### 5.3 Verificar redirect URI en Google Console
- Ir a: https://console.cloud.google.com/apis/credentials
- Editar credenciales OAuth 2.0
- Agregar URI: `https://perlflow.com/auth/callback`
- Guardar cambios

## 🚨 TROUBLESHOOTING COMÚN

### Error: "Connection refused"
```bash
# Verificar que la instancia esté corriendo
# En AWS Console: EC2 > Instances > Estado: "running"

# Verificar security group permite SSH (puerto 22)
```

### Error: "Permission denied (publickey)"
```bash
# Verificar permisos de la clave
ls -la Perflow-ssh.pem
# Debe mostrar: -r-------- 1 user user

# Si no, corregir:
chmod 400 Perflow-ssh.pem
```

### Error: "Service failed to start"
```bash
# Ver logs detallados
sudo journalctl -u perlflow -n 50

# Verificar dependencias
sudo -u perlflow pip list | grep fastapi

# Reinstalar dependencias (DIRECTORIO CORRECTO)
cd /home/ubuntu/PerlFlows
/home/ubuntu/PerlFlows/venv/bin/pip install -r requirements.txt
```

### Frontend no carga
```bash
# Verificar Nginx
sudo nginx -t
sudo systemctl status nginx

# Verificar archivos del frontend
ls -la /var/www/html/

# Rebuild frontend (DIRECTORIO CORRECTO)
cd /home/ubuntu/PerlFlows/Client/my-preact-app
# Si hay errores de plataforma:
rm -rf node_modules && rm -f package-lock.json && npm cache clean --force
npm install --force  # Usar --force si persisten errores
npm run build
# IMPORTANTE: Copiar al directorio correcto que usa Nginx
sudo mkdir -p /var/www/perlflow
sudo cp -r dist/* /var/www/perlflow/
```

## 📱 PASO 6: VERIFICACIÓN FINAL

### URLs a probar:
- ✅ **Frontend**: http://perlflow.com
- ✅ **API Health**: http://perlflow.com/api/health
- ✅ **Connectors**: http://perlflow.com/api/connectors
- ✅ **Gmail OAuth**: Crear workflow que use Gmail

### Checklist final:
- [ ] Conexión SSH funciona
- [ ] Servicios activos (perlflow-backend + nginx)
- [ ] Frontend carga correctamente
- [ ] API responde
- [ ] Connectors listados
- [ ] Gmail OAuth configurado
- [ ] Webhook funcional
- [ ] Logs sin errores críticos

---

## 🎯 COMANDOS RÁPIDOS PARA ERICK

```bash
# 1. Conectar
ssh -i "Perflow-ssh.pem" ubuntu@ec2-54-224-27-126.compute-1.amazonaws.com

# 2. Update backend
cd /home/ubuntu/PerlFlows
git stash push -m "Pre-update changes"
git pull origin master
sudo systemctl restart perlflow-backend

# 3. Update frontend
cd /home/ubuntu/PerlFlows/Client/my-preact-app
npm install --force && npm run build
sudo mkdir -p /var/www/perlflow && sudo cp -r dist/* /var/www/perlflow/

# 4. Verificar todo OK
curl http://perlflow.com/api/health && echo "✅ API OK"

# 5. Si algo falla, ver logs
sudo tail -20 /home/ubuntu/PerlFlows/logs/qyral_app_$(date +%Y-%m-%d).log
```