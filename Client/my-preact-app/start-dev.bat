@echo off
echo ==========================================
echo    INICIANDO SERVIDOR DE DESARROLLO
echo ==========================================

echo.
echo 1. Verificando instalacion de Vite...
npm list vite

echo.
echo 2. Iniciando servidor usando la ruta directa...
echo    URL: http://localhost:5173/
echo    Presiona Ctrl+C para detener el servidor
echo.

.\node_modules\.bin\vite

pause