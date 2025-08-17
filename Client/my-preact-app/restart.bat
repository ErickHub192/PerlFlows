@echo off
echo Limpiando y reiniciando la aplicación...

echo 1. Eliminando node_modules...
rmdir /s /q node_modules 2>nul

echo 2. Eliminando package-lock.json...
del package-lock.json 2>nul

echo 3. Limpiando cache de npm...
npm cache clean --force

echo 4. Instalando dependencias...
npm install

echo 5. Iniciando servidor de desarrollo...
echo La aplicacion estara disponible en: http://localhost:5173/
npm run dev

pause