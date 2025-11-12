@echo off
REM ==========================================
REM Sentinela - Script de Inicialização Windows
REM ==========================================

echo.
echo ========================================
echo   SENTINELA - Busca Unificada em
echo   Diarios Oficiais Brasileiros
echo ========================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale Python 3.10+ em: https://www.python.org/downloads/
    echo.
    echo Dica: Marque "Add Python to PATH" durante instalacao
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version
echo.

REM Verificar se venv existe
if not exist "venv" (
    echo [INFO] Ambiente virtual nao encontrado. Criando...
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual
        echo.
        echo Tente executar como Administrador ou verifique permissoes
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado
    echo.
)

REM Ativar ambiente virtual
echo [INFO] Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERRO] Falha ao ativar ambiente virtual
    echo.
    echo Tente: venv\Scripts\activate.bat
    pause
    exit /b 1
)
echo [OK] Ambiente virtual ativado
echo.

REM Atualizar pip
echo [INFO] Atualizando pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip atualizado
echo.

REM Instalar dependências essenciais
echo [INFO] Instalando dependencias essenciais...
echo (Isso pode levar alguns minutos na primeira vez)
echo.

pip install --no-cache-dir -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar dependencias
    echo.
    echo ========================================
    echo   SOLUCAO ALTERNATIVA
    echo ========================================
    echo.
    echo Tente instalar manualmente:
    echo   pip install fastapi uvicorn httpx pydantic python-dotenv
    echo.
    echo Ou baixe versoes pre-compiladas:
    echo   https://www.lfd.uci.edu/~gohlke/pythonlibs/
    echo.
    pause
    exit /b 1
)
echo.
echo [OK] Dependencias instaladas
echo.

REM Verificar arquivo .env
if not exist ".env" (
    echo [AVISO] Arquivo .env nao encontrado!
    echo.
    echo Criando .env a partir de .env.example...
    copy .env.example .env >nul
    echo.
    echo ========================================
    echo   CONFIGURACAO NECESSARIA
    echo ========================================
    echo.
    echo O arquivo .env foi criado.
    echo.
    echo IMPORTANTE: Para buscar em tribunais (DataJud/CNJ^),
    echo voce precisa de uma API Key GRATUITA.
    echo.
    echo 1. Solicite em: https://www.cnj.jus.br/sistemas/datajud/api-publica/
    echo 2. Edite .env e adicione: DATAJUD_API_KEY=sua_chave_aqui
    echo.
    echo As outras fontes funcionam sem configuracao:
    echo - Querido Diario (municipios^)
    echo - TCU (acordaos^)
    echo.
    pause
)

REM Verificar se porta 8000 está em uso
netstat -ano | findstr :8000 >nul 2>&1
if not errorlevel 1 (
    echo [AVISO] Porta 8000 ja esta em uso!
    echo.
    echo Encerrando processo na porta 8000...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
    echo [OK] Porta liberada
    echo.
)

REM Iniciar servidor
echo ========================================
echo   INICIANDO SENTINELA
echo ========================================
echo.
echo Interface Web: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Pressione Ctrl+C para encerrar
echo ========================================
echo.

REM Aguardar 3 segundos e abrir navegador
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM Executar servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM Se chegou aqui, servidor foi encerrado
echo.
echo ========================================
echo   SENTINELA ENCERRADO
echo ========================================
echo.
pause
