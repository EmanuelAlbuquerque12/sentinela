#!/bin/bash

# ==========================================
# Sentinela - Script de Inicialização Linux/Mac
# ==========================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "  SENTINELA - Busca Unificada em"
echo "  Diários Oficiais Brasileiros"
echo "========================================"
echo ""

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERRO]${NC} Python3 não encontrado!"
    echo "Por favor, instale Python 3.10+ usando seu gerenciador de pacotes"
    echo "Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "macOS: brew install python3"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python encontrado: $(python3 --version)"
echo ""

# Verificar se venv existe
if [ ! -d "venv" ]; then
    echo -e "${BLUE}[INFO]${NC} Ambiente virtual não encontrado. Criando..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO]${NC} Falha ao criar ambiente virtual"
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} Ambiente virtual criado"
    echo ""
fi

# Ativar ambiente virtual
echo -e "${BLUE}[INFO]${NC} Ativando ambiente virtual..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO]${NC} Falha ao ativar ambiente virtual"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Ambiente virtual ativado"
echo ""

# Instalar/atualizar dependências
echo -e "${BLUE}[INFO]${NC} Verificando dependências..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO]${NC} Falha ao instalar dependências"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Dependências instaladas"
echo ""

# Verificar arquivo .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[AVISO]${NC} Arquivo .env não encontrado!"
    echo ""
    echo "Criando .env a partir de .env.example..."
    cp .env.example .env
    echo ""
    echo "========================================"
    echo "  CONFIGURAÇÃO NECESSÁRIA"
    echo "========================================"
    echo ""
    echo "O arquivo .env foi criado."
    echo ""
    echo "IMPORTANTE: Para buscar em tribunais (DataJud/CNJ),"
    echo "você precisa de uma API Key GRATUITA."
    echo ""
    echo "Solicite em: https://www.cnj.jus.br/sistemas/datajud/api-publica/"
    echo ""
    echo "Depois, edite o arquivo .env e adicione:"
    echo "DATAJUD_API_KEY=sua_chave_aqui"
    echo ""
    echo "As outras fontes (Querido Diário e TCU) não precisam de autenticação."
    echo ""
    read -p "Pressione Enter para continuar..."
fi

# Verificar se porta 8000 está em uso
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}[AVISO]${NC} Porta 8000 já está em uso!"
    echo "Por favor, encerre o processo ou use outra porta."
    echo ""
    read -p "Pressione Enter para continuar mesmo assim..."
fi

# Iniciar servidor
echo "========================================"
echo "  INICIANDO SENTINELA"
echo "========================================"
echo ""
echo "Interface Web: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Pressione Ctrl+C para encerrar"
echo "========================================"
echo ""

# Aguardar 2 segundos e tentar abrir navegador
sleep 2

# Tentar abrir navegador (Linux)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000 &> /dev/null &
# Tentar abrir navegador (macOS)
elif command -v open &> /dev/null; then
    open http://localhost:8000 &> /dev/null &
fi

# Executar servidor
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Se chegou aqui, servidor foi encerrado
echo ""
echo "========================================"
echo "  SENTINELA ENCERRADO"
echo "========================================"
echo ""
