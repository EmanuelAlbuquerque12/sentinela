"""
Serviço de integração com a API Pública do DataJud/CNJ
"""
import httpx
from datetime import date
from typing import List, Optional, Dict, Any
from app.config import get_settings
from app.models.schemas import UnifiedResult
from app.utils.normalizer import DataNormalizer


class DataJudService:
    """
    Integração com a API Pública do DataJud (CNJ)
    https://datajud-wiki.cnj.jus.br/api-publica/
    """

    # Lista de tribunais disponíveis
    TRIBUNAIS_SUPERIORES = ["stf", "stj", "tst", "tse", "stm"]

    TRIBUNAIS_REGIONAIS_FEDERAIS = [
        "trf1", "trf2", "trf3", "trf4", "trf5", "trf6"
    ]

    TRIBUNAIS_JUSTICA_ESTADUAIS = [
        "tjac", "tjal", "tjap", "tjam", "tjba", "tjce", "tjdf", "tjes",
        "tjgo", "tjma", "tjmt", "tjms", "tjmg", "tjpa", "tjpb", "tjpr",
        "tjpe", "tjpi", "tjrj", "tjrn", "tjrs", "tjro", "tjrr", "tjsc",
        "tjsp", "tjse", "tjto"
    ]

    TRIBUNAIS_REGIONAIS_TRABALHO = [
        f"trt{i}" for i in range(1, 25)
    ]

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.datajud_base_url
        self.timeout = self.settings.http_timeout
        self.normalizer = DataNormalizer()

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        tribunais: Optional[List[str]] = None,
        size: int = 10,
        offset: int = 0,
        **kwargs  # Aceita parâmetros extras (ex: exact_match)
    ) -> List[UnifiedResult]:
        """
        Busca processos judiciais no DataJud/CNJ

        Args:
            query: Termo de busca
            data_inicio: Data inicial de ajuizamento
            data_fim: Data final de ajuizamento
            tribunais: Lista de tribunais (ex: ['tjsp', 'tjrj'])
            size: Quantidade de resultados
            offset: Offset para paginação

        Returns:
            Lista de resultados normalizados
        """
        if not self.settings.is_datajud_configured:
            raise Exception(
                "DataJud não configurado. Defina DATAJUD_API_KEY no .env"
            )

        # Se não especificou tribunais, usar apenas alguns principais
        if not tribunais:
            # Buscar apenas alguns tribunais por padrão para não sobrecarregar
            tribunais = ["tjsp", "tjrj", "tjmg", "stj"]

        all_results = []

        # Buscar em cada tribunal
        for tribunal in tribunais[:5]:  # Limitar a 5 tribunais por vez
            try:
                results = await self._search_tribunal(
                    tribunal=tribunal,
                    query=query,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    size=size,
                    offset=offset
                )
                all_results.extend(results)
            except Exception as e:
                # Log erro mas continua com outros tribunais
                print(f"Erro ao buscar no {tribunal}: {e}")
                continue

        # Ordenar por relevância e limitar ao size solicitado
        all_results.sort(key=lambda x: x.relevancia, reverse=True)
        return all_results[:size]

    async def _search_tribunal(
        self,
        tribunal: str,
        query: str,
        data_inicio: Optional[date],
        data_fim: Optional[date],
        size: int,
        offset: int
    ) -> List[UnifiedResult]:
        """Busca em um tribunal específico"""
        endpoint = f"{self.base_url}/api_publica_{tribunal}/_search"

        # Construir query Elasticsearch
        es_query = self._build_elasticsearch_query(
            query=query,
            data_inicio=data_inicio,
            data_fim=data_fim,
            size=size,
            offset=offset
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=es_query,
                    headers=self.settings.datajud_headers
                )
                response.raise_for_status()
                data = response.json()

            # Processar hits do Elasticsearch
            hits = data.get("hits", {}).get("hits", [])
            results = []

            for hit in hits:
                try:
                    normalized = self.normalizer.normalize_datajud(
                        hit,
                        query,
                        tribunal=tribunal.upper()
                    )
                    results.append(normalized)
                except Exception as e:
                    print(f"Erro ao normalizar hit: {e}")
                    continue

            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise Exception("API Key do DataJud inválida")
            elif e.response.status_code == 404:
                raise Exception(f"Tribunal {tribunal} não encontrado")
            raise Exception(f"Erro HTTP {e.response.status_code} no DataJud")
        except httpx.TimeoutException:
            raise Exception(f"Timeout ao consultar {tribunal}")
        except Exception as e:
            raise Exception(f"Erro ao consultar {tribunal}: {str(e)}")

    def _build_elasticsearch_query(
        self,
        query: str,
        data_inicio: Optional[date],
        data_fim: Optional[date],
        size: int,
        offset: int
    ) -> Dict[str, Any]:
        """
        Constrói query Elasticsearch/OpenSearch para DataJud

        Busca nos campos:
        - movimentos.complementoNacional (texto dos movimentos)
        - assuntos.*.nome (nome dos assuntos)
        - classe.nome (classe processual)
        """
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "movimentos.complementoNacional",
                        "assuntos.*.nome",
                        "classe.nome"
                    ],
                    "type": "best_fields",
                    "operator": "or"
                }
            }
        ]

        # Filtros de data
        filter_clauses = []
        if data_inicio or data_fim:
            date_filter = {"range": {"dataAjuizamento": {}}}
            if data_inicio:
                date_filter["range"]["dataAjuizamento"]["gte"] = data_inicio.isoformat()
            if data_fim:
                date_filter["range"]["dataAjuizamento"]["lte"] = data_fim.isoformat()
            filter_clauses.append(date_filter)

        query_dsl = {
            "query": {
                "bool": {
                    "must": must_clauses
                }
            },
            "size": min(size, 100),  # Máximo 100 por request
            "from": offset,
            "sort": [
                {"_score": {"order": "desc"}},  # Por relevância primeiro
                {"dataAjuizamento": {"order": "desc"}}  # Depois por data
            ]
        }

        if filter_clauses:
            query_dsl["query"]["bool"]["filter"] = filter_clauses

        return query_dsl

    async def search_by_processo(self, numero_processo: str) -> Optional[UnifiedResult]:
        """
        Busca processo específico por número do CNJ

        Args:
            numero_processo: Número no formato NNNNNNN-DD.AAAA.J.TR.OOOO

        Returns:
            Resultado normalizado ou None
        """
        if not self.settings.is_datajud_configured:
            raise Exception("DataJud não configurado")

        # Extrair tribunal do número do processo (posição TR)
        # Exemplo: 0001234-56.2024.8.26.0100 -> 8.26 = TJSP
        parts = numero_processo.split(".")
        if len(parts) < 4:
            raise ValueError("Número de processo inválido")

        # Mapear código do tribunal (simplificado)
        # 8.26 = TJSP, 8.19 = TJRJ, etc
        tribunal = self._map_tribunal_from_processo(numero_processo)

        if not tribunal:
            raise Exception("Não foi possível identificar o tribunal")

        # Buscar no tribunal específico
        endpoint = f"{self.base_url}/api_publica_{tribunal}/_search"

        query = {
            "query": {
                "match": {
                    "numeroProcesso": numero_processo
                }
            },
            "size": 1
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=query,
                    headers=self.settings.datajud_headers
                )
                response.raise_for_status()
                data = response.json()

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                return None

            return self.normalizer.normalize_datajud(
                hits[0],
                numero_processo,
                tribunal=tribunal.upper()
            )

        except Exception as e:
            raise Exception(f"Erro ao buscar processo: {str(e)}")

    def _map_tribunal_from_processo(self, numero_processo: str) -> Optional[str]:
        """Mapeia número do processo para sigla do tribunal"""
        # Extrair código do tribunal (simplificado)
        # Formato: NNNNNNN-DD.AAAA.J.TR.OOOO
        # J = Justiça (1=Federal, 2=Trabalho, 4=Militar, 8=Estadual, etc)
        parts = numero_processo.split(".")

        if len(parts) < 4:
            return None

        justica = parts[2]
        tribunal = parts[3]

        # Justiça Estadual (8)
        if justica == "8":
            # 26 = SP, 19 = RJ, 13 = MG, etc
            tj_map = {
                "01": "tjac", "02": "tjal", "04": "tjap", "03": "tjam",
                "05": "tjba", "06": "tjce", "07": "tjdf", "08": "tjes",
                "09": "tjgo", "10": "tjma", "11": "tjmt", "12": "tjms",
                "13": "tjmg", "14": "tjpa", "15": "tjpb", "16": "tjpr",
                "17": "tjpe", "18": "tjpi", "19": "tjrj", "20": "tjrn",
                "21": "tjrs", "22": "tjro", "23": "tjrr", "24": "tjsc",
                "26": "tjsp", "25": "tjse", "27": "tjto"
            }
            return tj_map.get(tribunal)

        # Justiça Federal (4)
        elif justica == "4":
            trf_map = {
                "01": "trf1", "02": "trf2", "03": "trf3",
                "04": "trf4", "05": "trf5", "06": "trf6"
            }
            return trf_map.get(tribunal)

        # Justiça do Trabalho (5)
        elif justica == "5":
            # TRT1 a TRT24
            try:
                num = int(tribunal)
                if 1 <= num <= 24:
                    return f"trt{num}"
            except:
                pass

        return None

    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde da API do DataJud"""
        if not self.settings.is_datajud_configured:
            return {
                "status": "unconfigured",
                "erro": "API Key não configurada"
            }

        try:
            import time
            start = time.time()

            # Testar com TJSP (um dos maiores)
            endpoint = f"{self.base_url}/api_publica_tjsp/_search"
            query = {"query": {"match_all": {}}, "size": 1}

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    endpoint,
                    json=query,
                    headers=self.settings.datajud_headers
                )
                response.raise_for_status()

            latency_ms = int((time.time() - start) * 1000)

            return {
                "status": "online",
                "latency_ms": latency_ms
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"status": "error", "erro": "API Key inválida"}
            return {"status": "error", "erro": f"HTTP {e.response.status_code}"}
        except Exception as e:
            return {"status": "offline", "erro": str(e)}

    def get_source_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a fonte"""
        return {
            "nome": "DataJud/CNJ",
            "tipo": "judicial",
            "descricao": "Base Nacional de Dados do Poder Judiciário",
            "cobertura": "Todos os tribunais brasileiros",
            "requer_autenticacao": True,
            "status": "disponível" if self.settings.is_datajud_configured else "não configurado",
            "limitacoes": [
                "Requer API Key gratuita (solicitar ao CNJ)",
                "Máximo 10.000 registros por consulta",
                "Não inclui processos sigilosos",
                "Rate limiting não documentado"
            ],
            "documentacao": "https://datajud-wiki.cnj.jus.br/api-publica/",
            "cadastro": "https://www.cnj.jus.br/sistemas/datajud/api-publica/"
        }
