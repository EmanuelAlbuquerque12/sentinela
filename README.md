# Sentinela - Sistema de Busca Unificada em Diários Oficiais Brasileiros

Sistema completo de busca textual unificada em todos os diários oficiais, cadernos judiciais e publicações oficiais do Brasil, integrando **apenas APIs gratuitas, públicas ou projetos open-source**.

## 🎯 Objetivo

Agregar e normalizar dados de múltiplas fontes oficiais brasileiras:
- **Diário Oficial da União (DOU)** - Imprensa Nacional
- **Diários Judiciais Eletrônicos (DJEN)** - via DataJud/CNJ
- **Boletim TCU (BTCU)** - Tribunal de Contas da União
- **Diários Municipais e Estaduais** - via Querido Diário (OKBR)
- **Tribunais** - APIs públicas de TRTs, TJs e tribunais superiores

## 🚀 Características

- ✅ **100% Gratuito** - Apenas APIs públicas e projetos open-source
- ⚡ **Busca Paralela** - Consultas simultâneas em múltiplas fontes
- 🔄 **Dados Normalizados** - Formato JSON unificado
- 🌐 **API REST** - Endpoints fáceis de usar
- 📚 **Ampla Cobertura** - Centenas de municípios e todos os tribunais

## 📋 Fontes de Dados Integradas

### 1. Querido Diário (Open Knowledge Brasil)
- **Cobertura**: 600+ municípios brasileiros
- **API**: https://api.queridodiario.ok.org.br
- **Tipo**: REST API pública e gratuita
- **Funcionalidades**: Busca por termo, data, município, temas

### 2. DataJud/CNJ (Conselho Nacional de Justiça)
- **Cobertura**: Todos os tribunais brasileiros
- **API**: https://api-publica.datajud.cnj.jus.br
- **Tipo**: REST API pública (requer API Key gratuita)
- **Funcionalidades**: Metadados processuais, busca textual limitada

### 3. TCU (Tribunal de Contas da União)
- **Cobertura**: Acórdãos, deliberações e publicações do TCU
- **API**: https://dados-abertos.apps.tcu.gov.br
- **Tipo**: REST API pública
- **Funcionalidades**: Busca em acórdãos, inabilitados

### 4. Imprensa Nacional (DOU)
- **Cobertura**: Diário Oficial da União (todas as seções)
- **Dados Abertos**: http://dados.gov.br/dataset/diario-oficial-da-uniao
- **Tipo**: Dados abertos mensais + API de pesquisa
- **Funcionalidades**: Busca textual completa no DOU

### 5. Projetos Open-Source Complementares
- **Ro-DOU**: Scraper Apache Airflow para DOU
- **scrapy-diario-oficial-da-uniao**: Spider Scrapy para DOU
- **api_cnj**: Cliente Python para DataJud

## 🏗️ Arquitetura Técnica

```
┌─────────────────────────────────────────────────────────┐
│                    API REST (FastAPI)                    │
│                  /search, /sources, /health              │
└─────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────┴───────────────────────────┐
│              Aggregator Service (Async)                │
│         Busca paralela em múltiplas fontes             │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│ Querido Diário │  │  DataJud/CNJ│  │   TCU / DOU     │
│   Integration  │  │ Integration │  │  Integration    │
└────────────────┘  └─────────────┘  └─────────────────┘
        │                   │                   │
┌───────▼───────────────────▼───────────────────▼────────┐
│               Data Normalizer (JSON)                    │
│  {termo, fonte, data, órgão, snippet, url_original}    │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Tecnologias

- **Backend**: Python 3.10+, FastAPI
- **HTTP Client**: httpx (assíncrono)
- **Validação**: Pydantic v2
- **Cache**: Redis (opcional)
- **Documentação**: OpenAPI/Swagger automático

## 📦 Instalação

```bash
# Clonar repositório
git clone https://github.com/EmanuelAlbuquerque12/sentinela.git
cd sentinela

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas API Keys (se necessário)

# Executar servidor
uvicorn app.main:app --reload
```

## 🔑 Configuração de API Keys

### DataJud/CNJ (Obrigatória)
1. Acesse: https://www.cnj.jus.br/sistemas/datajud/api-publica/
2. Solicite sua chave pública gratuita
3. Adicione ao `.env`: `DATAJUD_API_KEY=sua_chave_aqui`

### Outras APIs
- **Querido Diário**: Sem autenticação necessária ✅
- **TCU**: Sem autenticação necessária ✅
- **DOU**: Dados abertos sem autenticação ✅

## 🚀 Uso da API

### Busca Unificada
```bash
GET /api/v1/search?query=licitacao&data_inicio=2024-01-01&data_fim=2024-12-31
```

**Resposta:**
```json
{
  "total_resultados": 1523,
  "fontes_consultadas": 5,
  "tempo_consulta_ms": 2341,
  "resultados": [
    {
      "termo": "licitação",
      "fonte": "Querido Diário",
      "orgao": "Prefeitura Municipal de São Paulo",
      "data_publicacao": "2024-11-10",
      "snippet": "...processo licitatório nº 2024/001...",
      "url_original": "https://...",
      "relevancia": 0.95
    }
  ]
}
```

### Listar Fontes Disponíveis
```bash
GET /api/v1/sources
```

### Health Check
```bash
GET /api/v1/health
```

## 📊 Cobertura e Limitações

### ✅ Cobertura Atual

| Fonte | Cobertura | Status API |
|-------|-----------|------------|
| Querido Diário | 600+ municípios | ✅ Funcionando |
| DataJud/CNJ | Todos os tribunais | ✅ Funcionando (requer API Key) |
| TCU | Acórdãos e deliberações | ✅ Funcionando |
| DOU | Todas as seções | ⚠️ Dados abertos mensais |
| Tribunais individuais | Variável | ⚠️ Alguns disponíveis |

### ⚠️ Limitações Conhecidas

1. **DOU (Imprensa Nacional)**
   - Dados abertos publicados mensalmente (1ª terça-feira)
   - API de pesquisa existe mas documentação limitada
   - Alternativa: Usar projetos Ro-DOU ou scrapers

2. **DataJud/CNJ**
   - Requer API Key gratuita (solicitar ao CNJ)
   - Limite de 10.000 registros por consulta
   - Não inclui processos sigilosos

3. **Querido Diário**
   - Cobertura ainda em expansão (não cobre todos municípios)
   - Frequência de atualização varia por município

4. **TCU**
   - Indisponível entre 20h-21h (manutenção)
   - Foco em acórdãos (não inclui todo BTCU)

5. **Rate Limiting**
   - Algumas APIs podem ter limites de requisições
   - Implementar backoff exponencial e cache

## 🤝 Contribuindo

Contribuições são bem-vindas! Áreas prioritárias:

- [ ] Adicionar mais fontes de tribunais
- [ ] Implementar cache Redis
- [ ] Adicionar suporte a Elasticsearch
- [ ] Melhorar cobertura de diários estaduais
- [ ] Criar interface web

## 📚 Referências

### APIs Oficiais
- [Querido Diário - OKBR](https://queridodiario.ok.org.br/)
- [DataJud API Pública - CNJ](https://www.cnj.jus.br/sistemas/datajud/api-publica/)
- [TCU Dados Abertos](https://portal.tcu.gov.br/dados-abertos/)
- [Imprensa Nacional - Base DOU](https://www.in.gov.br/acesso-a-informacao/dados-abertos)

### Projetos Open-Source
- [Ro-DOU (Governo BR)](https://github.com/gestaogovbr/Ro-dou)
- [Querido Diário (OKBR)](https://github.com/okfn-brasil/querido-diario)
- [scrapy-diario-oficial-da-uniao](https://github.com/sinayra/scrapy-diario-oficial-da-uniao)
- [api_cnj](https://github.com/jespimentel/api_cnj)

## 📄 Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes.

## ⚖️ Aspectos Legais

- Todos os dados são públicos e de domínio público
- Respeita Lei de Acesso à Informação (LAI - Lei 12.527/2011)
- Segue diretrizes da Lei Geral de Proteção de Dados (LGPD)
- Não acessa processos sigilosos ou dados sensíveis

## 📧 Contato

Projeto desenvolvido para facilitar acesso à informação pública brasileira.

---

**🌟 Se este projeto foi útil, considere dar uma estrela!**
