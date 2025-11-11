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
    pause
    exit /b 1
)

echo [OK] Python encontrado
echo.

REM Verificar se venv existe
if not exist "venv" (
    echo [INFO] Ambiente virtual nao encontrado. Criando...
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual
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
    pause
    exit /b 1
)
echo [OK] Ambiente virtual ativado
echo.

REM Instalar/atualizar dependências
echo [INFO] Verificando dependencias...
pip install -q --upgrade pip
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias
    pause
    exit /b 1
)
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
    echo Solicite em: https://www.cnj.jus.br/sistemas/datajud/api-publica/
    echo.
    echo Depois, edite o arquivo .env e adicione:
    echo DATAJUD_API_KEY=sua_chave_aqui
    echo.
    echo As outras fontes (Querido Diario e TCU^) nao precisam de autenticacao.
    echo.
    pause
)

REM Verificar se porta 8000 está em uso
netstat -ano | findstr :8000 >nul 2>&1
if not errorlevel 1 (
    echo [AVISO] Porta 8000 ja esta em uso!
    echo Por favor, encerre o processo ou use outra porta.
    echo.
    pause
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

REM Aguardar 2 segundos e abrir navegador
timeout /t 2 /nobreak >nul
start http://localhost:8000

REM Executar servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM Se chegou aqui, servidor foi encerrado
echo.
echo ========================================
echo   SENTINELA ENCERRADO
echo ========================================
echo.
pause
