@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  ============================================
echo   Cattleya-Flow - Iniciando servidor
echo  ============================================
echo.
echo  NO CIERRES ESTA VENTANA mientras uses el sistema.
echo  Para apagar el servidor: cierra esta ventana o presiona Ctrl+C.
echo.
"C:\Users\leone\AppData\Local\Programs\Python\Python311\python.exe" run.py
echo.
echo  El servidor se detuvo.
pause
