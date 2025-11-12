# 🚀 Sentinela - Guia de Instalação Rápida

## ⚡ Instalação Automática (Windows)

### Opção 1: Instalador Automático (Recomendado)

Simplesmente **dê um duplo clique** no arquivo:

```
instalar.bat
```

O script vai:
- ✅ Criar o ambiente virtual (se necessário)
- ✅ Atualizar o pip
- ✅ Instalar TODAS as dependências
- ✅ Testar se tudo foi instalado corretamente
- ✅ Perguntar se quer iniciar o servidor

**Pronto!** O sistema estará funcionando em: http://localhost:8000

---

### Opção 2: Instalação Manual

Se preferir fazer manualmente:

```bash
# 1. Criar ambiente virtual (primeira vez)
python -m venv venv

# 2. Ativar ambiente virtual
venv\Scripts\activate

# 3. Atualizar pip
python -m pip install --upgrade pip

# 4. Instalar dependências base
pip install -r requirements.txt

# 5. Instalar bibliotecas essenciais
pip install beautifulsoup4 lxml pymupdf unidecode

# 6. Iniciar servidor
uvicorn app.main:app --reload
```

---

## 📦 O que será instalado?

### Dependências Base (requirements.txt)
- **FastAPI** - Framework web moderno
- **Uvicorn** - Servidor ASGI
- **httpx** - Cliente HTTP assíncrono
- **Pydantic v2** - Validação de dados
- **python-dotenv** - Gerenciamento de variáveis de ambiente

### Dependências Adicionais
- **beautifulsoup4** - Scraping de HTML
- **lxml** - Parser HTML rápido
- **PyMuPDF (fitz)** - Extração de texto de PDFs
- **unidecode** - Normalização de texto

---

## ✅ Verificar Instalação

Após a instalação, teste com:

```bash
python -c "from app.services.aggregator import SearchAggregator; print('✅ OK!')"
```

---

## 🌐 Acessar o Sistema

Depois de instalado, acesse:

- **Interface Web:** http://localhost:8000
- **Documentação API:** http://localhost:8000/docs
- **API Alternativa:** http://localhost:8000/redoc

---

## 🔧 Configuração (Opcional)

### Credenciais INLabs

Para usar as funcionalidades de download de PDF do DOU, configure no arquivo `.env`:

```env
INLABS_USERNAME=seu_email@exemplo.com
INLABS_PASSWORD=sua_senha
```

Para criar conta no INLabs: https://inlabs.in.gov.br

### DataJud - Chave Pública

Configure a chave pública do CNJ:

```env
DATAJUD_PUBLIC_KEY=sua_chave_publica
```

Para obter chave: https://datajud-wiki.cnj.jus.br

---

## 📊 Fontes Disponíveis

Após instalação completa, você terá acesso a **9 fontes de dados**:

| # | Fonte | Tipo | Requer Config |
|---|-------|------|---------------|
| 1 | Querido Diário | Municipal | ❌ |
| 2 | DataJud | Judicial | ✅ (chave pública) |
| 3 | TCU | Federal | ❌ |
| 4 | TCU Enhanced | Federal | ❌ |
| 5 | TCU Acórdãos PDF | Federal | ✅ (INLabs) |
| 6 | DOU | Federal | ❌ |
| 7 | INLabs | Federal | ✅ (login) |
| 8 | DOU Scrapy | Federal | ❌ |
| 9 | DOU Dados Abertos | Federal | ❌ |

**Nota:** Mesmo sem configurar credenciais, **7 de 9 fontes** funcionam imediatamente!

---

## ⚠️ Solução de Problemas

### Erro: "Python não reconhecido"

Instale o Python 3.11+ de: https://www.python.org/downloads/

**Importante:** Marque a opção "Add Python to PATH" durante a instalação.

### Erro ao instalar PyMuPDF

```bash
pip install --upgrade pip setuptools wheel
pip install pymupdf --no-cache-dir
```

### Erro ao instalar lxml

```bash
pip install lxml --only-binary :all:
```

### Servidor não inicia

Verifique se outra aplicação já está usando a porta 8000:

```bash
# Usar porta alternativa
uvicorn app.main:app --reload --port 8001
```

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique se o Python 3.11+ está instalado
2. Execute o `instalar.bat` como Administrador
3. Consulte o arquivo `INSTALL_WINDOWS.md` para detalhes
4. Abra uma issue no GitHub

---

## 🎉 Pronto para Usar!

Após a instalação, você pode:

- ✅ Fazer buscas unificadas em 9 fontes
- ✅ Buscar acórdãos do TCU em PDFs
- ✅ Exportar resultados em DOCX
- ✅ Usar paginação de 100 resultados
- ✅ Aplicar filtros por estado, data, etc.

**Boas buscas!** 🚀
