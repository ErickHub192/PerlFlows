# logging_config.py - Configuración automática de logs a archivos

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

def setup_file_logging():
    """
    🔧 SETUP: Configuración automática de logs a archivos
    - Logs se guardan automáticamente en /logs/
    - Rotación diaria automática  
    - Mantiene últimos 7 días
    """
    
    # Crear directorio de logs si no existe
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Formato detallado para debugging
    detailed_format = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 📁 ARCHIVO PRINCIPAL: Todo en un archivo diario
    today = datetime.now().strftime("%Y-%m-%d")
    main_handler = logging.FileHandler(
        f"logs/qyral_app_{today}.log",
        mode='a',
        encoding='utf-8'
    )
    main_handler.setFormatter(detailed_format)
    main_handler.setLevel(logging.INFO)
    
    # 🚨 ARCHIVO DE ERRORES: Solo errores críticos
    error_handler = logging.FileHandler(
        f"logs/errors_{today}.log", 
        mode='a',
        encoding='utf-8'
    )
    error_handler.setFormatter(detailed_format)
    error_handler.setLevel(logging.ERROR)
    
    # 🔄 ROTACIÓN AUTOMÁTICA: Archivo que rota cada día
    rotating_handler = logging.handlers.TimedRotatingFileHandler(
        "logs/qyral_rotating.log",
        when='midnight',
        interval=1,
        backupCount=7,  # Mantener 7 días
        encoding='utf-8'
    )
    rotating_handler.setFormatter(detailed_format)
    rotating_handler.setLevel(logging.DEBUG)
    
    # 📺 CONSOLA: Para ver en tiempo real
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))
    console_handler.setLevel(logging.INFO)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Agregar todos los handlers
    root_logger.addHandler(main_handler)      # Todo a archivo diario
    root_logger.addHandler(error_handler)     # Solo errores
    root_logger.addHandler(rotating_handler)  # Rotación automática
    root_logger.addHandler(console_handler)   # Consola
    
    print(f"LOGGING CONFIGURADO:")
    print(f"   Logs principales: logs/qyral_app_{today}.log")
    print(f"   Solo errores: logs/errors_{today}.log")
    print(f"   Rotacion: logs/qyral_rotating.log")
    print(f"   Consola: Habilitada")
    
    return True

# 🚀 CONFIGURACIÓN ESPECÍFICA PARA FASTAPI/UVICORN
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": f"logs/fastapi_{datetime.now().strftime('%Y-%m-%d')}.log",
            "mode": "a",
            "formatter": "detailed",
            "level": "INFO",
            "encoding": "utf-8"
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
            "stream": "ext://sys.stdout"
        },
        "rotating": {
            "class": "logging.handlers.TimedRotatingFileHandler", 
            "filename": "logs/app_rotating.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "formatter": "detailed",
            "level": "DEBUG",
            "encoding": "utf-8"
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["file", "console", "rotating"],
            "level": "DEBUG",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False
        },
        "fastapi": {
            "handlers": ["file", "console"],
            "level": "INFO", 
            "propagate": False
        }
    }
}

if __name__ == "__main__":
    # Test de la configuración
    setup_file_logging()
    
    logger = logging.getLogger("test")
    logger.info("🧪 TEST: Configuración de logging funcionando")
    logger.error("🚨 TEST: Error de prueba")
    logger.debug("🔍 TEST: Debug message")
    
    print("✅ Tests completados - revisa el directorio /logs/")