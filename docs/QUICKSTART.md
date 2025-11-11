# Guia de Início Rápido - Sentinela

## 🚀 Setup em 5 minutos

### 1. Clonar repositório

```bash
git clone https://github.com/EmanuelAlbuquerque12/sentinela.git
cd sentinela
```

### 2. Criar ambiente virtual

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env e adicionar sua API Key do DataJud
# DATAJUD_API_KEY=sua_chave_aqui
```

**⚠️ IMPORTANTE:** Solicite sua API Key gratuita do DataJud em:
https://www.cnj.jus.br/sistemas/datajud/api-publica/

### 5. Executar servidor

```bash
# Modo desenvolvimento (com reload)
uvicorn app.main:app --reload

# Ou usando Python direto
python -m app.main
```

🎉 **Pronto!** API rodando em `http://localhost:8000`

---

## 📖 Primeiros Passos

### Acessar documentação interativa

Abra no navegador:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Fazer primeira busca

#### Via navegador/cURL:

```bash
curl "http://localhost:8000/api/v1/search?query=licitacao&size=5"
```

#### Via Python:

```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/search",
    params={
        "query": "licitação",
        "size": 5
    }
)

print(response.json())
```

#### Via JavaScript:

```javascript
fetch('http://localhost:8000/api/v1/search?query=licitacao&size=5')
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 💡 Exemplos de Uso

### 1. Busca simples

```bash
GET /api/v1/search?query=concurso
```

### 2. Busca com filtro de data

```bash
GET /api/v1/search?query=edital&data_inicio=2024-01-01&data_fim=2024-12-31
```

### 3. Busca em fontes específicas

```bash
GET /api/v1/search?query=contrato&fontes=querido_diario,datajud
```

### 4. Busca por estado

```bash
GET /api/v1/search?query=licitacao&ufs=SP,RJ,MG
```

### 5. Busca com paginação

```bash
GET /api/v1/search?query=portaria&size=20&offset=40
```

### 6. Busca ordenada por data

```bash
GET /api/v1/search?query=nomeacao&sort_by=date_desc
```

### 7. Busca via POST (parâmetros complexos)

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "processo licitatório",
    "data_inicio": "2024-01-01",
    "data_fim": "2024-12-31",
    "fontes": ["querido_diario", "datajud"],
    "ufs": ["SP", "RJ"],
    "size": 20,
    "sort_by": "relevance"
  }'
```

---

## 📊 Outros Endpoints

### Listar fontes disponíveis

```bash
curl "http://localhost:8000/api/v1/sources"
```

**Resposta:**
```json
{
  "total_fontes": 4,
  "fontes": [
    {
      "nome": "Querido Diário",
      "tipo": "municipal",
      "status": "online",
      "requer_autenticacao": false,
      ...
    },
    ...
  ]
}
```

### Health check

```bash
curl "http://localhost:8000/api/v1/health"
```

**Resposta:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "fontes": {
    "querido_diario": {"status": "online", "latency_ms": 150},
    "datajud": {"status": "online", "latency_ms": 320},
    "tcu": {"status": "online", "latency_ms": 280}
  }
}
```

### Estatísticas de busca

```bash
curl "http://localhost:8000/api/v1/stats?query=licitacao"
```

---

## 🔧 Configurações Avançadas

### Arquivo .env

```bash
# Aplicação
DEBUG=True
LOG_LEVEL=INFO

# DataJud (obrigatório para buscar em tribunais)
DATAJUD_API_KEY=sua_chave_aqui

# Timeouts (segundos)
HTTP_TIMEOUT=30
AGGREGATOR_TIMEOUT=120

# Paginação
DEFAULT_PAGE_SIZE=10
MAX_PAGE_SIZE=100

# Cache Redis (opcional)
REDIS_ENABLED=False
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Com Redis cache

```bash
# 1. Instalar e executar Redis
docker run -d -p 6379:6379 redis:alpine

# 2. Habilitar no .env
echo "REDIS_ENABLED=True" >> .env

# 3. Reiniciar aplicação
```

### Com Docker

```bash
# Build
docker build -t sentinela .

# Run
docker run -p 8000:8000 \
  -e DATAJUD_API_KEY=sua_chave \
  sentinela
```

---

## 🐛 Troubleshooting

### Erro: "DataJud não configurado"

**Solução:** Adicione `DATAJUD_API_KEY` no `.env`

```bash
echo "DATAJUD_API_KEY=sua_chave_aqui" >> .env
```

### Erro: "Timeout ao consultar X"

**Solução:** Aumente timeout no `.env`

```bash
echo "HTTP_TIMEOUT=60" >> .env
echo "AGGREGATOR_TIMEOUT=180" >> .env
```

### Erro: "Module not found"

**Solução:** Instale dependências

```bash
pip install -r requirements.txt
```

### Performance lenta

**Dicas:**
1. Reduza `size` nas queries (padrão: 10)
2. Especifique `fontes` (não buscar todas)
3. Use filtros (`ufs`, `data_inicio/fim`)
4. Habilite cache Redis
5. Execute em produção (sem `--reload`)

---

## 📚 Próximos Passos

1. ✅ **Ler documentação completa:** [README.md](../README.md)
2. 📖 **Entender arquitetura:** [ARCHITECTURE.md](ARCHITECTURE.md)
3. 🔌 **Explorar APIs integradas:** [APIs.md](APIs.md)
4. 🧪 **Rodar testes:** `pytest tests/`
5. 🚀 **Deploy em produção:** [Deploy Guide](#deploy)

---

## 📞 Suporte

- **Issues:** https://github.com/EmanuelAlbuquerque12/sentinela/issues
- **Discussions:** https://github.com/EmanuelAlbuquerque12/sentinela/discussions

---

## ⭐ Gostou?

Se o Sentinela foi útil, considere dar uma estrela no GitHub!

**🌟 Star no GitHub:** https://github.com/EmanuelAlbuquerque12/sentinela

---

**Última atualização:** 2024-11-11
