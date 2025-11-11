"""
Rotas de busca e consulta
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import date

from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    SourcesResponse,
    HealthResponse
)
from app.services.aggregator import SearchAggregator
from app.config import get_settings, Settings

router = APIRouter(prefix="/api/v1", tags=["search"])


def get_aggregator():
    """Dependency injection para SearchAggregator"""
    return SearchAggregator()


def get_settings_dep():
    """Dependency injection para Settings"""
    return get_settings()


@router.get("/search", response_model=SearchResponse)
async def search_unified(
    query: str = Query(..., description="Termo de busca", min_length=1),
    data_inicio: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    fontes: Optional[str] = Query(
        None,
        description="Fontes separadas por vírgula (ex: querido_diario,datajud,tcu)"
    ),
    ufs: Optional[str] = Query(
        None,
        description="UFs separadas por vírgula (ex: SP,RJ,MG)"
    ),
    municipios: Optional[str] = Query(
        None,
        description="Códigos IBGE separados por vírgula"
    ),
    size: int = Query(10, ge=1, le=100, description="Resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    sort_by: str = Query("relevance", description="Ordenação: relevance, date_desc, date_asc"),
    aggregator: SearchAggregator = Depends(get_aggregator)
):
    """
    Busca unificada em múltiplas fontes de diários oficiais brasileiros

    Executa busca paralela e assíncrona em:
    - Querido Diário (diários municipais)
    - DataJud/CNJ (processos judiciais)
    - TCU (acórdãos)
    - DOU (diário oficial federal)

    **Exemplos:**

    ```
    # Busca simples
    GET /api/v1/search?query=licitacao

    # Busca com filtro de data
    GET /api/v1/search?query=contrato&data_inicio=2024-01-01&data_fim=2024-12-31

    # Busca em fontes específicas
    GET /api/v1/search?query=edital&fontes=querido_diario,datajud

    # Busca por UF
    GET /api/v1/search?query=concurso&ufs=SP,RJ

    # Busca com paginação
    GET /api/v1/search?query=portaria&size=20&offset=40
    ```
    """
    try:
        # Parsear parâmetros
        fontes_list = fontes.split(",") if fontes else None
        ufs_list = [uf.strip().upper() for uf in ufs.split(",")] if ufs else None
        municipios_list = municipios.split(",") if municipios else None

        # Criar request
        request = SearchRequest(
            query=query,
            data_inicio=data_inicio,
            data_fim=data_fim,
            fontes=fontes_list,
            ufs=ufs_list,
            municipios=municipios_list,
            size=size,
            offset=offset,
            sort_by=sort_by
        )

        # Executar busca agregada
        response = await aggregator.search_all(request)

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar busca: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_unified_post(
    request: SearchRequest,
    aggregator: SearchAggregator = Depends(get_aggregator)
):
    """
    Busca unificada (método POST)

    Permite passar parâmetros mais complexos no body.

    **Exemplo:**

    ```json
    POST /api/v1/search
    {
        "query": "licitação",
        "data_inicio": "2024-01-01",
        "data_fim": "2024-12-31",
        "fontes": ["querido_diario", "datajud"],
        "ufs": ["SP", "RJ"],
        "size": 20,
        "offset": 0,
        "sort_by": "date_desc"
    }
    ```
    """
    try:
        response = await aggregator.search_all(request)
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar busca: {str(e)}"
        )


@router.get("/sources", response_model=SourcesResponse)
async def list_sources(
    aggregator: SearchAggregator = Depends(get_aggregator)
):
    """
    Lista todas as fontes de dados disponíveis

    Retorna informações sobre cada fonte incluindo:
    - Nome e tipo
    - Descrição e cobertura
    - Status atual (online/offline)
    - Requisitos de autenticação
    - Limitações conhecidas
    """
    try:
        sources = await aggregator.get_available_sources()

        return SourcesResponse(
            total_fontes=len(sources),
            fontes=sources
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar fontes: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    aggregator: SearchAggregator = Depends(get_aggregator),
    settings: Settings = Depends(get_settings_dep)
):
    """
    Verifica saúde da aplicação e das fontes integradas

    Retorna status de cada fonte de dados:
    - online: Funcionando normalmente
    - offline: Inacessível
    - degraded: Funcionando com problemas
    - maintenance: Em manutenção programada
    """
    try:
        from datetime import datetime

        # Health check de todas as fontes
        fontes_status = await aggregator.health_check_all()

        # Determinar status geral
        all_online = all(
            s.get("status") == "online"
            for s in fontes_status.values()
        )
        any_online = any(
            s.get("status") == "online"
            for s in fontes_status.values()
        )

        if all_online:
            overall_status = "healthy"
        elif any_online:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            fontes=fontes_status
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao verificar saúde: {str(e)}"
        )


@router.get("/stats")
async def get_statistics(
    query: str = Query(..., description="Termo para estatísticas"),
    aggregator: SearchAggregator = Depends(get_aggregator)
):
    """
    Retorna estatísticas sobre uma busca

    Útil para analytics e visualizações.
    """
    try:
        # Executar busca completa
        request = SearchRequest(
            query=query,
            size=1000  # Buscar muitos para estatísticas
        )

        response = await aggregator.search_all(request)

        # Calcular estatísticas
        stats = aggregator.get_statistics(response.resultados)

        return {
            "query": query,
            "estatisticas": stats,
            "tempo_consulta_ms": response.tempo_consulta_ms
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar estatísticas: {str(e)}"
        )
