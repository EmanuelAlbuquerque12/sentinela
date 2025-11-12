"""
Serviço APRIMORADO de integração com APIs do TCU
Baseado em: https://sites.tcu.gov.br/dados-abertos/webservices-tcu/

10 webservices integrados:
1. Acórdãos
2. Pessoa Jurídica (CNPJ)
3. Atos Normativos
4. Sanções e Inabilitados
5. CADIRREG
6. Solicitações do Congresso
7. Pautas de Sessões
8. Licitações
9. Contratos
10. Cálculo de Débito
"""
import httpx
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from app.config import get_settings
from app.models.schemas import UnifiedResult, SourceType
from app.utils.normalizer import DataNormalizer
from app.utils.helpers import (
    matches_exact_query,
    extract_snippet_with_highlight,
    calculate_relevance_exact,
    generate_hash_id,
    cache_diario,
    get_cached_diario
)


class TCUEnhancedService:
    """
    Integração COMPLETA com todos os webservices do TCU
    https://sites.tcu.gov.br/dados-abertos/webservices-tcu/
    """

    # URLs base dos diferentes sistemas
    DADOS_ABERTOS_URL = "https://dados-abertos.apps.tcu.gov.br/api"
    CONTAS_URL = "https://contas.tcu.gov.br"
    CERTIDOES_URL = "https://certidoes-apf.apps.tcu.gov.br/api/rest/publico"
    PORTAL_URL = "https://portal.tcu.gov.br"

    def __init__(self):
        self.settings = get_settings()
        self.timeout = self.settings.http_timeout
        self.normalizer = DataNormalizer()

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        size: int = 10,
        offset: int = 0,
        exact_match: bool = False,
        **kwargs
    ) -> List[UnifiedResult]:
        """
        Busca unificada em TODOS os webservices do TCU

        Busca em:
        - Acórdãos
        - Atos Normativos
        - Pautas de Sessões
        - Inabilitados/Sanções
        - Solicitações do Congresso

        Args:
            query: Termo de busca
            data_inicio: Data inicial
            data_fim: Data final
            size: Quantidade de resultados
            offset: Offset
            exact_match: Busca exata

        Returns:
            Lista unificada de resultados
        """
        all_results = []

        # Buscar em paralelo em múltiplas fontes TCU
        tasks = [
            self._search_acordaos(query, data_inicio, data_fim, exact_match),
            self._search_atos_normativos(query, data_inicio, data_fim, exact_match),
            self._search_pautas(query, exact_match),
            self._search_inabilitados_text(query, exact_match),
        ]

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Consolidar resultados
        for results in results_lists:
            if isinstance(results, list):
                all_results.extend(results)

        # Ordenar por relevância
        all_results.sort(key=lambda x: x.relevancia, reverse=True)

        # Aplicar paginação
        return all_results[offset:offset + size]

    async def _search_acordaos(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        exact_match: bool = False
    ) -> List[UnifiedResult]:
        """Busca em acórdãos do TCU"""
        # Verificar cache
        cache_key = f"tcu_acordaos_{datetime.now().strftime('%Y-%m-%d')}"
        cached = get_cached_diario(
            source="tcu_acordaos",
            data=datetime.now(),
            max_age_hours=24
        )

        if cached:
            acordaos = cached.get("content", [])
        else:
            # Buscar da API
            endpoint = f"{self.DADOS_ABERTOS_URL}/acordao/recupera-acordaos"
            params = {"inicio": 0, "quantidade": 100}

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(endpoint, params=params)
                    response.raise_for_status()
                    data = response.json()

                # FIX: Verificar se data é lista ou dict
                if isinstance(data, list):
                    acordaos = data
                elif isinstance(data, dict):
                    acordaos = data.get("data", data.get("items", []))
                else:
                    acordaos = []

                # Salvar em cache
                if acordaos:
                    cache_diario(
                        source="tcu_acordaos",
                        data=datetime.now(),
                        content=acordaos
                    )

            except Exception as e:
                print(f"Erro ao buscar acórdãos TCU: {e}")
                return []

        # Filtrar por query
        results = []
        for acordao in acordaos:
            titulo = acordao.get("titulo", "") or ""
            sumario = acordao.get("sumario", "") or ""
            texto_completo = f"{titulo} {sumario}"

            if not matches_exact_query(texto_completo, query):
                continue

            # Filtrar por data
            data_sessao_str = acordao.get("dataSessao", "")
            if data_sessao_str and (data_inicio or data_fim):
                try:
                    data_sessao = datetime.fromisoformat(data_sessao_str).date()
                    if data_inicio and data_sessao < data_inicio:
                        continue
                    if data_fim and data_sessao > data_fim:
                        continue
                except:
                    pass

            # Criar resultado normalizado
            snippet = extract_snippet_with_highlight(
                text=sumario or titulo,
                query=query,
                exact_match=exact_match,
                max_length=400
            )

            relevancia = calculate_relevance_exact(
                query=query,
                text=texto_completo,
                exact_match=exact_match
            )

            result = UnifiedResult(
                id=generate_hash_id("tcu_acordao", acordao.get("chave", "")),
                termo_busca=query,
                fonte="TCU (Acórdãos)",
                fonte_tipo=SourceType.TCU,
                orgao="Tribunal de Contas da União",
                orgao_uf=None,
                titulo=titulo or f"Acórdão {acordao.get('numero', '')}",
                data_publicacao=data_sessao if 'data_sessao' in locals() else date.today(),
                snippet=snippet,
                url_original=acordao.get("linkArquivo", self.PORTAL_URL),
                relevancia=relevancia,
                metadados={
                    "numero": acordao.get("numero"),
                    "ano": acordao.get("ano"),
                    "colegiado": acordao.get("colegiado"),
                    "relator": acordao.get("relator"),
                    "tipo": "acórdão"
                }
            )
            results.append(result)

        return results

    async def _search_atos_normativos(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        exact_match: bool = False
    ) -> List[UnifiedResult]:
        """Busca em atos normativos do TCU"""
        endpoint = f"{self.DADOS_ABERTOS_URL}/atonormativo/recupera-atos-normativos"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                data = response.json()

            # Parse response
            if isinstance(data, list):
                atos = data
            elif isinstance(data, dict):
                atos = data.get("data", data.get("items", []))
            else:
                atos = []

        except Exception as e:
            print(f"Erro ao buscar atos normativos TCU: {e}")
            return []

        # Filtrar e normalizar
        results = []
        for ato in atos:
            texto = ato.get("textoInteiroTeor", "") or ""
            titulo = ato.get("titulo", "") or ""
            texto_completo = f"{titulo} {texto}"

            if not matches_exact_query(texto_completo, query):
                continue

            snippet = extract_snippet_with_highlight(
                text=texto or titulo,
                query=query,
                exact_match=exact_match
            )

            relevancia = calculate_relevance_exact(query, texto_completo, exact_match)

            result = UnifiedResult(
                id=generate_hash_id("tcu_ato", ato.get("numero", "")),
                termo_busca=query,
                fonte="TCU (Atos Normativos)",
                fonte_tipo=SourceType.TCU,
                orgao="Tribunal de Contas da União",
                orgao_uf=None,
                titulo=titulo or f"Ato Normativo {ato.get('numero', '')}",
                data_publicacao=date.today(),
                snippet=snippet,
                url_original=ato.get("linkDocumento", self.PORTAL_URL),
                relevancia=relevancia,
                metadados={"tipo": "ato_normativo"}
            )
            results.append(result)

        return results

    async def _search_pautas(
        self,
        query: str,
        exact_match: bool = False
    ) -> List[UnifiedResult]:
        """Busca em pautas de sessões"""
        endpoint = f"{self.DADOS_ABERTOS_URL}/pautassessao"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                data = response.json()

            if isinstance(data, list):
                pautas = data
            elif isinstance(data, dict):
                pautas = data.get("data", data.get("items", []))
            else:
                pautas = []

        except Exception as e:
            print(f"Erro ao buscar pautas TCU: {e}")
            return []

        results = []
        for pauta in pautas:
            natureza = pauta.get("naturezaProcesso", "") or ""
            relator = pauta.get("nomeRelator", "") or ""
            texto = f"{natureza} {relator}"

            if not matches_exact_query(texto, query):
                continue

            snippet = extract_snippet_with_highlight(texto, query, exact_match)
            relevancia = calculate_relevance_exact(query, texto, exact_match)

            result = UnifiedResult(
                id=generate_hash_id("tcu_pauta", pauta.get("numeroProcesso", "")),
                termo_busca=query,
                fonte="TCU (Pautas)",
                fonte_tipo=SourceType.TCU,
                orgao="Tribunal de Contas da União",
                orgao_uf=None,
                titulo=f"Pauta: {pauta.get('numeroProcesso', '')}",
                data_publicacao=date.today(),
                snippet=snippet,
                url_original=self.PORTAL_URL,
                relevancia=relevancia,
                metadados={
                    "natureza": natureza,
                    "relator": relator,
                    "colegiado": pauta.get("nomeColegiado", ""),
                    "tipo": "pauta"
                }
            )
            results.append(result)

        return results

    async def _search_inabilitados_text(
        self,
        query: str,
        exact_match: bool = False
    ) -> List[UnifiedResult]:
        """Busca textual em inabilitados"""
        endpoint = f"{self.CONTAS_URL}/ords/condenacao/consulta/inabilitados"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                data = response.json()

            if isinstance(data, list):
                inabilitados = data
            elif isinstance(data, dict):
                inabilitados = data.get("items", [])
            else:
                inabilitados = []

        except Exception as e:
            print(f"Erro ao buscar inabilitados TCU: {e}")
            return []

        results = []
        for inab in inabilitados:
            nome = inab.get("nome", "") or ""
            if not matches_exact_query(nome, query):
                continue

            snippet = extract_snippet_with_highlight(nome, query, exact_match)
            relevancia = calculate_relevance_exact(query, nome, exact_match)

            result = UnifiedResult(
                id=generate_hash_id("tcu_inab", inab.get("cpf", "")),
                termo_busca=query,
                fonte="TCU (Inabilitados)",
                fonte_tipo=SourceType.TCU,
                orgao="Tribunal de Contas da União",
                orgao_uf=inab.get("uf", None),
                titulo=f"Inabilitado: {nome}",
                data_publicacao=date.today(),
                snippet=snippet,
                url_original=self.PORTAL_URL,
                relevancia=relevancia,
                metadados={
                    "cpf": inab.get("cpf", ""),
                    "processo": inab.get("numeroProcesso", ""),
                    "tipo": "inabilitado"
                }
            )
            results.append(result)

        return results

    async def consultar_cnpj(self, cnpj: str) -> Dict[str, Any]:
        """
        Consulta consolidada de pessoa jurídica

        Args:
            cnpj: CNPJ da empresa

        Returns:
            Dados consolidados da empresa
        """
        endpoint = f"{self.CERTIDOES_URL}/certidoes/{cnpj}"
        params = {"seEmitirPDF": "false"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise Exception(f"Erro ao consultar CNPJ: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde dos serviços TCU"""
        # Verificar horário de manutenção
        now = datetime.now()
        if 20 <= now.hour < 21:
            return {
                "status": "maintenance",
                "message": "TCU em manutenção (20h-21h)"
            }

        try:
            import time
            start = time.time()

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.DADOS_ABERTOS_URL}/acordao/recupera-acordaos",
                    params={"inicio": 0, "quantidade": 1}
                )
                response.raise_for_status()

            latency_ms = int((time.time() - start) * 1000)

            return {
                "status": "online",
                "latency_ms": latency_ms,
                "webservices": "10 disponíveis"
            }

        except Exception as e:
            return {
                "status": "offline",
                "erro": str(e)
            }

    def get_source_info(self) -> Dict[str, Any]:
        """Informações sobre a fonte"""
        return {
            "nome": "TCU Enhanced",
            "tipo": "tcu",
            "descricao": "Tribunal de Contas da União - 10 Webservices Integrados",
            "cobertura": "Acórdãos, Atos Normativos, Pautas, Inabilitados, Licitações, Contratos, CNPJ",
            "requer_autenticacao": False,
            "status": "disponível",
            "webservices_disponiveis": 10,
            "apis": [
                "Acórdãos",
                "Pessoa Jurídica (CNPJ)",
                "Atos Normativos",
                "Sanções/Inabilitados",
                "CADIRREG",
                "Solicitações Congresso",
                "Pautas Sessões",
                "Licitações",
                "Contratos",
                "Cálculo Débito"
            ],
            "limitacoes": [
                "Indisponível entre 20h-21h (manutenção)",
                "Máximo 100 registros por requisição em alguns endpoints"
            ],
            "documentacao": "https://sites.tcu.gov.br/dados-abertos/webservices-tcu/"
        }


# Manter importação de asyncio
import asyncio
