"""
Serviços de integração com fontes de dados
"""
from .querido_diario import QueridoDiarioService
from .datajud import DataJudService
from .tcu import TCUService
from .tcu_enhanced import TCUEnhancedService
from .dou import DOUService
from .inlabs import INLabsService
from .dou_scrapy import DOUScrapyService
from .aggregator import SearchAggregator

__all__ = [
    "QueridoDiarioService",
    "DataJudService",
    "TCUService",
    "TCUEnhancedService",
    "DOUService",
    "INLabsService",
    "DOUScrapyService",
    "SearchAggregator",
]
