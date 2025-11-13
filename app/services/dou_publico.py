"""
Serviço de download público do DOU
Acessa o portal público da Imprensa Nacional SEM autenticação
Fallback principal quando INLabs falha
"""
import httpx
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from app.utils.helpers import cache_diario, get_cached_diario


class DOUPublicoService:
    """
    Serviço para download público do DOU sem autenticação

    Usa o portal público da Imprensa Nacional:
    - https://www.in.gov.br/
    - Acesso direto aos PDFs publicados
    - Não requer login ou credenciais
    """

    def __init__(self):
        self.timeout = 60

    async def download_dou_pdf(
        self,
        data_publicacao: date,
        secao: str = "do1",
        use_cache: bool = True
    ) -> Optional[bytes]:
        """
        Baixa PDF do DOU do servidor público

        Args:
            data_publicacao: Data da edição
            secao: Seção (do1, do2, do3)
            use_cache: Se True, usa cache

        Returns:
            Conteúdo PDF em bytes ou None
        """
        # Tentar cache primeiro
        if use_cache:
            cached = get_cached_diario(
                source=f"dou_publico_{secao}",
                data=datetime.combine(data_publicacao, datetime.min.time()),
                max_age_hours=72
            )
            if cached:
                print(f"✓ Cache DOU público {data_publicacao} {secao}")
                content_b64 = cached.get("content")
                if content_b64:
                    import base64
                    return base64.b64decode(content_b64)

        # URLs públicas conhecidas do portal da Imprensa Nacional
        urls = self._build_public_urls(data_publicacao, secao)

        for url in urls:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=True
                ) as client:
                    response = await client.get(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "application/pdf,*/*"
                        }
                    )

                    if response.status_code == 200:
                        # Verificar se é PDF válido
                        if len(response.content) > 1000 and response.content[:4] == b'%PDF':
                            print(f"✓ DOU público baixado: {len(response.content)} bytes")

                            # Salvar em cache
                            if use_cache:
                                import base64
                                cache_diario(
                                    source=f"dou_publico_{secao}",
                                    data=datetime.combine(data_publicacao, datetime.min.time()),
                                    content=base64.b64encode(response.content).decode('utf-8'),
                                    metadata={"secao": secao, "fonte": "publico", "url": url}
                                )

                            return response.content

            except httpx.TimeoutException:
                print(f"⏱️  Timeout ao acessar {url}")
                continue
            except Exception as e:
                continue

        return None

    def _build_public_urls(self, data_pub: date, secao: str) -> list:
        """
        Constrói lista de URLs públicas para tentar

        Returns:
            Lista de URLs para tentar
        """
        ano = data_pub.year
        mes = f"{data_pub.month:02d}"
        dia = f"{data_pub.day:02d}"

        # Mapear secao
        secao_num = {
            "do1": "1",
            "do2": "2",
            "do3": "3",
            "do1e": "1e"
        }.get(secao, "1")

        # Data formatada para URLs
        data_slash = f"{dia}/{mes}/{ano}"
        data_dash = f"{ano}-{mes}-{dia}"
        data_compact = f"{ano}{mes}{dia}"

        urls = [
            # Formato 1: Portal principal com leiturajornal
            f"https://www.in.gov.br/leiturajornal?data={data_slash}&secao=dou{secao_num}",

            # Formato 2: Pesquisa JSP
            f"https://pesquisa.in.gov.br/imprensa/jsp/visualiza/index.jsp?data={data_slash}&jornal={secao_num}&pagina=1&totalArquivos=1",

            # Formato 3: Arquivo direto (padrão comum)
            f"https://www.in.gov.br/web/dou/-/arquivo-{secao_num}-{data_compact}",

            # Formato 4: Download direto
            f"https://www.in.gov.br/servicos/diario-oficial-da-uniao/download/{ano}/{mes}/{dia}/do{secao_num}.pdf",

            # Formato 5: URL antiga
            f"https://www.in.gov.br/content/diario-oficial/do{secao_num}-{data_dash}.pdf",
        ]

        return urls

    async def test_connection(self) -> bool:
        """
        Testa se consegue acessar o portal público

        Returns:
            True se portal está acessível
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get("https://www.in.gov.br")
                return response.status_code == 200
        except:
            return False
