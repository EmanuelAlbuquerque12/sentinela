"""
Serviço de integração com a API do Querido Diário (Open Knowledge Brasil)
"""
import httpx
from datetime import date
from typing import List, Optional, Dict, Any
from app.config import get_settings
from app.models.schemas import UnifiedResult
from app.utils.normalizer import DataNormalizer


class QueridoDiarioService:
    """
    Integração com a API pública do Querido Diário
    https://api.queridodiario.ok.org.br/docs
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.querido_diario_base_url
        self.timeout = self.settings.http_timeout
        self.normalizer = DataNormalizer()

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        territory_ids: Optional[List[str]] = None,
        ufs: Optional[List[str]] = None,
        size: int = 10,
        offset: int = 0,
        **kwargs  # Aceita parâmetros extras (ex: exact_match)
    ) -> List[UnifiedResult]:
        """
        Busca diários municipais no Querido Diário

        Args:
            query: Termo de busca
            data_inicio: Data inicial de publicação
            data_fim: Data final de publicação
            territory_ids: Códigos IBGE de municípios
            ufs: Filtro por UF
            size: Quantidade de resultados
            offset: Offset para paginação

        Returns:
            Lista de resultados normalizados
        """
        params = self._build_params(
            query=query,
            data_inicio=data_inicio,
            data_fim=data_fim,
            territory_ids=territory_ids,
            size=size,
            offset=offset
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/gazettes",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

            # Normalizar resultados
            gazettes = data.get("gazettes", [])
            results = []

            for gazette in gazettes:
                # Filtrar por UF se especificado
                if ufs and gazette.get("state_code") not in ufs:
                    continue

                try:
                    normalized = self.normalizer.normalize_querido_diario(
                        gazette,
                        query
                    )
                    results.append(normalized)
                except Exception as e:
                    # Log erro mas continua processando outros
                    print(f"Erro ao normalizar gazette: {e}")
                    continue

            return results

        except httpx.TimeoutException:
            raise Exception("Timeout ao consultar Querido Diário")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Erro HTTP do Querido Diário: {e.response.status_code}")
        except Exception as e:
            raise Exception(f"Erro ao consultar Querido Diário: {str(e)}")

    async def get_cities(
        self,
        city_name: Optional[str] = None,
        state_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista cidades disponíveis no Querido Diário

        Args:
            city_name: Nome da cidade (busca parcial)
            state_code: UF para filtrar

        Returns:
            Lista de cidades com territory_id e informações
        """
        params = {}
        if city_name:
            params["city_name"] = city_name
        if state_code:
            params["state_code"] = state_code.upper()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/cities",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

            return data.get("cities", [])

        except Exception as e:
            raise Exception(f"Erro ao buscar cidades: {str(e)}")

    async def get_city_by_id(self, territory_id: str) -> Dict[str, Any]:
        """
        Obtém informações detalhadas de uma cidade específica

        Args:
            territory_id: Código IBGE (7 dígitos)

        Returns:
            Informações da cidade
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/cities/{territory_id}"
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"Cidade {territory_id} não encontrada")
            raise Exception(f"Erro ao buscar cidade: {e.response.status_code}")
        except Exception as e:
            raise Exception(f"Erro ao buscar cidade: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde da API do Querido Diário

        Returns:
            Status e latência
        """
        try:
            import time
            start = time.time()

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()

            latency_ms = int((time.time() - start) * 1000)

            return {
                "status": "online",
                "latency_ms": latency_ms,
                "api_version": response.json().get("version", "unknown")
            }

        except Exception as e:
            return {
                "status": "offline",
                "erro": str(e)
            }

    def _build_params(
        self,
        query: str,
        data_inicio: Optional[date],
        data_fim: Optional[date],
        territory_ids: Optional[List[str]],
        size: int,
        offset: int
    ) -> Dict[str, Any]:
        """Constrói parâmetros da query"""
        params = {
            "querystring": query,
            "size": size,
            "offset": offset,
            "excerpt_size": 300,  # Tamanho dos snippets
            "sort_by": "descending_date"  # Mais recentes primeiro
        }

        if data_inicio:
            params["published_since"] = data_inicio.isoformat()

        if data_fim:
            params["published_until"] = data_fim.isoformat()

        if territory_ids:
            # Querido Diário aceita múltiplos territory_ids
            params["territory_ids"] = territory_ids

        return params

    def get_source_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a fonte"""
        return {
            "nome": "Querido Diário",
            "tipo": "municipal",
            "descricao": "Diários oficiais de 600+ municípios brasileiros",
            "cobertura": "~600 municípios (em expansão)",
            "requer_autenticacao": False,
            "status": "disponível",
            "limitacoes": [
                "Cobertura parcial de municípios",
                "Frequência de atualização varia por município",
                "Alguns diários podem ter OCR com erros"
            ],
            "documentacao": "https://api.queridodiario.ok.org.br/docs",
            "projeto": "https://queridodiario.ok.org.br"
        }
