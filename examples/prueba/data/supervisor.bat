@echo on
title Supervisor de descargas

echo ==============================
echo Monitor de descargas iniciado
echo Carpeta: %cd%
echo ==============================

:inicio
set count1=0
for /f %%A in ('dir /b /a-d ^| find /c /v ""') do set count1=%%A
echo Archivos actuales: %count1%

echo Esperando 60 segundos...
timeout /t 60

set count2=0
for /f %%A in ('dir /b /a-d ^| find /c /v ""') do set count2=%%A
echo Archivos despues: %count2%

if "%count1%"=="%count2%" (
    echo No hubo cambios. Apagando el PC...
    shutdown /s /t 0
) else (
    echo Hubo cambios. Siguiendo monitoreo...
    echo.
    goto inicio
)