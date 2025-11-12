# Integração DOU Scrapy - Guia de Implementação

## 📋 Visão Geral

Este documento explica como integrar o scraping do DOU baseado no projeto [scrapy-diario-oficial-da-uniao](https://github.com/sinayra/scrapy-diario-oficial-da-uniao) ao Sentinela.

## 🏗️ Arquitetura Proposta

### Estratégia de Fallback em Cascata

```
┌─────────────────────────────────────────┐
│     Usuário faz busca no DOU            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  1ª Tentativa: INLabsService            │
│  ✓ XMLs oficiais completos              │
│  ✓ Autenticação configurada             │
│  ✓ Cache implementado                   │
└──────────────┬──────────────────────────┘
               │
               ├─── ✅ Sucesso → Retorna resultados
               │
               ▼ ❌ Falha (SSL, auth, etc)
┌─────────────────────────────────────────┐
│  2ª Tentativa: DOUScrapyService         │
│  ✓ Scraping do site público             │
│  ✓ Sem autenticação                     │
│  ✓ Fallback confiável                   │
└──────────────┬──────────────────────────┘
               │
               ├─── ✅ Sucesso → Retorna resultados
               │
               ▼ ❌ Falha
┌─────────────────────────────────────────┐
│  3ª Tentativa: DOUService (placeholder) │
│  ⚠️  Retorna lista vazia                │
└─────────────────────────────────────────┘
```

## 🔧 Implementação Completa do Scraping

### Passo 1: Adicionar BeautifulSoup ao requirements-full.txt

Já está presente:
```txt
beautifulsoup4
```

### Passo 2: Implementar método de scraping real

**Localização:** `app/services/dou_scrapy.py`

```python
async def scrape_dou_edition(
    self,
    data: date,
    secao: str = "1"
) -> List[Dict[str, Any]]:
    """
    Faz scraping real de uma edição do DOU

    Baseado em: https://github.com/sinayra/scrapy-diario-oficial-da-uniao
    """
    import httpx
    from bs4 import BeautifulSoup
    import re

    # URL do jornal
    url = f"{self.base_url}/leiturajornal"
    params = {
        "data": data.strftime("%d-%m-%Y"),
        "secao": f"dou{secao}"
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

        # Parsear HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscar script JSON com dados dos artigos
        # O site embute JSON em tags <script type="application/json">
        scripts = soup.find_all('script', type='application/json')

        artigos = []
        for script in scripts:
            try:
                data_json = json.loads(script.string)

                # Estrutura varia, mas geralmente tem:
                # - jsonArray com URLs e títulos
                # - Metadados da edição

                if 'jsonArray' in data_json:
                    for item in data_json['jsonArray']:
                        artigo = {
                            "titulo": item.get('title', ''),
                            "url": self.base_url + item.get('urlTitle', ''),
                            "orgao": item.get('name', 'Órgão Federal'),
                            "secao": secao,
                            "data_publicacao": data,
                            "pagina": item.get('numberPage'),
                            "conteudo": ""  # Seria necessário fazer outra request
                        }
                        artigos.append(artigo)

            except json.JSONDecodeError:
                continue

        # Salvar em cache
        if artigos:
            cache_diario(
                source=f"dou_scrapy_secao_{secao}",
                data=datetime.combine(data, datetime.min.time()),
                content=artigos,
                metadata={
                    "secao": secao,
                    "total_artigos": len(artigos)
                }
            )
            print(f"✓ Scraped {len(artigos)} artigos DOU {data} seção {secao}")

        return artigos

    except Exception as e:
        print(f"❌ Erro no scraping DOU: {e}")
        return []
```

### Passo 3: Atualizar aggregator para usar fallback

**Localização:** `app/services/aggregator.py`

```python
from app.services.dou_scrapy import DOUScrapyService

class SearchAggregator:
    def __init__(self):
        # ... outros serviços ...
        self.inlabs = INLabsService()
        self.dou_scrapy = DOUScrapyService()  # Novo fallback

        self.sources = {
            # ... outras fontes ...
            "inlabs": self.inlabs,
            "dou_scrapy": self.dou_scrapy,  # Adicionar como fonte
        }

    async def _search_source_safe(self, service, source_name, request):
        """Busca com fallback automático"""

        # Se for busca no DOU, tentar INLabs primeiro
        if source_name == "inlabs":
            try:
                results = await service.search(**params)
                if results:  # Se INLabs funcionou, retornar
                    return results

                # Se INLabs não retornou resultados, tentar scrapy
                print("⚠️ INLabs sem resultados, tentando DOU Scrapy...")
                return await self.dou_scrapy.search(**params)

            except Exception as e:
                print(f"❌ INLabs falhou: {e}")
                print("🔄 Fallback para DOU Scrapy...")

                # Fallback para scraping
                try:
                    return await self.dou_scrapy.search(**params)
                except Exception as e2:
                    return {"error": f"Ambos falharam: INLabs={e}, Scrapy={e2}"}

        # Outras fontes seguem fluxo normal
        # ... código existente ...
```

## 📝 Exemplo de Uso

```python
# Busca automática com fallback
request = SearchRequest(
    query="licitação",
    data_inicio=date(2024, 11, 1),
    data_fim=date(2024, 11, 12),
    fontes=["inlabs"]  # Tenta INLabs, faz fallback se falhar
)

response = await aggregator.search_all(request)
```

## 🎯 Vantagens desta Abordagem

| Aspecto | Vantagem |
|---------|----------|
| **Confiabilidade** | Se INLabs cair, scrapy funciona |
| **Performance** | INLabs é mais rápido quando funciona |
| **Manutenção** | Código isolado, fácil de atualizar |
| **Cache** | Ambos usam sistema unificado |
| **Transparência** | Usuário não precisa saber qual está usando |

## ⚠️ Considerações Importantes

### 1. Legalidade e Ética
- ✅ DOU é **público** e **gratuito**
- ✅ Scraping para fins de **pesquisa e acesso à informação** é legítimo
- ✅ Não sobrecarregar servidores (usar delays e cache)

### 2. Manutenção
- ⚠️ **HTML do site pode mudar** - scraper pode quebrar
- 💡 Solução: Monitorar e atualizar selectores quando necessário
- 💡 INLabs como principal, scrapy como backup

### 3. Performance
- 📊 INLabs: ~2-5s por edição (download XML)
- 📊 Scrapy: ~3-10s por edição (scraping + parsing)
- 💾 Cache: <1s (ambos)

### 4. Completude
- INLabs: Edição completa em XML estruturado ⭐
- Scrapy: Lista de artigos, precisa segunda request para conteúdo

## 🚀 Roadmap de Implementação

### Fase 1: Estrutura Base ✅
- [x] Criar `DOUScrapyService` com interface
- [x] Documentar estratégia de fallback
- [x] Preparar métodos placeholder

### Fase 2: Scraping Básico (Próximo)
- [ ] Implementar `scrape_dou_edition()` real
- [ ] Testar extração de artigos
- [ ] Validar cache funcionando

### Fase 3: Integração Completa
- [ ] Integrar no aggregator com fallback
- [ ] Adicionar métricas de qual fonte foi usada
- [ ] Logs detalhados de fallback

### Fase 4: Otimizações
- [ ] Scraping de conteúdo completo do artigo
- [ ] Paralelização de requests
- [ ] Rate limiting inteligente

## 📚 Referências

- **Projeto Original**: https://github.com/sinayra/scrapy-diario-oficial-da-uniao
- **Licença**: GPL-3.0 (requer código aberto)
- **Site DOU**: https://www.in.gov.br/leiturajornal
- **Documentação Scrapy**: https://docs.scrapy.org/

## 💡 Conclusão

O projeto `scrapy-diario-oficial-da-uniao` é **extremamente útil** como:
1. **Referência técnica** de como o site funciona
2. **Base de código** para implementar scraping
3. **Fallback** quando INLabs falhar

**Recomendação**: Manter INLabs como primário, implementar scrapy como backup robusto.
