"""
Agregador de buscas - coordena buscas paralelas em múltiplas fontes
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import date

from app.config import get_settings
from app.models.schemas import SearchRequest, SearchResponse, UnifiedResult, SourceInfo, SortBy
from app.services.querido_diario import QueridoDiarioService
from app.services.datajud import DataJudService
from app.services.tcu import TCUService
from app.services.tcu_enhanced import TCUEnhancedService
from app.services.tcu_acordaos import TCUAcordaosService
from app.services.dou import DOUService
from app.services.inlabs import INLabsService
from app.services.dou_scrapy import DOUScrapyService
from app.services.dou_dados_abertos import DOUDadosAbertosService
from app.utils.helpers import parse_search_query


class SearchAggregator:
    """
    Coordena buscas paralelas em múltiplas fontes de dados oficiais brasileiras
    """

    def __init__(self):
        self.settings = get_settings()

        # Instanciar serviços
        self.querido_diario = QueridoDiarioService()
        self.datajud = DataJudService()
        self.tcu = TCUService()
        self.tcu_enhanced = TCUEnhancedService()
        self.tcu_acordaos = TCUAcordaosService()
        self.dou = DOUService()
        self.inlabs = INLabsService()
        self.dou_scrapy = DOUScrapyService()
        self.dou_dados_abertos = DOUDadosAbertosService()

        # Mapear nomes de fontes para serviços
        self.sources = {
            "querido_diario": self.querido_diario,
            "datajud": self.datajud,
            "tcu": self.tcu,
            "tcu_enhanced": self.tcu_enhanced,
            "tcu_acordaos": self.tcu_acordaos,
            "dou": self.dou,
            "inlabs": self.inlabs,
            "dou_scrapy": self.dou_scrapy,
            "dou_dados_abertos": self.dou_dados_abertos,
        }

    async def search_all(self, request: SearchRequest) -> SearchResponse:
        """
        Executa busca unificada em todas as fontes (ou nas especificadas)

        Args:
            request: Requisição de busca com parâmetros

        Returns:
            Resposta agregada com resultados normalizados de todas as fontes
        """
        start_time = time.time()

        # Detectar busca exata automaticamente se não especificado
        query_clean, is_exact = parse_search_query(request.query)
        if request.exact_match is None:
            request.exact_match = is_exact
        # Atualizar query limpa (sem aspas)
        request.query = query_clean

        # Determinar quais fontes consultar
        sources_to_query = request.fontes if request.fontes else list(self.sources.keys())

        # Criar tasks assíncronas para cada fonte
        tasks = []
        source_names = []

        for source_name in sources_to_query:
            if source_name not in self.sources:
                continue

            service = self.sources[source_name]
            task = self._search_source_safe(
                service=service,
                source_name=source_name,
                request=request
            )
            tasks.append(task)
            source_names.append(source_name)

        # Executar todas as buscas em paralelo
        results_list = await asyncio.gather(*tasks)

        # Processar resultados
        all_results: List[UnifiedResult] = []
        errors: List[Dict[str, str]] = []
        successful_sources = 0

        for source_name, result in zip(source_names, results_list):
            if isinstance(result, dict) and "error" in result:
                # Fonte retornou erro
                errors.append({
                    "fonte": source_name,
                    "erro": result["error"]
                })
            else:
                # Fonte retornou resultados
                successful_sources += 1
                all_results.extend(result)

        # Ordenar resultados
        all_results = self._sort_results(all_results, request.sort_by)

        # Aplicar paginação
        total_results = len(all_results)
        paginated_results = all_results[request.offset:request.offset + request.size]

        # Calcular tempo de execução
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Informações de paginação
        paginacao = {
            "size": request.size,
            "offset": request.offset,
            "total": total_results,
            "has_next": (request.offset + request.size) < total_results,
            "has_prev": request.offset > 0
        }

        return SearchResponse(
            total_resultados=total_results,
            fontes_consultadas=len(sources_to_query),
            fontes_sucesso=successful_sources,
            tempo_consulta_ms=elapsed_ms,
            resultados=paginated_results,
            erros=errors,
            paginacao=paginacao
        )

    async def _search_source_safe(
        self,
        service: Any,
        source_name: str,
        request: SearchRequest
    ) -> List[UnifiedResult] | Dict[str, str]:
        """
        Executa busca em uma fonte com tratamento de erros

        Args:
            service: Instância do serviço (QueridoDiarioService, etc)
            source_name: Nome da fonte
            request: Requisição de busca

        Returns:
            Lista de resultados ou dicionário com erro
        """
        try:
            # Mapear parâmetros específicos para cada serviço
            params = {
                "query": request.query,
                "data_inicio": request.data_inicio,
                "data_fim": request.data_fim,
                "size": request.size,
                "offset": request.offset,
                "exact_match": request.exact_match or False
            }

            # Parâmetros específicos por fonte
            if source_name == "querido_diario":
                params["territory_ids"] = request.municipios
                params["ufs"] = request.ufs

            elif source_name == "datajud":
                # Para DataJud, podemos mapear UFs para tribunais
                tribunais = None
                if request.ufs:
                    tribunais = [f"tj{uf.lower()}" for uf in request.ufs]
                params["tribunais"] = tribunais

            elif source_name in ["dou", "inlabs"]:
                # DOU e INLabs suportam busca exata nativa
                params["exact_match"] = request.exact_match or False

            # Executar busca com timeout
            try:
                results = await asyncio.wait_for(
                    service.search(**params),
                    timeout=self.settings.aggregator_timeout
                )
                return results

            except asyncio.TimeoutError:
                return {"error": f"Timeout ao consultar {source_name}"}

        except Exception as e:
            return {"error": str(e)}

    def _sort_results(
        self,
        results: List[UnifiedResult],
        sort_by: SortBy
    ) -> List[UnifiedResult]:
        """
        Ordena resultados conforme critério especificado

        Args:
            results: Lista de resultados
            sort_by: Critério de ordenação

        Returns:
            Lista ordenada
        """
        if sort_by == SortBy.RELEVANCE:
            # Ordenar por relevância (score) decrescente
            return sorted(results, key=lambda x: x.relevancia, reverse=True)

        elif sort_by == SortBy.DATE_DESC:
            # Ordenar por data decrescente (mais recente primeiro)
            return sorted(results, key=lambda x: x.data_publicacao, reverse=True)

        elif sort_by == SortBy.DATE_ASC:
            # Ordenar por data crescente (mais antiga primeiro)
            return sorted(results, key=lambda x: x.data_publicacao)

        return results

    async def get_available_sources(self) -> List[SourceInfo]:
        """
        Lista todas as fontes disponíveis com seus status

        Returns:
            Lista de informações sobre cada fonte
        """
        sources_info = []

        # Executar health checks em paralelo
        health_checks = {
            name: service.health_check()
            for name, service in self.sources.items()
        }

        health_results = await asyncio.gather(
            *health_checks.values(),
            return_exceptions=True
        )

        # Processar resultados
        for (name, service), health in zip(self.sources.items(), health_results):
            info_dict = service.get_source_info()

            # Atualizar status baseado no health check
            if isinstance(health, Exception):
                status = "error"
            elif isinstance(health, dict):
                status = health.get("status", "unknown")
            else:
                status = "unknown"

            source_info = SourceInfo(
                nome=info_dict["nome"],
                tipo=info_dict["tipo"],
                descricao=info_dict["descricao"],
                cobertura=info_dict["cobertura"],
                requer_autenticacao=info_dict["requer_autenticacao"],
                status=status,
                limitacoes=info_dict.get("limitacoes", [])
            )

            sources_info.append(source_info)

        return sources_info

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Executa health check em todas as fontes em paralelo

        Returns:
            Dicionário com status de cada fonte
        """
        health_tasks = {
            name: service.health_check()
            for name, service in self.sources.items()
        }

        results = await asyncio.gather(
            *health_tasks.values(),
            return_exceptions=True
        )

        health_status = {}
        for name, result in zip(health_tasks.keys(), results):
            if isinstance(result, Exception):
                health_status[name] = {
                    "status": "error",
                    "erro": str(result)
                }
            else:
                health_status[name] = result

        return health_status

    def get_statistics(self, results: List[UnifiedResult]) -> Dict[str, Any]:
        """
        Calcula estatísticas sobre os resultados

        Args:
            results: Lista de resultados

        Returns:
            Dicionário com estatísticas
        """
        if not results:
            return {
                "total": 0,
                "por_fonte": {},
                "por_uf": {},
                "relevancia_media": 0.0
            }

        # Contar por fonte
        por_fonte = {}
        for result in results:
            fonte = result.fonte
            por_fonte[fonte] = por_fonte.get(fonte, 0) + 1

        # Contar por UF
        por_uf = {}
        for result in results:
            if result.orgao_uf:
                uf = result.orgao_uf
                por_uf[uf] = por_uf.get(uf, 0) + 1

        # Relevância média
        relevancia_media = sum(r.relevancia for r in results) / len(results)

        return {
            "total": len(results),
            "por_fonte": por_fonte,
            "por_uf": por_uf,
            "relevancia_media": round(relevancia_media, 2)
        }
