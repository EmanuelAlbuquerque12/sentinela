# Instruções de Instalação - Windows

## Erro: ModuleNotFoundError: No module named 'bs4'

Este erro ocorre porque as novas dependências não estão instaladas no seu ambiente.

## Solução Rápida

Abra o terminal (cmd ou PowerShell) na pasta do projeto e execute:

```bash
# Ativar o ambiente virtual (se ainda não estiver ativo)
venv\Scripts\activate

# Instalar as novas dependências
pip install beautifulsoup4 lxml pymupdf unidecode

# OU instalar todas as dependências completas de uma vez
pip install -r requirements-full.txt
```

## Dependências Adicionadas

Estas bibliotecas foram adicionadas para suportar as novas funcionalidades:

1. **beautifulsoup4** - Scraping de HTML do DOU
2. **lxml** - Parser HTML rápido
3. **pymupdf** - Extração de texto de PDFs (acórdãos TCU)
4. **unidecode** - Normalização de texto (remove acentos)

## Verificar Instalação

Depois de instalar, teste com:

```bash
python -c "from bs4 import BeautifulSoup; import fitz; from unidecode import unidecode; print('✅ Todas as dependências instaladas!')"
```

## Executar o Servidor

Após instalar as dependências:

```bash
uvicorn app.main:app --reload
```

O servidor estará disponível em: http://localhost:8000

## Troubleshooting

### Erro com pymupdf no Windows

Se tiver problema ao instalar `pymupdf`, tente:

```bash
pip install --upgrade pip
pip install pymupdf --no-cache-dir
```

### Erro com lxml no Windows

Se tiver problema com `lxml`, você pode instalar uma versão pré-compilada:

```bash
pip install lxml --only-binary :all:
```

### Usar apenas funcionalidades básicas (sem PDF)

Se não precisar da funcionalidade de extração de acórdãos em PDF, você pode desabilitar o serviço TCU Acórdãos comentando a linha no arquivo `app/services/__init__.py`:

```python
# from .tcu_acordaos import TCUAcordaosService
```

E no `app/services/aggregator.py`:

```python
# self.tcu_acordaos = TCUAcordaosService()
# "tcu_acordaos": self.tcu_acordaos,
```
