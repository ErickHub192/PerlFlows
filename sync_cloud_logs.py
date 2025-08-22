#!/usr/bin/env python3
"""
Script para sincronizar logs de la nube AWS a local
Usa SSH para descargar logs del servidor de producción
"""

import subprocess
import os
from datetime import datetime
import time

# Configuración del servidor
SERVER_HOST = "ec2-54-224-27-126.compute-1.amazonaws.com"
SERVER_USER = "ubuntu"
SSH_KEY = "Perflow-ssh.pem"  # Ajusta la ruta si está en otro lado
REMOTE_LOG_DIR = "/home/ubuntu/PerlFlows/logs"
LOCAL_LOG_DIR = "./cloud_logs"

def ensure_local_dir():
    """Crear directorio local para logs si no existe"""
    if not os.path.exists(LOCAL_LOG_DIR):
        os.makedirs(LOCAL_LOG_DIR)
        print(f"✅ Creado directorio: {LOCAL_LOG_DIR}")

def sync_logs():
    """Sincronizar logs del servidor remoto"""
    try:
        # Comando SCP para descargar logs
        cmd = [
            "scp", 
            "-i", SSH_KEY,
            "-r",  # Recursivo
            f"{SERVER_USER}@{SERVER_HOST}:{REMOTE_LOG_DIR}/*",
            LOCAL_LOG_DIR
        ]
        
        print(f"🔄 Sincronizando logs desde {SERVER_HOST}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Logs sincronizados exitosamente")
            return True
        else:
            print(f"❌ Error sincronizando: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def sync_systemd_logs():
    """Descargar logs del sistema (journalctl)"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{LOCAL_LOG_DIR}/systemd_perlflow_{timestamp}.log"
        
        cmd = [
            "ssh", 
            "-i", SSH_KEY,
            f"{SERVER_USER}@{SERVER_HOST}",
            "sudo journalctl -u perlflow-backend --since '24 hours ago' --no-pager"
        ]
        
        print("🔄 Descargando logs del sistema...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            print(f"✅ Logs del sistema guardados en: {output_file}")
            return True
        else:
            print(f"❌ Error descargando logs del sistema: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def watch_logs():
    """Modo watch: sincronizar cada 30 segundos"""
    print("👀 Modo watch activado (Ctrl+C para salir)")
    try:
        while True:
            sync_logs()
            sync_systemd_logs()
            print(f"💤 Esperando 30 segundos...")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n✋ Detenido por usuario")

if __name__ == "__main__":
    print("🚀 PerlFlow Cloud Log Sync")
    
    # Verificar que existe la clave SSH
    if not os.path.exists(SSH_KEY):
        print(f"❌ No se encuentra la clave SSH: {SSH_KEY}")
        print("💡 Ajusta la ruta en la variable SSH_KEY del script")
        exit(1)
    
    ensure_local_dir()
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        watch_logs()
    else:
        print("🔄 Sincronización única...")
        sync_logs()
        sync_systemd_logs()
        print("\n💡 Usa --watch para sincronización continua")