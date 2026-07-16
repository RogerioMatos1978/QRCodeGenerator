@echo off
REM ============================================================================
REM  build_windows_exe.bat
REM ============================================================================
REM  Gera QRCodeGenerator.exe (executavel portatil para Windows) usando
REM  PyInstaller. Rode este script DENTRO do Windows -- nao e possivel gerar
REM  um .exe valido a partir de Linux/macOS (compilacao cruzada nao suportada).
REM
REM  Como usar:
REM    1. Abra o terminal do PyCharm (ou Prompt de Comando) na pasta do projeto.
REM    2. Ative o ambiente virtual, se ainda nao estiver ativo:
REM         venv\Scripts\activate
REM    3. Execute:
REM         build_windows_exe.bat
REM    4. Aguarde a compilacao terminar. O executavel final estara em:
REM         dist\QRCodeGenerator.exe
REM
REM  O .exe gerado e PORTATIL: pode ser copiado para qualquer computador
REM  Windows e executado com um duplo-clique, sem precisar instalar Python.
REM ============================================================================

echo.
echo [1/3] Instalando PyInstaller (caso ainda nao esteja instalado)...
pip install --upgrade pyinstaller

echo.
echo [2/3] Limpando builds anteriores...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q QRCodeGenerator.spec 2>nul

echo.
echo [3/3] Gerando o executavel (isso pode levar alguns minutos)...
REM --onefile     -> um unico arquivo .exe portatil
REM --windowed    -> nao abre janela de terminal preta junto com a GUI
REM --collect-all -> garante que os dados internos de cada biblioteca
REM                  (temas do customtkinter, etc.) sejam incluidos no .exe
pyinstaller ^
    --name QRCodeGenerator ^
    --onefile ^
    --windowed ^
    --collect-all customtkinter ^
    --collect-all segno ^
    --add-data "landing_page;landing_page" ^
    --add-data "assets;assets" ^
    main.py

echo.
if exist dist\QRCodeGenerator.exe (
    echo ============================================================
    echo  Build concluido com sucesso!
    echo  Executavel gerado em: dist\QRCodeGenerator.exe
    echo.
    echo  Esse arquivo pode ser copiado para qualquer computador
    echo  Windows e executado diretamente, sem instalar Python.
    echo ============================================================
) else (
    echo ============================================================
    echo  ERRO: o executavel nao foi gerado. Revise as mensagens
    echo  de erro acima para identificar o problema.
    echo ============================================================
)

pause
