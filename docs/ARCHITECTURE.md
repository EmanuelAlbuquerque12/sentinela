# Arquitetura do Sentinela

## Visão Geral

O Sentinela é um sistema de busca unificada que agrega dados de múltiplas fontes públicas de diários oficiais brasileiros, utilizando apenas APIs gratuitas e projetos open-source.

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      Cliente HTTP                            │
│              (Navegador, cURL, App Mobile)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               Routers (Endpoints)                     │  │
│  │  - GET/POST /api/v1/search                           │  │
│  │  - GET /api/v1/sources                               │  │
│  │  - GET /api/v1/health                                │  │
│  │  - GET /api/v1/stats                                 │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │            SearchAggregator                           │  │
│  │  - Coordena buscas paralelas                         │  │
│  │  - Normaliza resultados                              │  │
│  │  - Gerencia timeouts e erros                         │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                    │
│         ┌───────────────┼───────────────┐                  │
│         │               │               │                   │
│  ┌──────▼────────┐ ┌───▼──────┐ ┌─────▼──────┐           │
│  │ Querido Diário│ │ DataJud  │ │    TCU     │           │
│  │   Service     │ │ Service  │ │  Service   │           │
│  └───────────────┘ └──────────┘ └────────────┘           │
│         │               │               │                   │
└─────────┼───────────────┼───────────────┼───────────────────┘
          │               │               │
          ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                   APIs Externas (Async)                      │
├─────────────────────────────────────────────────────────────┤
│  Querido Diário      DataJud/CNJ          TCU               │
│  api.queridodiario   api-publica.datajud  dados-abertos.tcu │
│  ✅ Sem Auth         🔑 API Key           ✅ Sem Auth       │
└─────────────────────────────────────────────────────────────┘
          │               │               │
          ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                   DataNormalizer                             │
│  - Normaliza formatos diferentes                            │
│  - Gera IDs únicos                                          │
│  - Calcula relevância                                       │
│  - Extrai snippets                                          │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Resultado Unificado (JSON)                      │
│  {                                                           │
│    id, termo_busca, fonte, fonte_tipo,                      │
│    orgao, titulo, data_publicacao,                          │
│    snippet, url_original, relevancia                        │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Principais

### 1. FastAPI Application (`app/main.py`)

**Responsabilidades:**
- Servidor HTTP assíncrono
- Roteamento de requisições
- Middleware (CORS, logging, error handling)
- Documentação OpenAPI/Swagger
- Health checks

**Tecnologias:**
- FastAPI 0.109+
- Uvicorn (ASGI server)
- Pydantic v2 (validação)

### 2. Routers (`app/routers/`)

**Endpoints expostos:**

#### `GET/POST /api/v1/search`
- Busca unificada em múltiplas fontes
- Suporta filtros (data, UF, município)
- Paginação e ordenação
- Retorna resultados normalizados

#### `GET /api/v1/sources`
- Lista fontes disponíveis
- Status de cada fonte
- Limitações e requisitos

#### `GET /api/v1/health`
- Status da aplicação
- Health check de cada fonte
- Latência de APIs

#### `GET /api/v1/stats`
- Estatísticas de busca
- Distribuição por fonte/UF
- Relevância média

### 3. SearchAggregator (`app/services/aggregator.py`)

**Coordenador central** que:

1. **Distribui buscas** para múltiplos serviços em paralelo
2. **Gerencia timeouts** e erros de cada fonte
3. **Agrega resultados** normalizados
4. **Ordena e pagina** conforme critérios
5. **Calcula estatísticas** gerais

**Fluxo de execução:**

```python
async def search_all(request):
    # 1. Determinar fontes a consultar
    sources = request.fontes or ["querido_diario", "datajud", "tcu"]

    # 2. Criar tasks assíncronas
    tasks = [source.search(**params) for source in sources]

    # 3. Executar em paralelo com timeout
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 4. Processar resultados e erros
    all_results = process_results(results)

    # 5. Ordenar e paginar
    sorted_results = sort_by_relevance(all_results)

    # 6. Retornar resposta agregada
    return SearchResponse(...)
```

### 4. Services (Integradores)

#### `QueridoDiarioService` (`app/services/querido_diario.py`)

**Integração com API do Querido Diário (OKBR)**

- **URL Base:** `https://api.queridodiario.ok.org.br`
- **Autenticação:** Não requerida ✅
- **Cobertura:** 600+ municípios brasileiros

**Principais métodos:**
- `search()` - Busca em diários municipais
- `get_cities()` - Lista cidades disponíveis
- `get_city_by_id()` - Detalhes de município
- `health_check()` - Verifica disponibilidade

**Normalização:**
```python
Querido Diário → UnifiedResult
{
  "territory_id": "3550308",
  "date": "2024-11-10",
  "excerpts": ["..."],
  "url": "https://..."
}
↓
{
  "fonte": "Querido Diário",
  "fonte_tipo": "municipal",
  "orgao": "Prefeitura Municipal de São Paulo",
  "orgao_uf": "SP",
  ...
}
```

#### `DataJudService` (`app/services/datajud.py`)

**Integração com DataJud/CNJ**

- **URL Base:** `https://api-publica.datajud.cnj.jus.br`
- **Autenticação:** API Key obrigatória 🔑
- **Cobertura:** Todos os tribunais brasileiros

**Características:**
- Endpoint por tribunal: `api_publica_{tribunal}/_search`
- Query DSL Elasticsearch
- Busca em movimentos e assuntos processuais
- Limite: 10.000 registros por consulta

**Normalização:**
```python
DataJud (Elasticsearch) → UnifiedResult
{
  "_source": {
    "numeroProcesso": "0001234-56.2024.8.26.0100",
    "movimentos": [...],
    "assuntos": [...]
  }
}
↓
{
  "fonte": "DataJud/TJSP",
  "fonte_tipo": "judicial",
  "orgao": "TJSP - 1ª Vara Cível",
  "titulo": "Processo 0001234-56.2024.8.26.0100",
  ...
}
```

#### `TCUService` (`app/services/tcu.py`)

**Integração com TCU Dados Abertos**

- **URL Base:** `https://dados-abertos.apps.tcu.gov.br/api`
- **Autenticação:** Não requerida ✅
- **Cobertura:** Acórdãos e deliberações do TCU

**Limitações:**
- Indisponível 20h-21h (manutenção)
- Busca textual feita client-side (filtragem local)
- Máximo 100 registros por request

#### `DOUService` (`app/services/dou.py`)

**Integração com DOU**

⚠️ **Status:** Implementação parcial

**Desafios:**
- DOU não possui API oficial documentada
- Dados abertos mensais (delay até 30 dias)
- API de pesquisa não oficial

**Alternativas recomendadas:**
1. **Ro-DOU** (Apache Airflow scraper)
2. **scrapy-diario-oficial-da-uniao**
3. Processar dados abertos mensais

### 5. DataNormalizer (`app/utils/normalizer.py`)

**Responsável por:**

1. **Normalização de formatos** diferentes para `UnifiedResult`
2. **Geração de IDs únicos** (hash MD5)
3. **Extração de snippets** com contexto
4. **Cálculo de relevância** (0-1 score)
5. **Padronização de metadados**

**Métodos principais:**
- `normalize_querido_diario()`
- `normalize_datajud()`
- `normalize_tcu()`
- `normalize_dou()`

**Algoritmo de relevância:**
```python
relevance = frequency_score (0.7 max) + position_score (0.3 max)

frequency_score = min(count / 10.0, 0.7)
position_score = (1.0 - first_pos / text_length) * 0.3
```

### 6. Models (`app/models/schemas.py`)

**Schemas Pydantic** para validação:

- `SearchRequest` - Request de busca
- `SearchResponse` - Response agregada
- `UnifiedResult` - Resultado normalizado
- `SourceInfo` - Info sobre fontes
- `HealthResponse` - Status de saúde

### 7. Configuration (`app/config.py`)

**Gerenciamento de configurações:**

- Carrega variáveis de ambiente (`.env`)
- Valida configurações obrigatórias
- Singleton pattern com `lru_cache`
- Type hints com Pydantic Settings

## Fluxo de Dados

### Exemplo: Busca por "licitação" em SP

```
1. Cliente → GET /api/v1/search?query=licitacao&ufs=SP

2. Router valida parâmetros → SearchRequest

3. SearchAggregator.search_all(request)
   ├── Task 1: QueridoDiarioService.search(query, ufs=["SP"])
   ├── Task 2: DataJudService.search(query, tribunais=["tjsp"])
   ├── Task 3: TCUService.search(query)
   └── await asyncio.gather(*tasks)

4. Cada service:
   ├── Faz request HTTP async para API externa
   ├── Processa resposta
   └── Normaliza com DataNormalizer

5. SearchAggregator:
   ├── Coleta resultados de todos os services
   ├── Trata erros (alguns podem falhar)
   ├── Ordena por relevância
   ├── Aplica paginação
   └── Retorna SearchResponse

6. FastAPI serializa para JSON → Cliente
```

## Decisões de Design

### 1. Arquitetura Assíncrona

**Por quê?**
- Múltiplas APIs externas com latências variadas
- Busca paralela melhora performance drasticamente
- Python asyncio + httpx = throughput elevado

**Resultado:**
- Buscar 3 fontes em paralelo: ~2-3s
- Buscar sequencial: ~8-10s

### 2. Normalização de Dados

**Por quê?**
- Cada fonte tem formato diferente
- Cliente precisa de interface unificada
- Facilita agregação e comparação

**Benefícios:**
- API consistente
- Fácil adicionar novas fontes
- Permite ordenação cross-source

### 3. Tratamento de Erros Granular

**Estratégia:**
- Falha em uma fonte não bloqueia outras
- Erros retornados em campo separado
- Cliente decide como tratar

**Exemplo:**
```json
{
  "fontes_consultadas": 3,
  "fontes_sucesso": 2,
  "resultados": [...],
  "erros": [
    {"fonte": "tcu", "erro": "Timeout"}
  ]
}
```

### 4. Paginação Client-Side

**Por quê?**
- Cada API tem seu próprio sistema de paginação
- Resultados são agregados e re-ordenados
- Total de resultados só conhecido após buscar

**Trade-off:**
- Busca inicial pode trazer mais dados que necessário
- Mas permite ordenação consistente por relevância

## Segurança

### Dados Sensíveis

- ✅ API Keys em variáveis de ambiente
- ✅ Não loga dados sensíveis
- ✅ Respeita processos sigilosos (DataJud filtra)
- ✅ Não armazena dados pessoais

### Rate Limiting

- Implementar throttling por IP (TODO)
- Respeitar rate limits das APIs externas
- Backoff exponencial em erros

### CORS

- Configurável via `.env`
- Padrão: localhost (dev)
- Produção: domínios específicos

## Performance

### Otimizações Implementadas

1. **Busca paralela** com asyncio
2. **Connection pooling** (httpx)
3. **Timeouts configuráveis**
4. **Validação rápida** (Pydantic)

### Otimizações Futuras

1. **Redis cache** para queries frequentes
2. **Elasticsearch** para indexação local
3. **CDN** para assets estáticos
4. **Horizontal scaling** (múltiplas instâncias)

## Escalabilidade

### Vertical

- CPU: Busca paralela usa múltiplos cores
- RAM: ~200MB por instância
- I/O: Limitado pelas APIs externas

### Horizontal

- Stateless (exceto cache Redis opcional)
- Load balancer friendly
- Docker ready

## Monitoramento

### Métricas Chave

- Tempo de resposta por endpoint
- Taxa de sucesso por fonte
- Latência de APIs externas
- Taxa de erro global

### Logging

- Request/response logging
- Error tracking
- Performance profiling

## Testes

### Estratégia

1. **Unit tests** - Normalizer, helpers
2. **Integration tests** - Services com mocks
3. **E2E tests** - API completa
4. **Load tests** - Performance sob carga

### Ferramentas

- pytest
- pytest-asyncio
- httpx-mock
- locust (load testing)

## Deployment

### Requisitos Mínimos

- Python 3.10+
- 512MB RAM
- 1 CPU core
- 1GB storage

### Opções de Deploy

1. **Docker** (recomendado)
2. **Heroku** (Procfile incluído)
3. **AWS Lambda** (com adaptador)
4. **DigitalOcean App Platform**
5. **Render.com**

### Variáveis de Ambiente Obrigatórias

- `DATAJUD_API_KEY` - Para buscar no DataJud/CNJ

### Variáveis Opcionais

- `REDIS_ENABLED=true` - Para cache
- `ELASTICSEARCH_ENABLED=true` - Para indexação

## Extensibilidade

### Adicionar Nova Fonte

1. Criar service em `app/services/{fonte}.py`
2. Implementar método `search()` async
3. Adicionar método `normalize_{fonte}()` no DataNormalizer
4. Registrar no SearchAggregator
5. Adicionar testes

**Template:**
```python
class NovaFonteService:
    async def search(self, query, **params) -> List[UnifiedResult]:
        # 1. Request HTTP async
        # 2. Processar resposta
        # 3. Normalizar com DataNormalizer
        # 4. Retornar lista de UnifiedResult
        pass

    async def health_check(self) -> Dict:
        pass

    def get_source_info(self) -> Dict:
        pass
```

## Referências Técnicas

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [httpx](https://www.python-httpx.org/)

---

**Última atualização:** 2024-11-11
