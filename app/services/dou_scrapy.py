"""
Serviço de integração com DOU usando Scrapy
Baseado em: https://github.com/sinayra/scrapy-diario-oficial-da-uniao

Fallback para quando INLabs não estiver disponível
"""
import asyncio
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
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

        # Não está em cache - precisaria fazer scraping
        # Por enquanto, retornar vazio (implementação futura)
        print(f"⚠️  DOU Scrapy: data {data} seção {secao} não disponível")

        # TODO: Implementar scraping real usando httpx + BeautifulSoup
        # Isso requereria:
        # 1. Fazer request para https://www.in.gov.br/leiturajornal
        # 2. Extrair script JSON com dados das seções
        # 3. Parsear artigos
        # 4. Salvar em cache

        return []

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

        NOTA: Implementação futura usando httpx + BeautifulSoup
        Atualmente retorna lista vazia

        Args:
            data: Data da edição
            secao: Seção (1, 2, 3)

        Returns:
            Lista de artigos extraídos
        """
        # TODO: Implementar scraping real
        # Passos:
        # 1. Construir URL: f"{self.base_url}/leiturajornal?data={data:%d-%m-%Y}&secao=dou{secao}"
        # 2. Fazer request com httpx
        # 3. Parsear HTML com BeautifulSoup
        # 4. Extrair script JSON com dados
        # 5. Processar artigos
        # 6. Salvar em cache

        print(f"⚠️  Scraping não implementado ainda para {data} seção {secao}")
        return []

    async def health_check(self) -> Dict[str, Any]:
        """Verifica disponibilidade do serviço"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(f"{self.base_url}/leiturajornal")

                if response.status_code < 500:
                    return {
                        "status": "online",
                        "message": "Site acessível (scraping não implementado ainda)",
                        "implementation": "placeholder"
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
            "status": "em desenvolvimento",
            "limitacoes": [
                "Depende da estrutura HTML do site (pode quebrar)",
                "Scraping não totalmente implementado ainda",
                "Mais lento que INLabs",
                "Use INLabs como primeira opção"
            ],
            "vantagens": [
                "Não requer autenticação",
                "Fallback quando INLabs falha",
                "Acesso direto ao site público",
                "Baseado em projeto open-source testado"
            ],
            "github_reference": "https://github.com/sinayra/scrapy-diario-oficial-da-uniao",
            "license": "GPL-3.0 (projeto original)"
        }
