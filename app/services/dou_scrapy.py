"""
Serviço de integração com DOU usando Scrapy
Baseado em: https://github.com/sinayra/scrapy-diario-oficial-da-uniao

Fallback para quando INLabs não estiver disponível
"""
import asyncio
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.models.schemas import UnifiedResult, SourceType
from app.utils.helpers import (
    cache_diario,
    get_cached_diario,
    matches_exact_query,
    extract_snippet_with_highlight,
    calculate_relevance_exact,
    generate_hash_id
)


class DOUScrapyService:
    """
    Serviço de scraping do DOU usando técnica similar ao scrapy-diario-oficial-da-uniao

    Importante: Este é um scraper que depende da estrutura HTML do site da IN.
    Use como fallback quando INLabs não estiver disponível.
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://www.in.gov.br"
        self.timeout = 60

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        secao: Optional[str] = None,
        size: int = 10,
        offset: int = 0,
        exact_match: bool = False,
        **kwargs
    ) -> List[UnifiedResult]:
        """
        Busca artigos no DOU usando scraping

        Args:
            query: Termo de busca
            data_inicio: Data inicial
            data_fim: Data final
            secao: Seção (1, 2, 3)
            size: Quantidade de resultados
            offset: Offset
            exact_match: Busca exata

        Returns:
            Lista de resultados
        """
        # Se não especificou datas, usar últimos 7 dias
        if not data_fim:
            data_fim = date.today()
        if not data_inicio:
            data_inicio = data_fim - timedelta(days=7)

        results = []

        # Iterar sobre datas
        current_date = data_inicio
        while current_date <= data_fim and len(results) < (size + offset):
            # Seções a buscar
            secoes = [secao] if secao else ["1", "2", "3"]

            for sec in secoes:
                if len(results) >= (size + offset):
                    break

                # Buscar artigos da data/seção
                artigos = await self._fetch_dou_date(current_date, sec)

                if artigos:
                    # Filtrar por query
                    filtered = self._filter_artigos(
                        artigos,
                        query,
                        exact_match
                    )
                    results.extend(filtered)

            current_date += timedelta(days=1)

        # Aplicar paginação
        return results[offset:offset + size]

    async def _fetch_dou_date(
        self,
        data: date,
        secao: str
    ) -> List[Dict[str, Any]]:
        """
        Busca artigos do DOU para uma data/seção específica

        Usa cache se disponível, senão faz scraping

        Args:
            data: Data da publicação
            secao: Seção do DOU

        Returns:
            Lista de artigos
        """
        # Verificar cache
        cached = get_cached_diario(
            source=f"dou_scrapy_secao_{secao}",
            data=datetime.combine(data, datetime.min.time()),
            max_age_hours=72
        )

        if cached:
            print(f"✓ Cache DOU Scrapy {data} seção {secao}")
            return cached.get("content", [])

        # Não está em cache - fazer scraping
        print(f"⏬ Downloading DOU {data} seção {secao} via scraping...")
        artigos = await self.scrape_dou_edition(data, secao)

        # Salvar em cache se conseguiu baixar
        if artigos:
            cache_diario(
                source=f"dou_scrapy_secao_{secao}",
                data=datetime.combine(data, datetime.min.time()),
                content=artigos,
                metadata={"total_artigos": len(artigos), "metodo": "scraping"}
            )
            print(f"✓ DOU scraped e cached: {len(artigos)} artigos")

        return artigos

    def _filter_artigos(
        self,
        artigos: List[Dict[str, Any]],
        query: str,
        exact_match: bool
    ) -> List[UnifiedResult]:
        """
        Filtra e normaliza artigos baseado na query

        Args:
            artigos: Lista de artigos raw
            query: Termo de busca
            exact_match: Se True, apenas matches exatos

        Returns:
            Lista de resultados normalizados
        """
        results = []

        for artigo in artigos:
            titulo = artigo.get("titulo", "")
            conteudo = artigo.get("conteudo", "")
            texto_completo = f"{titulo} {conteudo}"

            # Verificar match
            if not matches_exact_query(texto_completo, query):
                continue

            # Criar resultado normalizado
            snippet = extract_snippet_with_highlight(
                text=conteudo or titulo,
                query=query,
                exact_match=exact_match,
                max_length=400
            )

            relevancia = calculate_relevance_exact(
                query=query,
                text=texto_completo,
                exact_match=exact_match
            )

            result_id = generate_hash_id(
                "dou_scrapy",
                artigo.get("data", ""),
                artigo.get("secao", ""),
                titulo[:50]
            )

            result = UnifiedResult(
                id=result_id,
                termo_busca=query,
                fonte="DOU (Scrapy)",
                fonte_tipo=SourceType.FEDERAL,
                orgao=artigo.get("orgao", "Órgão Federal"),
                orgao_uf=None,
                titulo=titulo or "Publicação DOU",
                data_publicacao=artigo.get("data_publicacao", date.today()),
                snippet=snippet,
                url_original=artigo.get("url", self.base_url),
                relevancia=relevancia,
                metadados={
                    "secao": artigo.get("secao"),
                    "pagina": artigo.get("pagina"),
                    "exact_match": exact_match,
                    "scraping_method": "scrapy_style"
                }
            )

            results.append(result)

        return results

    async def scrape_dou_edition(
        self,
        data: date,
        secao: str = "1"
    ) -> List[Dict[str, Any]]:
        """
        Faz scraping de uma edição do DOU

        Args:
            data: Data da edição
            secao: Seção (1, 2, 3)

        Returns:
            Lista de artigos extraídos
        """
        try:
            # Construir URL
            data_str = data.strftime("%d-%m-%Y")
            url = f"{self.base_url}/leiturajornal?data={data_str}&secao=dou{secao}"

            print(f"🔍 Scraping DOU {data_str} seção {secao}...")

            # Fazer request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                html = response.text

            # Parsear HTML
            soup = BeautifulSoup(html, 'html.parser')

            # Método 1: Extrair script JSON (similar ao projeto scrapy-diario-oficial-da-uniao)
            artigos = []
            scripts = soup.find_all('script', type='text/javascript')

            for script in scripts:
                if script.string and 'jsonArray' in script.string:
                    # Tentar extrair JSON
                    match = re.search(r'var\s+jsonArray\s*=\s*(\[.*?\]);', script.string, re.DOTALL)
                    if match:
                        try:
                            json_data = json.loads(match.group(1))
                            artigos = self._parse_json_artigos(json_data, data, secao)
                            print(f"✓ Extraídos {len(artigos)} artigos via JSON")
                            break
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Erro ao parsear JSON: {e}")

            # Método 2: Fallback - extrair do HTML diretamente
            if not artigos:
                artigos = self._parse_html_artigos(soup, data, secao)
                if artigos:
                    print(f"✓ Extraídos {len(artigos)} artigos via HTML")

            return artigos

        except Exception as e:
            print(f"❌ Erro ao fazer scraping DOU {data} seção {secao}: {e}")
            return []

    def _parse_json_artigos(
        self,
        json_data: List[Dict],
        data: date,
        secao: str
    ) -> List[Dict[str, Any]]:
        """Parse artigos do JSON extraído"""
        artigos = []

        for item in json_data:
            # Extrair campos do JSON
            url_title = item.get('urlTitle', '')
            titulo = item.get('title', '')
            orgao = item.get('orgao', '')

            # Construir URL do artigo
            url_artigo = f"{self.base_url}/en/web/dou/-/{url_title}" if url_title else ""

            artigo = {
                "titulo": titulo,
                "conteudo": "",  # Requer download do artigo específico
                "orgao": orgao,
                "secao": secao,
                "pagina": item.get('pagina', ''),
                "data_publicacao": data,
                "url": url_artigo,
                "data": data.strftime("%Y-%m-%d"),
                "json_raw": item
            }

            artigos.append(artigo)

        return artigos

    def _parse_html_artigos(
        self,
        soup: BeautifulSoup,
        data: date,
        secao: str
    ) -> List[Dict[str, Any]]:
        """Parse artigos extraindo do HTML (fallback)"""
        artigos = []

        # Tentar encontrar containers de artigos
        # A estrutura pode variar, tentando seletores comuns
        containers = soup.find_all(['article', 'div'], class_=re.compile(r'resultado|artigo|item', re.I))

        for container in containers:
            try:
                # Extrair título
                titulo_tag = container.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'titulo|title', re.I))
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""

                # Extrair link
                link_tag = container.find('a', href=True)
                url = f"{self.base_url}{link_tag['href']}" if link_tag else ""

                # Extrair texto/resumo
                texto = container.get_text(strip=True, separator=' ')

                if titulo or texto:
                    artigo = {
                        "titulo": titulo or texto[:100],
                        "conteudo": texto,
                        "orgao": "Órgão Federal",
                        "secao": secao,
                        "pagina": "",
                        "data_publicacao": data,
                        "url": url or self.base_url,
                        "data": data.strftime("%Y-%m-%d")
                    }
                    artigos.append(artigo)

            except Exception as e:
                continue

        return artigos

    async def health_check(self) -> Dict[str, Any]:
        """Verifica disponibilidade do serviço"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(f"{self.base_url}/leiturajornal")

                if response.status_code < 500:
                    return {
                        "status": "online",
                        "message": "Site acessível - scraping funcional",
                        "implementation": "complete",
                        "metodos": ["JSON extraction", "HTML parsing"]
                    }
                else:
                    return {
                        "status": "offline",
                        "erro": f"Status {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "offline",
                "erro": str(e)
            }

    def get_source_info(self) -> Dict[str, Any]:
        """Informações sobre a fonte"""
        return {
            "nome": "DOU (Scrapy)",
            "tipo": "federal",
            "descricao": "Scraping do site do DOU (fallback para INLabs)",
            "cobertura": "Todas as seções do DOU",
            "requer_autenticacao": False,
            "status": "operacional",
            "limitacoes": [
                "Depende da estrutura HTML do site (pode quebrar)",
                "Mais lento que INLabs (requer scraping)",
                "Use INLabs como primeira opção",
                "Conteúdo completo pode não estar disponível"
            ],
            "vantagens": [
                "Não requer autenticação",
                "Fallback quando INLabs falha",
                "Acesso direto ao site público",
                "Baseado em projeto open-source testado",
                "Cache de 72 horas",
                "Duplo método: JSON + HTML parsing"
            ],
            "metodos": [
                "Extração de JSON embedded no HTML",
                "Parsing de HTML como fallback",
                "Cache automático de resultados"
            ],
            "github_reference": "https://github.com/sinayra/scrapy-diario-oficial-da-uniao",
            "license": "GPL-3.0 (projeto original)"
        }
