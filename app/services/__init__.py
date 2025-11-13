"""
Serviços de integração com fontes de dados
Versão com imports condicionais para dependências opcionais
"""

# Serviços essenciais (sempre disponíveis - sem dependências externas)
from .querido_diario import QueridoDiarioService
from .datajud import DataJudService
from .aggregator import SearchAggregator

__all__ = ["QueridoDiarioService", "DataJudService", "SearchAggregator"]

# Serviços com dependências opcionais (importar apenas se disponíveis)
try:
    from .tcu import TCUService
    __all__.append("TCUService")
except ImportError:
    pass

try:
    from .tcu_enhanced import TCUEnhancedService
    __all__.append("TCUEnhancedService")
except ImportError:
    pass

try:
    from .dou import DOUService
    __all__.append("DOUService")
except ImportError:
    pass

try:
    from .inlabs import INLabsService
    __all__.append("INLabsService")
except ImportError:
    pass

# Serviços que requerem beautifulsoup4, lxml, pymupdf
try:
    from .tcu_acordaos import TCUAcordaosService
    __all__.append("TCUAcordaosService")
except ImportError:
    pass

try:
    from .dou_scrapy import DOUScrapyService
    __all__.append("DOUScrapyService")
except ImportError:
    pass

try:
    from .dou_dados_abertos import DOUDadosAbertosService
    __all__.append("DOUDadosAbertosService")
except ImportError:
    pass

