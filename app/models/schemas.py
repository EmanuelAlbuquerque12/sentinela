"""
Schemas Pydantic para request/response da API
"""
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    """Tipos de fontes de dados"""
    MUNICIPAL = "municipal"
    ESTADUAL = "estadual"
    FEDERAL = "federal"
    JUDICIAL = "judicial"
    TCU = "tcu"


class SortBy(str, Enum):
    """Ordenação dos resultados"""
    RELEVANCE = "relevance"
    DATE_DESC = "date_desc"
    DATE_ASC = "date_asc"


class SearchRequest(BaseModel):
    """Request de busca unificada"""
    query: str = Field(..., description="Termo de busca", min_length=1)
    data_inicio: Optional[date] = Field(None, description="Data inicial (YYYY-MM-DD)")
    data_fim: Optional[date] = Field(None, description="Data final (YYYY-MM-DD)")
    fontes: Optional[List[str]] = Field(
        None,
        description="Lista de fontes específicas (querido_diario, datajud, tcu, dou)"
    )
    ufs: Optional[List[str]] = Field(
        None,
        description="Filtrar por UF (ex: ['SP', 'RJ'])",
        max_length=2
    )
    municipios: Optional[List[str]] = Field(
        None,
        description="Códigos IBGE de municípios (ex: ['3550308'])"
    )
    size: int = Field(10, description="Quantidade de resultados por página", ge=1, le=100)
    offset: int = Field(0, description="Offset para paginação", ge=0)
    sort_by: SortBy = Field(SortBy.RELEVANCE, description="Ordenação dos resultados")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Valida e limpa o termo de busca"""
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Query não pode ser vazia")
        return v

    @field_validator("data_fim")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        """Valida que data_fim >= data_inicio"""
        if v and info.data.get("data_inicio"):
            if v < info.data["data_inicio"]:
                raise ValueError("data_fim deve ser >= data_inicio")
        return v


class UnifiedResult(BaseModel):
    """Resultado normalizado de uma publicação"""
    id: str = Field(..., description="ID único (hash)")
    termo_busca: str = Field(..., description="Termo buscado")
    fonte: str = Field(..., description="Nome da fonte (Querido Diário, DataJud, etc)")
    fonte_tipo: SourceType = Field(..., description="Tipo da fonte")
    orgao: str = Field(..., description="Órgão publicador")
    orgao_uf: Optional[str] = Field(None, description="UF do órgão")
    titulo: str = Field(..., description="Título ou identificação da publicação")
    data_publicacao: date = Field(..., description="Data de publicação")
    snippet: str = Field(..., description="Trecho relevante com contexto")
    url_original: str = Field(..., description="URL da publicação original")
    relevancia: float = Field(..., description="Score de relevância (0-1)", ge=0, le=1)
    metadados: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados específicos da fonte"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "qd_3550308_2024-11-10_abc123",
                "termo_busca": "licitação",
                "fonte": "Querido Diário",
                "fonte_tipo": "municipal",
                "orgao": "Prefeitura Municipal de São Paulo",
                "orgao_uf": "SP",
                "titulo": "Edital de Licitação nº 2024/001",
                "data_publicacao": "2024-11-10",
                "snippet": "...processo licitatório nº 2024/001 para contratação de...",
                "url_original": "https://queridodiario.ok.org.br/...",
                "relevancia": 0.95,
                "metadados": {
                    "edicao": "1234",
                    "pagina": 42,
                    "secao": "Licitações"
                }
            }
        }


class SourceInfo(BaseModel):
    """Informações sobre uma fonte de dados"""
    nome: str
    tipo: SourceType
    descricao: str
    cobertura: str
    requer_autenticacao: bool
    status: str  # "online", "offline", "degraded"
    limitacoes: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Response da busca unificada"""
    total_resultados: int = Field(..., description="Total de resultados encontrados")
    fontes_consultadas: int = Field(..., description="Número de fontes consultadas")
    fontes_sucesso: int = Field(..., description="Fontes que responderam com sucesso")
    tempo_consulta_ms: int = Field(..., description="Tempo total da consulta em ms")
    resultados: List[UnifiedResult] = Field(
        default_factory=list,
        description="Lista de resultados normalizados"
    )
    erros: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Erros de fontes que falharam"
    )
    paginacao: Dict[str, Any] = Field(
        default_factory=dict,
        description="Informações de paginação"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_resultados": 1523,
                "fontes_consultadas": 5,
                "fontes_sucesso": 4,
                "tempo_consulta_ms": 2341,
                "resultados": [],
                "erros": [
                    {
                        "fonte": "DOU",
                        "erro": "Timeout na requisição"
                    }
                ],
                "paginacao": {
                    "size": 10,
                    "offset": 0,
                    "has_next": True
                }
            }
        }


class SourcesResponse(BaseModel):
    """Response listando todas as fontes disponíveis"""
    total_fontes: int
    fontes: List[SourceInfo]


class HealthResponse(BaseModel):
    """Response do health check"""
    status: str = Field(..., description="Status geral (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    fontes: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Status de cada fonte integrada"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-11-11T10:00:00",
                "version": "1.0.0",
                "fontes": {
                    "querido_diario": {
                        "status": "online",
                        "latency_ms": 150
                    },
                    "datajud": {
                        "status": "online",
                        "latency_ms": 320
                    },
                    "tcu": {
                        "status": "offline",
                        "erro": "Timeout"
                    }
                }
            }
        }
