@echo off
REM ====================================================
REM Sentinela - Instalador Automático de Dependências
REM ====================================================

echo.
echo ====================================================
echo  SENTINELA - Instalacao Automatica
echo ====================================================
echo.

REM Verificar se está na pasta correta
if not exist "app" (
    echo [ERRO] Pasta 'app' nao encontrada!
    echo Execute este script na raiz do projeto Sentinela.
    pause
    exit /b 1
)

REM Verificar se venv existe
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado!
)

REM Ativar ambiente virtual
echo [INFO] Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Atualizar pip, setuptools e wheel
echo.
echo [INFO] Atualizando pip, setuptools e wheel...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [AVISO] Falha ao atualizar pip/setuptools/wheel
)

REM Instalar dependências base
echo.
echo [INFO] Instalando dependencias base...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias base!
    pause
    exit /b 1
)

REM Instalar dependências essenciais para scraping e PDF
echo.
echo [INFO] Instalando bibliotecas essenciais...
echo   - BeautifulSoup4 (scraping HTML)
echo   - lxml (parser rapido)
echo   - PyMuPDF (extracao PDF)
echo   - unidecode (normalizacao texto)
echo.

pip install beautifulsoup4 lxml pymupdf unidecode
if errorlevel 1 (
    echo [AVISO] Algumas bibliotecas podem ter falhado
    echo Tentando instalacao individual...

    pip install beautifulsoup4
    pip install lxml --only-binary :all:
    pip install pymupdf --no-cache-dir
    pip install unidecode
)

REM Testar imports
echo.
echo [INFO] Testando instalacao...
python -c "from bs4 import BeautifulSoup; print('[OK] BeautifulSoup instalado')" 2>nul || echo [ERRO] BeautifulSoup nao instalado
python -c "import lxml; print('[OK] lxml instalado')" 2>nul || echo [ERRO] lxml nao instalado
python -c "import fitz; print('[OK] PyMuPDF instalado')" 2>nul || echo [ERRO] PyMuPDF nao instalado
python -c "from unidecode import unidecode; print('[OK] unidecode instalado')" 2>nul || echo [ERRO] unidecode nao instalado

REM Verificar se o app pode ser importado
echo.
echo [INFO] Verificando integracao...
python -c "from app.services.aggregator import SearchAggregator; print('[OK] Sistema pode ser carregado')" 2>nul
if errorlevel 1 (
    echo [ERRO] Sistema nao pode ser carregado. Verifique os erros acima.
    echo.
    echo Pressione qualquer tecla para ver os detalhes do erro...
    pause > nul
    python -c "from app.services.aggregator import SearchAggregator"
    pause
    exit /b 1
)

echo.
echo ====================================================
echo  INSTALACAO CONCLUIDA COM SUCESSO!
echo ====================================================
echo.
echo Dependencias instaladas:
echo   [x] FastAPI + Uvicorn
echo   [x] httpx (HTTP client)
echo   [x] Pydantic v2
echo   [x] BeautifulSoup4 + lxml
echo   [x] PyMuPDF (fitz)
echo   [x] unidecode
echo.
echo Fontes disponiveis: 9
echo   1. Querido Diario (municipios)
echo   2. DataJud (processos judiciais)
echo   3. TCU (acordaos)
echo   4. TCU Enhanced (10 APIs)
echo   5. TCU Acordaos PDF
echo   6. DOU (dados abertos)
echo   7. INLabs (DOU completo)
echo   8. DOU Scrapy (fallback)
echo   9. DOU Dados Abertos (mensal)
echo.
echo ====================================================
echo.

REM Perguntar se quer iniciar o servidor
echo Deseja iniciar o servidor agora? (S/N)
set /p START_SERVER="> "

if /i "%START_SERVER%"=="S" (
    echo.
    echo [INFO] Iniciando servidor Sentinela...
    echo Acesse: http://localhost:8000
    echo Pressione Ctrl+C para parar
    echo.
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) else (
    echo.
    echo Para iniciar o servidor manualmente, execute:
    echo   venv\Scripts\activate
    echo   uvicorn app.main:app --reload
    echo.
)

pause
