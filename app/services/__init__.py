"""
Serviços de integração com fontes de dados
"""
from .querido_diario import QueridoDiarioService
from .datajud import DataJudService
from .tcu import TCUService
from .dou import DOUService
from .inlabs import INLabsService
from .aggregator import SearchAggregator

__all__ = [
    "QueridoDiarioService",
    "DataJudService",
    "TCUService",
    "DOUService",
    "INLabsService",
    "SearchAggregator",
]
