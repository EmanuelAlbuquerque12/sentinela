"""
Serviço INLabs usando requests (síncrono) como no script original
Versão que FUNCIONA baseada no script fornecido pelo usuário
"""
import asyncio
import requests
from datetime import date, datetime
from typing import Optional
from pathlib import Path

from app.config import get_settings
from app.utils.helpers import cache_diario, get_cached_diario


class INLabsRequestsService:
    """
    Serviço INLabs usando biblioteca requests (como script original)

    Esta versão replica EXATAMENTE a lógica do script que funciona:
    - Usa requests ao invés de httpx
    - Login simples sem retry complexo
    - Mantém sessão com requests.Session()
    - Headers exatos do script original
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://inlabs.in.gov.br"
        self.username = self.settings.inlabs_username
        self.password = self.settings.inlabs_password
        self.session = None

    def _login_sync(self) -> Optional[str]:
        """
        Login síncrono EXATAMENTE como no script original

        Returns:
            Cookie de sessão ou None
        """
        if not self.username or not self.password:
            print("⚠️  Credenciais INLabs não configuradas")
            return None

        # URL exata do script original
        login_url = f"{self.base_url}/logar.php"

        try:
            # POST exatamente como no script original
            response = requests.post(
                login_url,
                data={
                    "email": self.username,
                    "password": self.password
                },
                headers={
                    "origem": "736372697074"  # Header especial do script
                },
                timeout=30
            )

            if response.status_code == 200:
                # Cookie exato como no script
                cookie = response.cookies.get("inlabs_session_cookie")
                if cookie:
                    print(f"✓ Login INLabs OK (requests)")
                    return cookie
                else:
                    print("❌ Cookie não encontrado na resposta")
                    return None
            else:
                print(f"❌ Login falhou: HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Erro no login: {e}")
            return None

    async def login_async(self) -> Optional[str]:
        """Wrapper async para login síncrono"""
        return await asyncio.to_thread(self._login_sync)

    def _download_pdf_sync(
        self,
        data_publicacao: date,
        secao: str = "do1",
        use_cache: bool = True
    ) -> Optional[bytes]:
        """
        Download síncrono EXATAMENTE como no script original

        Args:
            data_publicacao: Data da edição
            secao: Seção (do1, do2, do3)
            use_cache: Se usa cache

        Returns:
            Bytes do PDF ou None
        """
        # Checar cache primeiro
        if use_cache:
            cached = get_cached_diario(
                source=f"inlabs_requests_{secao}",
                data=datetime.combine(data_publicacao, datetime.min.time()),
                max_age_hours=72
            )
            if cached:
                print(f"✓ Cache: {data_publicacao} {secao}")
                content_b64 = cached.get("content")
                if content_b64:
                    import base64
                    return base64.b64decode(content_b64)

        # Login se necessário
        cookie = self._login_sync()
        if not cookie:
            print("❌ Login falhou, não pode baixar PDF")
            return None

        # Construir URL exatamente como no script original
        ano = data_publicacao.year
        mes = f"{data_publicacao.month:02d}"
        dia = f"{data_publicacao.day:02d}"
        data_str = f"{ano}-{mes}-{dia}"

        # Nome do arquivo como no script
        filename = f"{ano}_{mes}_{dia}_ASSINADO_{secao}.pdf"

        # URL exata do script original
        url = f"{self.base_url}/index.php?p={data_str}&dl={filename}"

        try:
            # GET com headers exatos do script
            response = requests.get(
                url,
                headers={
                    "Cookie": f"inlabs_session_cookie={cookie}",
                    "origem": "736372697074"
                },
                timeout=120
            )

            if response.status_code == 200:
                # Verificar se é PDF válido
                if len(response.content) > 1000 and response.content[:4] == b'%PDF':
                    print(f"✓ PDF baixado: {len(response.content)} bytes (requests)")

                    # Salvar em cache
                    if use_cache:
                        import base64
                        cache_diario(
                            source=f"inlabs_requests_{secao}",
                            data=datetime.combine(data_publicacao, datetime.min.time()),
                            content=base64.b64encode(response.content).decode('utf-8'),
                            metadata={"secao": secao, "filename": filename}
                        )

                    return response.content
                else:
                    print(f"⚠️  Resposta não é PDF válido")
                    return None
            elif response.status_code == 404:
                print(f"⚠️  PDF não encontrado: {filename}")
                return None
            else:
                print(f"❌ Erro HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Erro ao baixar PDF: {e}")
            return None

    async def download_dou_pdf(
        self,
        data_publicacao: date,
        secao: str = "do1",
        use_cache: bool = True
    ) -> Optional[bytes]:
        """Wrapper async para download síncrono"""
        return await asyncio.to_thread(
            self._download_pdf_sync,
            data_publicacao,
            secao,
            use_cache
        )
