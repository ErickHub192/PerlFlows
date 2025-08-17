@echo off
echo ==========================================
echo    LIMPIEZA COMPLETA E INSTALACION
echo ==========================================

echo.
echo 1. Eliminando archivos de cache...
if exist "node_modules" (
    echo    - Eliminando node_modules...
    rmdir /s /q node_modules
)
if exist "package-lock.json" (
    echo    - Eliminando package-lock.json...
    del package-lock.json
)
if exist ".vite" (
    echo    - Eliminando cache de Vite...
    rmdir /s /q .vite
)

echo.
echo 2. Limpiando cache de npm...
npm cache clean --force

echo.
echo 3. Verificando versiones...
echo    Node.js version:
node --version
echo    npm version:
npm --version

echo.
echo 4. Instalando dependencias...
npm install

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Instalacion completada exitosamente!
    echo.
    echo 5. Verificando Vite...
    npx vite --version
    echo.
    echo 6. Iniciando servidor de desarrollo...
    echo    URL: http://localhost:5173/
    echo    Presiona Ctrl+C para detener el servidor
    echo.
    npm run dev
) else (
    echo.
    echo ❌ Error durante la instalacion
    echo    Revisa los errores anteriores
)

pause