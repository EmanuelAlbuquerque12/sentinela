"""
Serviço de integração com INLabs (Imprensa Nacional)
Portal para download do Diário Oficial da União em XML e PDF
"""
import httpx
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from app.config import get_settings
from app.models.schemas import UnifiedResult
from app.utils.normalizer import DataNormalizer
from app.utils.helpers import (
    cache_diario,
    get_cached_diario,
    matches_exact_query,
    extract_snippet_with_highlight,
    calculate_relevance_exact
)
import xml.etree.ElementTree as ET


class INLabsService:
    """
    Integração com INLabs - Portal da Imprensa Nacional
    https://inlabs.in.gov.br

    Permite download de edições completas do DOU em XML e PDF
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://inlabs.in.gov.br"
        self.timeout = self.settings.http_timeout
        self.normalizer = DataNormalizer()

        # Credenciais do INLabs
        self.username = self.settings.inlabs_username
        self.password = self.settings.inlabs_password

        self.session = None

    async def login(self) -> bool:
        """
        Realiza login no portal INLabs

        Returns:
            True se login bem-sucedido
        """
        if not self.username or not self.password:
            raise Exception("Credenciais INLabs não configuradas")

        login_url = f"{self.base_url}/api/auth/login"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    login_url,
                    json={
                        "email": self.username,
                        "password": self.password
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    # Armazenar token de sessão
                    self.session = data.get("token")
                    return True
                else:
                    raise Exception(f"Falha no login: {response.status_code}")

        except Exception as e:
            raise Exception(f"Erro ao fazer login no INLabs: {str(e)}")

    async def download_dou_xml(
        self,
        data_publicacao: date,
        secao: str = "1",
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Download do DOU em formato XML com suporte a cache

        Args:
            data_publicacao: Data da edição
            secao: Seção do DOU (1, 2, 3, Extra)
            use_cache: Se True, tenta usar cache antes de baixar

        Returns:
            Conteúdo XML ou None
        """
        # Tentar cache primeiro
        if use_cache:
            cached = get_cached_diario(
                source=f"inlabs_secao_{secao}",
                data=datetime.combine(data_publicacao, datetime.min.time()),
                max_age_hours=72  # Cache válido por 3 dias
            )
            if cached:
                print(f"✓ Usando cache para DOU {data_publicacao} seção {secao}")
                return cached.get("content")

        if not self.session:
            await self.login()

        # Formato da URL: /download/xml/{ano}/{mes}/{dia}/secao-{secao}.xml
        ano = data_publicacao.year
        mes = f"{data_publicacao.month:02d}"
        dia = f"{data_publicacao.day:02d}"

        xml_url = f"{self.base_url}/download/xml/{ano}/{mes}/{dia}/secao-{secao}.xml"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(
                    xml_url,
                    headers={"Authorization": f"Bearer {self.session}"}
                )

                if response.status_code == 200:
                    xml_content = response.text

                    # Salvar em cache
                    if use_cache:
                        cache_diario(
                            source=f"inlabs_secao_{secao}",
                            data=datetime.combine(data_publicacao, datetime.min.time()),
                            content=xml_content,
                            metadata={"secao": secao}
                        )
                        print(f"✓ Cache salvo para DOU {data_publicacao} seção {secao}")

                    return xml_content

                elif response.status_code == 404:
                    return None  # Edição não disponível
                else:
                    raise Exception(f"Erro ao baixar XML: {response.status_code}")

        except Exception as e:
            print(f"Erro ao baixar DOU XML: {e}")
            return None

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        secao: Optional[str] = None,
        size: int = 10,
        offset: int = 0,
        exact_match: bool = False,
        **kwargs
    ) -> List[UnifiedResult]:
        """
        Busca no DOU usando INLabs com cache

        Args:
            query: Termo de busca
            data_inicio: Data inicial
            data_fim: Data final
            secao: Seção do DOU (1, 2, 3)
            size: Quantidade de resultados
            offset: Offset para paginação
            exact_match: Se True, busca apenas matches exatos

        Returns:
            Lista de resultados normalizados
        """
        # Garantir login
        if not self.session:
            await self.login()

        # Se não especificou datas, buscar últimos 7 dias
        if not data_fim:
            data_fim = date.today()
        if not data_inicio:
            from datetime import timedelta
            data_inicio = data_fim - timedelta(days=7)

        results = []

        # Buscar em cada dia do período
        current_date = data_inicio
        while current_date <= data_fim and len(results) < size:
            # Buscar em cada seção se não especificado
            secoes = [secao] if secao else ["1", "2", "3"]

            for sec in secoes:
                if len(results) >= size:
                    break

                # Download do XML da edição (com cache)
                xml_content = await self.download_dou_xml(current_date, sec, use_cache=True)

                if xml_content:
                    # Parsear XML e buscar termo
                    matches = self._search_in_xml(
                        xml_content,
                        query,
                        current_date,
                        sec,
                        exact_match=exact_match
                    )
                    results.extend(matches)

            # Próximo dia
            from datetime import timedelta
            current_date += timedelta(days=1)

        # Aplicar paginação
        return results[offset:offset + size]

    def _search_in_xml(
        self,
        xml_content: str,
        query: str,
        data_publicacao: date,
        secao: str,
        exact_match: bool = False
    ) -> List[UnifiedResult]:
        """
        Busca termo no XML do DOU com suporte a busca exata

        Args:
            xml_content: Conteúdo XML
            query: Termo de busca
            data_publicacao: Data da edição
            secao: Seção
            exact_match: Se True, apenas matches exatos

        Returns:
            Lista de resultados encontrados
        """
        results = []

        try:
            # Parsear XML
            root = ET.fromstring(xml_content)

            # Iterar sobre artigos/matérias
            for artigo in root.findall(".//artigo"):
                # Extrair dados
                titulo = artigo.find("titulo")
                conteudo = artigo.find("texto")
                orgao = artigo.find("orgao")

                titulo_text = titulo.text if titulo is not None else ""
                conteudo_text = conteudo.text if conteudo is not None else ""
                orgao_text = orgao.text if orgao is not None else "Órgão Federal"

                # Verificar se termo está presente
                texto_completo = f"{titulo_text} {conteudo_text}"

                # Verificar match (exato ou flexível)
                if exact_match:
                    if not matches_exact_query(texto_completo, query):
                        continue  # Pular se não há match exato
                else:
                    if not matches_exact_query(texto_completo, query):
                        continue  # Mesmo busca flexível precisa ter o termo

                # Extrair snippet com destaque
                snippet = extract_snippet_with_highlight(
                    text=conteudo_text or titulo_text,
                    query=query,
                    exact_match=exact_match,
                    max_length=400,
                    context_chars=200
                )

                # Calcular relevância
                relevancia = calculate_relevance_exact(
                    query=query,
                    text=texto_completo,
                    exact_match=exact_match
                )

                # Criar resultado normalizado
                from app.utils.helpers import generate_hash_id
                result_id = generate_hash_id("inlabs", data_publicacao.isoformat(), secao, titulo_text[:50])

                result = UnifiedResult(
                    id=result_id,
                    termo_busca=query,
                    fonte="INLabs/DOU",
                    fonte_tipo="federal",
                    orgao=orgao_text,
                    orgao_uf=None,
                    titulo=titulo_text or "Publicação DOU",
                    data_publicacao=data_publicacao,
                    snippet=snippet,
                    url_original=f"https://www.in.gov.br/web/dou/-/{data_publicacao.strftime('%Y%m%d')}",
                    relevancia=relevancia,
                    metadados={
                        "secao": secao,
                        "data_download": datetime.now().isoformat(),
                        "exact_match": exact_match
                    }
                )

                results.append(result)

        except ET.ParseError as e:
            print(f"Erro ao parsear XML: {e}")
        except Exception as e:
            print(f"Erro ao processar XML: {e}")

        return results

    async def get_available_editions(
        self,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict[str, Any]]:
        """
        Lista edições disponíveis no período

        Args:
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Lista de edições disponíveis
        """
        if not self.session:
            await self.login()

        editions = []
        current_date = data_inicio

        while current_date <= data_fim:
            for secao in ["1", "2", "3"]:
                # Verificar se edição existe
                xml = await self.download_dou_xml(current_date, secao)

                if xml:
                    editions.append({
                        "data": current_date.isoformat(),
                        "secao": secao,
                        "disponivel": True
                    })

            from datetime import timedelta
            current_date += timedelta(days=1)

        return editions

    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde do serviço INLabs

        Returns:
            Status e informações
        """
        try:
            import time
            start = time.time()

            # Testar login
            success = await self.login()

            latency_ms = int((time.time() - start) * 1000)

            if success:
                return {
                    "status": "online",
                    "latency_ms": latency_ms,
                    "authenticated": True
                }
            else:
                return {
                    "status": "offline",
                    "erro": "Falha na autenticação"
                }

        except Exception as e:
            return {
                "status": "offline",
                "erro": str(e)
            }

    def get_source_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a fonte"""
        return {
            "nome": "INLabs/DOU",
            "tipo": "federal",
            "descricao": "Portal INLabs - Download completo do DOU em XML/PDF",
            "cobertura": "Todas as seções do DOU (desde 2020)",
            "requer_autenticacao": True,
            "status": "disponível" if self.username and self.password else "não configurado",
            "limitacoes": [
                "Requer cadastro no portal INLabs",
                "Download de edições completas (não busca textual nativa)",
                "Processamento local do XML necessário"
            ],
            "vantagens": [
                "Acesso a edições completas desde 2020",
                "Formato XML estruturado",
                "Download de PDFs originais",
                "Sem limitação de consultas"
            ],
            "portal": "https://inlabs.in.gov.br",
            "github": "https://github.com/Imprensa-Nacional/inlabs"
        }
