"""
Serviço de integração com a API de Dados Abertos do TCU
"""
import httpx
from datetime import date
from typing import List, Optional, Dict, Any
from app.config import get_settings
from app.models.schemas import UnifiedResult
from app.utils.normalizer import DataNormalizer


class TCUService:
    """
    Integração com a API de Dados Abertos do TCU
    https://portal.tcu.gov.br/dados-abertos/
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.tcu_base_url
        self.timeout = self.settings.http_timeout
        self.normalizer = DataNormalizer()

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        size: int = 10,
        offset: int = 0
    ) -> List[UnifiedResult]:
        """
        Busca acórdãos do TCU

        Args:
            query: Termo de busca
            data_inicio: Data inicial da sessão
            data_fim: Data final da sessão
            size: Quantidade de resultados
            offset: Offset para paginação

        Returns:
            Lista de resultados normalizados
        """
        try:
            # Buscar acórdãos
            acordaos = await self._fetch_acordaos(
                inicio=offset,
                quantidade=min(size * 3, 100)  # Buscar mais para filtrar depois
            )

            # Filtrar por termo de busca e datas
            filtered_results = []

            for acordao in acordaos:
                # Verificar se o termo aparece no sumário ou título
                sumario = (acordao.get("sumario", "") or "").lower()
                titulo = (acordao.get("titulo", "") or "").lower()
                query_lower = query.lower()

                if query_lower not in sumario and query_lower not in titulo:
                    continue

                # Filtrar por data se especificado
                data_sessao_str = acordao.get("dataSessao", "")
                if data_sessao_str and (data_inicio or data_fim):
                    try:
                        from datetime import datetime
                        data_sessao = datetime.fromisoformat(data_sessao_str).date()

                        if data_inicio and data_sessao < data_inicio:
                            continue
                        if data_fim and data_sessao > data_fim:
                            continue
                    except:
                        # Se erro ao parsear data, incluir mesmo assim
                        pass

                # Normalizar resultado
                try:
                    normalized = self.normalizer.normalize_tcu(acordao, query)
                    filtered_results.append(normalized)

                    if len(filtered_results) >= size:
                        break
                except Exception as e:
                    print(f"Erro ao normalizar acórdão: {e}")
                    continue

            return filtered_results[:size]

        except Exception as e:
            raise Exception(f"Erro ao buscar no TCU: {str(e)}")

    async def _fetch_acordaos(
        self,
        inicio: int = 0,
        quantidade: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca acórdãos na API do TCU

        Args:
            inicio: Índice inicial (paginação)
            quantidade: Quantidade de registros

        Returns:
            Lista de acórdãos
        """
        endpoint = f"{self.base_url}/acordao/recupera-acordaos"
        params = {
            "inicio": inicio,
            "quantidade": min(quantidade, 100)  # Máximo 100
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()

            return data.get("data", [])

        except httpx.TimeoutException:
            raise Exception("Timeout ao consultar TCU")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Erro HTTP {e.response.status_code} do TCU")
        except Exception as e:
            raise Exception(f"Erro ao buscar acórdãos: {str(e)}")

    async def get_inabilitados(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de pessoas inabilitadas para cargos públicos

        Returns:
            Lista de inabilitados
        """
        endpoint = f"{self.base_url}/inabilitados"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                data = response.json()

            return data.get("data", [])

        except Exception as e:
            raise Exception(f"Erro ao buscar inabilitados: {str(e)}")

    async def search_inabilitados(
        self,
        nome: Optional[str] = None,
        cpf: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca inabilitados por nome ou CPF

        Args:
            nome: Nome para buscar (busca parcial)
            cpf: CPF para buscar

        Returns:
            Lista de inabilitados encontrados
        """
        try:
            inabilitados = await self.get_inabilitados()

            if not nome and not cpf:
                return inabilitados

            filtered = []
            for inab in inabilitados:
                match = True

                if nome:
                    nome_inab = (inab.get("nome", "") or "").lower()
                    if nome.lower() not in nome_inab:
                        match = False

                if cpf:
                    cpf_inab = inab.get("cpf", "")
                    # Remover formatação do CPF para comparar
                    cpf_clean = cpf.replace(".", "").replace("-", "")
                    cpf_inab_clean = cpf_inab.replace(".", "").replace("-", "").replace("*", "")

                    if cpf_clean not in cpf_inab_clean:
                        match = False

                if match:
                    filtered.append(inab)

            return filtered

        except Exception as e:
            raise Exception(f"Erro ao buscar inabilitados: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde da API do TCU

        Nota: TCU fica indisponível entre 20h-21h para manutenção
        """
        try:
            import time
            from datetime import datetime

            # Verificar se está no horário de manutenção (20h-21h)
            now = datetime.now()
            if 20 <= now.hour < 21:
                return {
                    "status": "maintenance",
                    "message": "TCU em manutenção (20h-21h)"
                }

            start = time.time()

            # Testar endpoint de acórdãos
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/acordao/recupera-acordaos",
                    params={"inicio": 0, "quantidade": 1}
                )
                response.raise_for_status()

            latency_ms = int((time.time() - start) * 1000)

            return {
                "status": "online",
                "latency_ms": latency_ms
            }

        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "erro": "Timeout ao conectar"
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "erro": f"HTTP {e.response.status_code}"
            }
        except Exception as e:
            return {
                "status": "offline",
                "erro": str(e)
            }

    def get_source_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a fonte"""
        return {
            "nome": "TCU",
            "tipo": "tcu",
            "descricao": "Tribunal de Contas da União - Acórdãos e Deliberações",
            "cobertura": "Acórdãos, deliberações e inabilitados do TCU",
            "requer_autenticacao": False,
            "status": "disponível",
            "limitacoes": [
                "Indisponível entre 20h-21h (manutenção diária)",
                "Foco em acórdãos (não cobre todo o BTCU)",
                "Busca textual limitada (filtro client-side)",
                "Máximo 100 registros por requisição"
            ],
            "documentacao": "https://portal.tcu.gov.br/dados-abertos/",
            "webservices": "https://portal.tcu.gov.br/webservices-tcu/"
        }
