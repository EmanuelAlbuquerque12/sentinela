"""
Serviços de integração com fontes de dados
"""
from .querido_diario import QueridoDiarioService
from .datajud import DataJudService
from .tcu import TCUService
from .tcu_enhanced import TCUEnhancedService
from .tcu_acordaos import TCUAcordaosService
from .dou import DOUService
from .inlabs import INLabsService
from .dou_scrapy import DOUScrapyService
from .dou_dados_abertos import DOUDadosAbertosService
from .aggregator import SearchAggregator

__all__ = [
    "QueridoDiarioService",
    "DataJudService",
    "TCUService",
    "TCUEnhancedService",
    "TCUAcordaosService",
    "DOUService",
    "INLabsService",
    "DOUScrapyService",
    "DOUDadosAbertosService",
    "SearchAggregator",
]
