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
- 🖥️ **Interface Web Moderna** - UI intuitiva com tema dark/light
- 📚 **Ampla Cobertura** - Centenas de municípios e todos os tribunais
- 🎯 **Iniciar com 1 Clique** - Scripts .bat (Windows) e .sh (Linux/Mac)

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

### 5. INLabs (Imprensa Nacional)
- **Cobertura**: Diário Oficial da União - acesso completo em XML/PDF
- **Portal**: https://inlabs.in.gov.br
- **Tipo**: Portal com autenticação (credenciais configuradas)
- **Funcionalidades**: Download de edições completas, busca em XML, todas as seções
- **Status**: ✅ Integrado com autenticação automática

### 6. Projetos Open-Source Complementares
- **Ro-DOU**: Scraper Apache Airflow para DOU
- **scrapy-diario-oficial-da-uniao**: Spider Scrapy para DOU
- **api_cnj**: Cliente Python para DataJud

## 🏗️ Arquitetura Técnica

```
┌──────────────────────────────────────────────────────────────┐
│                    API REST (FastAPI)                         │
│                  /search, /sources, /health                   │
└──────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────────┐
│              Aggregator Service (Async)                     │
│         Busca paralela em 5 fontes simultâneas              │
└──────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼──────────────────┬──────────┐
        │                   │                  │          │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────┐  ┌─▼──────┐
│ Querido Diário │  │  DataJud/CNJ│  │    TCU     │  │ INLabs │
│   Integration  │  │ Integration │  │Integration │  │  DOU   │
└────────────────┘  └─────────────┘  └────────────┘  └────────┘
        │                   │                │             │
┌───────▼───────────────────▼────────────────▼─────────────▼────┐
│               Data Normalizer (JSON)                           │
│  {termo, fonte, data, órgão, snippet, url_original}           │
└────────────────────────────────────────────────────────────────┘
```

## 🔧 Tecnologias

- **Backend**: Python 3.10+, FastAPI
- **HTTP Client**: httpx (assíncrono)
- **Validação**: Pydantic v2
- **Cache**: Redis (opcional)
- **Documentação**: OpenAPI/Swagger automático

## 📦 Instalação e Uso

### 🎯 Método 1: Iniciar com 1 Clique (Recomendado)

#### Windows
```bash
# Duplo clique no arquivo ou execute:
start.bat
```

#### Linux/Mac
```bash
# Execute:
./start.sh
```

O script automaticamente:
- ✅ Verifica e instala dependências
- ✅ Cria ambiente virtual
- ✅ Configura arquivo .env (se necessário)
- ✅ Inicia o servidor
- ✅ Abre o navegador automaticamente

**Acesse:** http://localhost:8000

### 🔧 Método 2: Manual

```bash
# 1. Clonar repositório
git clone https://github.com/EmanuelAlbuquerque12/sentinela.git
cd sentinela

# 2. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com sua API Key do DataJud (opcional mas recomendado)

# 5. Executar servidor
uvicorn app.main:app --reload
```

**Acesse:** http://localhost:8000

## 🔑 Configuração de API Keys

### DataJud/CNJ (Chave Pública Pré-configurada)
- ✅ **Status**: Chave pública já configurada no código
- 📋 **Fonte**: https://datajud-wiki.cnj.jus.br/
- 🔓 **Tipo**: Chave pública de demonstração (acesso básico)
- Para acesso ampliado, solicite sua própria chave em: https://www.cnj.jus.br/sistemas/datajud/api-publica/

### INLabs/Imprensa Nacional (Pré-configurado)
- ✅ **Status**: Credenciais já configuradas no código
- 🔐 **Portal**: https://inlabs.in.gov.br
- 📥 **Funcionalidade**: Download completo de edições do DOU em XML/PDF
- Para usar suas próprias credenciais, edite o arquivo `.env`:
  - `INLABS_USERNAME=seu_email@example.com`
  - `INLABS_PASSWORD=sua_senha`

### Outras APIs
- **Querido Diário**: Sem autenticação necessária ✅
- **TCU**: Sem autenticação necessária ✅
- **DOU (Dados Abertos)**: Sem autenticação necessária ✅

## 🖥️ Interface Web

O Sentinela inclui uma **interface web moderna e intuitiva** com:

- 🎨 **Design Moderno**: UI limpa com animações suaves
- 🌓 **Tema Dark/Light**: Alternância com persistência
- 🔍 **Busca Avançada**: Filtros por data, UF, fonte
- 📊 **Visualização Rica**: Cards com relevância e snippets
- 📱 **Responsivo**: Funciona em desktop, tablet e mobile
- ⚡ **Zero Dependências**: HTML5, CSS3, JavaScript puro

### Screenshots

**Página Inicial:**
```
┌─────────────────────────────────────────┐
│  🔍 Sentinela                           │
│  Busca Unificada em Diários Oficiais   │
├─────────────────────────────────────────┤
│  [Digite sua busca...]          [🔍]   │
│  ▼ Filtros Avançados                   │
├─────────────────────────────────────────┤
│  📊 1.523 resultados | 4 fontes | 2.3s │
├─────────────────────────────────────────┤
│  📄 Edital de Licitação nº 2024/001    │
│  📅 10/11/2024 | 📍 Pref. SP | 95%     │
│  ...processo licitatório...            │
└─────────────────────────────────────────┘
```

### Acesso

- **Interface Web:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

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

### Outros Endpoints

```bash
# Listar fontes disponíveis
GET /api/v1/sources

# Health check
GET /api/v1/health

# Estatísticas
GET /api/v1/stats?query=licitacao
```

## 📊 Cobertura e Limitações

### ✅ Cobertura Atual

| Fonte | Cobertura | Status API |
|-------|-----------|------------|
| Querido Diário | 600+ municípios | ✅ Funcionando |
| DataJud/CNJ | Todos os tribunais | ✅ Funcionando (chave pública pré-configurada) |
| TCU | Acórdãos e deliberações | ✅ Funcionando |
| DOU (Dados Abertos) | Todas as seções | ⚠️ Dados abertos mensais |
| INLabs/DOU | DOU completo em XML/PDF | ✅ Funcionando (credenciais pré-configuradas) |
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
