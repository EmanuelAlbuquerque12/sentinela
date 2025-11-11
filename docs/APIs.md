# Documentação Completa das APIs Públicas Integradas

## 1. Querido Diário (Open Knowledge Brasil)

### Informações Gerais
- **URL Base**: `https://api.queridodiario.ok.org.br`
- **Versão**: 0.19.0
- **Autenticação**: Não requerida ✅
- **Formato**: JSON
- **Documentação**: https://api.queridodiario.ok.org.br/docs

### Endpoints Principais

#### 1.1. Busca em Diários
```http
GET /gazettes
```

**Parâmetros:**
- `querystring` (string): Termo de busca (sintaxe OpenSearch)
- `territory_ids` (array): Códigos IBGE de 7 dígitos (ex: 3550308 para São Paulo)
- `published_since` (date): Data início publicação (YYYY-MM-DD)
- `published_until` (date): Data fim publicação (YYYY-MM-DD)
- `scraped_since` (datetime): Data início scraping (ISO 8601)
- `scraped_until` (datetime): Data fim scraping (ISO 8601)
- `size` (int): Tamanho da página (padrão: 10, máx: 1000)
- `offset` (int): Paginação (padrão: 0)
- `sort_by` (enum): relevance | descending_date | ascending_date

**Exemplo:**
```bash
curl "https://api.queridodiario.ok.org.br/gazettes?querystring=licitacao&territory_ids=3550308&published_since=2024-01-01&size=10"
```

**Resposta:**
```json
{
  "total_gazettes": 150,
  "gazettes": [
    {
      "territory_id": "3550308",
      "date": "2024-11-10",
      "url": "https://...",
      "territory_name": "São Paulo",
      "state_code": "SP",
      "edition": "1234",
      "is_extra_edition": false,
      "txt_url": "https://...",
      "scraped_at": "2024-11-11T10:00:00"
    }
  ]
}
```

#### 1.2. Busca por Tema
```http
GET /gazettes/by_theme/{theme}
```

**Temas disponíveis:**
- `contratos`
- `licitacoes`
- `covid-19`
- E outros...

**Parâmetros:**
- Mesmos da busca regular + `theme`
- `subthemes` (array): Subtemas específicos
- `entities` (array): Entidades relacionadas

#### 1.3. Listar Cidades
```http
GET /cities
```

**Parâmetros:**
- `city_name` (string): Nome da cidade
- `state_code` (string): UF (ex: SP, RJ, MG)

**Exemplo:**
```bash
curl "https://api.queridodiario.ok.org.br/cities?city_name=São%20Paulo&state_code=SP"
```

#### 1.4. Detalhes de Cidade
```http
GET /cities/{territory_id}
```

**Exemplo:**
```bash
curl "https://api.queridodiario.ok.org.br/cities/3550308"
```

**Resposta:**
```json
{
  "territory_id": "3550308",
  "territory_name": "São Paulo",
  "state_code": "SP",
  "publication_urls": ["https://..."]
}
```

### Limitações
- ⚠️ Cobertura: ~600 municípios (em expansão)
- ⚠️ Frequência de atualização varia por município
- ✅ Sem limite de requisições documentado
- ✅ Sem necessidade de cadastro/autenticação

---

## 2. DataJud/CNJ (Conselho Nacional de Justiça)

### Informações Gerais
- **URL Base**: `https://api-publica.datajud.cnj.jus.br`
- **Autenticação**: API Key obrigatória 🔑
- **Formato**: JSON (Elasticsearch)
- **Documentação**: https://datajud-wiki.cnj.jus.br/api-publica/

### Obter API Key
1. Acesse: https://www.cnj.jus.br/sistemas/datajud/api-publica/
2. Solicite chave pública (processo gratuito)
3. Aguarde aprovação (geralmente rápido)

### Estrutura de Endpoints

Cada tribunal tem seu próprio endpoint:
```
https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search
```

#### 2.1. Tribunais Superiores
- **STF**: `api_publica_stf/_search`
- **STJ**: `api_publica_stj/_search`
- **TST**: `api_publica_tst/_search`
- **TSE**: `api_publica_tse/_search`
- **STM**: `api_publica_stm/_search`

#### 2.2. Tribunais Regionais Federais
- **TRF1**: `api_publica_trf1/_search`
- **TRF2**: `api_publica_trf2/_search`
- **TRF3**: `api_publica_trf3/_search`
- **TRF4**: `api_publica_trf4/_search`
- **TRF5**: `api_publica_trf5/_search`
- **TRF6**: `api_publica_trf6/_search`

#### 2.3. Tribunais de Justiça Estaduais
Padrão: `api_publica_tj{UF}/_search`
- **TJSP**: `api_publica_tjsp/_search`
- **TJRJ**: `api_publica_tjrj/_search`
- **TJMG**: `api_publica_tjmg/_search`
- E todos os outros 24 estados...

#### 2.4. Tribunais Regionais do Trabalho
Padrão: `api_publica_trt{numero}/_search`
- **TRT1** a **TRT24**: `api_publica_trt1/_search`, etc.

#### 2.5. Tribunais Regionais Eleitorais
Padrão: `api_publica_tre-{uf}/_search`
- **TRE-SP**: `api_publica_tre-sp/_search`
- E todos os outros estados...

### Autenticação

**Header obrigatório:**
```http
Authorization: APIKey SUA_CHAVE_AQUI
```

### Busca com Query DSL (Elasticsearch)

**Busca por Número de Processo:**
```bash
curl -X POST "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search" \
  -H "Authorization: APIKey SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "numeroProcesso": "0001234-56.2024.8.26.0100"
      }
    }
  }'
```

**Busca Textual:**
```json
{
  "query": {
    "multi_match": {
      "query": "licitação",
      "fields": ["movimentos.complementoNacional", "assuntos.*.nome"]
    }
  },
  "size": 100,
  "from": 0
}
```

**Filtros por Data:**
```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"classe.nome": "Procedimento Comum"}}
      ],
      "filter": [
        {
          "range": {
            "dataAjuizamento": {
              "gte": "2024-01-01",
              "lte": "2024-12-31"
            }
          }
        }
      ]
    }
  }
}
```

### Campos Disponíveis na Resposta
```json
{
  "numeroProcesso": "0001234-56.2024.8.26.0100",
  "classe": {"codigo": 123, "nome": "Procedimento Comum"},
  "sistema": "PJe",
  "formato": {"codigo": 1, "nome": "Eletrônico"},
  "tribunal": "TJSP",
  "dataAjuizamento": "2024-01-15T00:00:00",
  "orgaoJulgador": {"codigo": 100, "nome": "1ª Vara Cível"},
  "assuntos": [
    {"codigo": 456, "nome": "Indenização por Dano Material"}
  ],
  "movimentos": [
    {
      "codigo": 789,
      "nome": "Juntada de Documento",
      "dataHora": "2024-01-20T14:30:00",
      "complementoNacional": "Petição inicial"
    }
  ]
}
```

### Limitações
- 🔑 **Requer API Key** (solicitar ao CNJ - processo gratuito)
- ⚠️ **Limite**: 10.000 registros por consulta
- ⚠️ **Não inclui**: Processos sigilosos ou segredos de justiça
- ⚠️ **Rate limit**: Não documentado oficialmente (usar com moderação)

---

## 3. TCU (Tribunal de Contas da União)

### Informações Gerais
- **URL Base**: `https://dados-abertos.apps.tcu.gov.br/api`
- **Autenticação**: Não requerida ✅
- **Formato**: JSON
- **Documentação**: https://portal.tcu.gov.br/webservices-tcu/

### Endpoints Principais

#### 3.1. Buscar Acórdãos
```http
GET /acordao/recupera-acordaos
```

**Parâmetros:**
- `inicio` (int): Índice inicial (paginação)
- `quantidade` (int): Quantidade de resultados

**Exemplo:**
```bash
curl "https://dados-abertos.apps.tcu.gov.br/api/acordao/recupera-acordaos?inicio=0&quantidade=10"
```

**Resposta:**
```json
{
  "data": [
    {
      "key": "12345",
      "tipo": "Acórdão",
      "anoAcordao": 2024,
      "titulo": "Acórdão nº 123/2024 - Plenário",
      "numeroAcordao": 123,
      "colegiado": "Plenário",
      "dataSessao": "2024-11-10",
      "relator": "Ministro Fulano de Tal",
      "situacao": "Publicado",
      "sumario": "Texto do sumário...",
      "urlInteiro": "https://...",
      "urlDocumento": "https://..."
    }
  ]
}
```

#### 3.2. Inabilitados
```http
GET /inabilitados
```

Retorna informações sobre pessoas inabilitadas para cargos públicos.

**Resposta:**
```json
{
  "data": [
    {
      "nome": "Nome da Pessoa",
      "cpf": "***.***.***-**",
      "numeroProcesso": "TC 012345/2024",
      "deliberacao": "Acórdão 456/2024",
      "dataInicio": "2024-01-01",
      "dataFim": "2029-01-01"
    }
  ]
}
```

### Limitações
- ⚠️ **Indisponibilidade**: 20h-21h (manutenção diária)
- ⚠️ **Cobertura**: Foco em acórdãos (não todo o BTCU)
- ✅ Sem necessidade de autenticação
- ✅ Dados públicos e atualizados

---

## 4. Imprensa Nacional (DOU)

### Informações Gerais
- **Dados Abertos**: http://dados.gov.br/dataset/diario-oficial-da-uniao
- **Portal DOU**: https://www.in.gov.br/consulta
- **Frequência**: Dados publicados mensalmente (1ª terça-feira)
- **Formato**: XML, JSON, CSV

### 4.1. Dados Abertos (Publicação Mensal)

**URL do Dataset:**
```
http://dados.gov.br/dataset/diario-oficial-da-uniao
```

**Conteúdo:**
- Publicações do mês anterior
- Todas as seções (1, 2, 3, Extra)
- Metadados completos

**Estrutura de Dados:**
```json
{
  "data_publicacao": "2024-11-10",
  "secao": "1",
  "pagina": 42,
  "titulo": "PORTARIA Nº 123, DE 9 DE NOVEMBRO DE 2024",
  "orgao": "Ministério da Fazenda",
  "conteudo": "Texto completo da publicação...",
  "edicao": "212",
  "url_certificacao": "https://..."
}
```

### 4.2. API de Pesquisa (Não Documentada Oficialmente)

A Imprensa Nacional possui uma API usada pelo portal de consulta, mas não há documentação pública oficial.

**Endpoint inferido:**
```http
GET https://www.in.gov.br/consulta (parâmetros via query string)
```

**Parâmetros possíveis:**
- Termo de busca
- Data início/fim
- Seção
- Órgão

⚠️ **Não recomendado para produção** (sem documentação oficial)

### 4.3. Alternativas Open-Source Recomendadas

#### Ro-DOU (Governo BR)
- **Repositório**: https://github.com/gestaogovbr/Ro-dou
- **Tecnologia**: Apache Airflow
- **Funcionalidade**: DAGs para scraping e clipping do DOU
- **Uso**: Configurar localmente para scraping automático

#### scrapy-diario-oficial-da-uniao
- **Repositório**: https://github.com/sinayra/scrapy-diario-oficial-da-uniao
- **Tecnologia**: Scrapy (Python)
- **Funcionalidade**: Spider para buscar conteúdo do DOU
- **Retorno**: JSON com título e link das matérias

**Exemplo de uso:**
```python
import scrapy

class DOUSpider(scrapy.Spider):
    name = 'dou'
    start_urls = ['https://www.in.gov.br/consulta/']

    def parse(self, response):
        # Extrair publicações
        pass
```

### Limitações
- ⚠️ **Dados abertos**: Atualização mensal (delay de até 30 dias)
- ⚠️ **API não oficial**: Pode mudar sem aviso
- ✅ **Alternativa**: Usar scrapers open-source como Ro-DOU
- ⚠️ **Cloudflare**: Alguns scrapers bloqueados por proteção DDoS

---

## 5. Comparação Geral das Fontes

| Fonte | Autenticação | Cobertura | Atualização | Limitações |
|-------|--------------|-----------|-------------|------------|
| **Querido Diário** | ❌ Não | 600+ municípios | Variável | Cobertura parcial |
| **DataJud/CNJ** | ✅ API Key | Todos tribunais | Tempo real | 10k registros/query |
| **TCU** | ❌ Não | Acórdãos TCU | Diária | Indisponível 20h-21h |
| **DOU** | ❌ Não | DOU completo | Mensal | Delay até 30 dias |
| **Scrapers OSS** | ❌ Não | Variável | Sob demanda | Risco de bloqueio |

---

## 6. Recomendações de Implementação

### 6.1. Estratégia de Integração

1. **Prioridade 1** (APIs prontas):
   - Querido Diário (sem auth)
   - DataJud/CNJ (com API Key)
   - TCU (sem auth)

2. **Prioridade 2** (requer implementação):
   - DOU via dados abertos mensais
   - Scrapers OSS como fallback

### 6.2. Tratamento de Erros

- **Rate Limiting**: Implementar backoff exponencial
- **Timeout**: 30s por fonte, 2min total agregado
- **Fallback**: Se API falhar, tentar fonte alternativa
- **Cache**: Redis para resultados recentes (TTL: 24h)

### 6.3. Normalização de Dados

Campos unificados:
```json
{
  "id": "hash_unico",
  "termo_busca": "licitação",
  "fonte": "Querido Diário",
  "fonte_tipo": "municipal|estadual|federal|judicial",
  "orgao": "Prefeitura Municipal de São Paulo",
  "orgao_uf": "SP",
  "titulo": "Processo Licitatório nº 2024/001",
  "data_publicacao": "2024-11-10",
  "snippet": "...texto relevante com destaque...",
  "conteudo_completo": "Texto integral (opcional)",
  "url_original": "https://...",
  "relevancia": 0.95,
  "metadados": {
    "secao": "Licitações",
    "pagina": 42,
    "edicao": "1234"
  }
}
```

### 6.4. Boas Práticas

- ✅ Respeitar robots.txt e termos de uso
- ✅ Implementar user-agent identificável
- ✅ Adicionar delays entre requisições (1-2s)
- ✅ Logs completos para auditoria
- ✅ Monitoramento de saúde das APIs
- ✅ Documentar todas as limitações

---

## 7. Referências Adicionais

### Artigos e Tutoriais
- [Consulta com Python à API DataJud](https://medium.com/@pimentel.jes/consulta-com-python-à-api-pública-do-datajud-base-de-dados-do-poder-judiciário-do-cnj-670157a392ae)
- [Tutorial API DataJud - CNJ (PDF)](https://www.cnj.jus.br/wp-content/uploads/2023/05/tutorial-api-publica-datajud-beta.pdf)

### Comunidades
- [Querido Diário - Discord OKBR](https://ok.org.br/projetos/querido-diario/)
- [Fórum Dados Abertos Brasil](https://discuss.okfn.org/)

### Legislação Relevante
- Lei de Acesso à Informação (LAI - Lei 12.527/2011)
- Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018)
- Resolução CNJ nº 331/2020 (Base Nacional de Dados do Poder Judiciário)

---

**Última atualização**: 2024-11-11
