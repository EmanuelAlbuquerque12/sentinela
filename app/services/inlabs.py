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
        secao: str = "1"
    ) -> Optional[str]:
        """
        Download do DOU em formato XML

        Args:
            data_publicacao: Data da edição
            secao: Seção do DOU (1, 2, 3, Extra)

        Returns:
            Conteúdo XML ou None
        """
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
                    return response.text
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
        offset: int = 0
    ) -> List[UnifiedResult]:
        """
        Busca no DOU usando INLabs

        Args:
            query: Termo de busca
            data_inicio: Data inicial
            data_fim: Data final
            secao: Seção do DOU (1, 2, 3)
            size: Quantidade de resultados
            offset: Offset para paginação

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

                # Download do XML da edição
                xml_content = await self.download_dou_xml(current_date, sec)

                if xml_content:
                    # Parsear XML e buscar termo
                    matches = self._search_in_xml(xml_content, query, current_date, sec)
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
        secao: str
    ) -> List[UnifiedResult]:
        """
        Busca termo no XML do DOU

        Args:
            xml_content: Conteúdo XML
            query: Termo de busca
            data_publicacao: Data da edição
            secao: Seção

        Returns:
            Lista de resultados encontrados
        """
        results = []
        query_lower = query.lower()

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
                texto_completo = f"{titulo_text} {conteudo_text}".lower()

                if query_lower in texto_completo:
                    # Criar resultado normalizado
                    result_data = {
                        "data_publicacao": data_publicacao.isoformat(),
                        "secao": secao,
                        "titulo": titulo_text,
                        "orgao": orgao_text,
                        "conteudo": conteudo_text,
                        "url_certificacao": f"https://www.in.gov.br/web/dou/-/{data_publicacao.strftime('%Y%m%d')}"
                    }

                    normalized = self.normalizer.normalize_dou(result_data, query)
                    results.append(normalized)

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
