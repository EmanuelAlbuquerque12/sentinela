"""
Serviço especializado para busca de acórdãos do TCU no DOU
Utiliza INLabs para download de PDFs e PyMuPDF para extração
"""
import asyncio
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.config import get_settings
from app.models.schemas import UnifiedResult, SourceType
from app.services.inlabs import INLabsService
from app.utils.pdf_helpers import (
    extrair_texto_pdf,
    encontrar_acordaos,
    resumir_acordao,
    gerar_docx
)
from app.utils.helpers import (
    generate_hash_id,
    extract_snippet_with_highlight,
    calculate_relevance_exact
)


class TCUAcordaosService:
    """
    Serviço especializado para busca de acórdãos do TCU no Diário Oficial da União

    Este serviço:
    1. Baixa o DOU em PDF via INLabs
    2. Extrai o texto completo do PDF
    3. Procura por acórdãos que contêm o termo de busca
    4. Retorna resultados normalizados
    5. Permite exportação para DOCX
    """

    def __init__(self):
        self.settings = get_settings()
        self.inlabs = INLabsService()
        self.timeout = 120

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        secao: str = "do1",  # DOU Seção 1 (onde são publicados acórdãos do TCU)
        size: int = 10,
        offset: int = 0,
        exact_match: bool = False,
        **kwargs
    ) -> List[UnifiedResult]:
        """
        Busca acórdãos do TCU no DOU

        Args:
            query: Termo de busca
            data_inicio: Data inicial
            data_fim: Data final
            secao: Seção do DOU (do1, do2, do3)
            size: Quantidade de resultados
            offset: Offset para paginação
            exact_match: Busca exata (não usado neste serviço)

        Returns:
            Lista de resultados normalizados
        """
        # Se não especificou datas, usar últimos 7 dias
        if not data_fim:
            data_fim = date.today()
        if not data_inicio:
            data_inicio = data_fim - timedelta(days=7)

        print(f"🔍 Buscando acórdãos do TCU: '{query}' ({data_inicio} a {data_fim})")

        all_acordaos = []
        current_date = data_inicio

        # Iterar sobre datas
        while current_date <= data_fim:
            # Baixar PDF do DOU
            try:
                pdf_content = await self.inlabs.download_dou_pdf(
                    data_publicacao=current_date,
                    secao=secao,
                    use_cache=True
                )

                if pdf_content:
                    # Extrair texto do PDF
                    texto = extrair_texto_pdf(pdf_content)

                    # Procurar acórdãos
                    acordaos_encontrados = encontrar_acordaos(texto, query)

                    if acordaos_encontrados:
                        print(f"✓ {len(acordaos_encontrados)} acórdão(s) encontrado(s) em {current_date}")

                        # Normalizar resultados
                        for ident, conteudo in acordaos_encontrados:
                            result = self._normalizar_acordao(
                                identificador=ident,
                                conteudo=conteudo,
                                data_publicacao=current_date,
                                query=query,
                                secao=secao
                            )
                            all_acordaos.append(result)

            except Exception as e:
                print(f"⚠️  Erro ao processar {current_date}: {e}")

            current_date += timedelta(days=1)

        print(f"📊 Total de acórdãos encontrados: {len(all_acordaos)}")

        # Ordenar por relevância
        all_acordaos.sort(key=lambda x: x.relevancia, reverse=True)

        # Aplicar paginação
        return all_acordaos[offset:offset + size]

    def _normalizar_acordao(
        self,
        identificador: str,
        conteudo: str,
        data_publicacao: date,
        query: str,
        secao: str
    ) -> UnifiedResult:
        """
        Normaliza um acórdão para o formato UnifiedResult

        Args:
            identificador: Identificação do acórdão (ex: "ACÓRDÃO Nº 1234/2025")
            conteudo: Texto completo do acórdão
            data_publicacao: Data de publicação no DOU
            query: Termo de busca
            secao: Seção do DOU

        Returns:
            Resultado normalizado
        """
        # Gerar snippet com destaque
        snippet = extract_snippet_with_highlight(
            text=conteudo,
            query=query,
            exact_match=False,
            max_length=500
        )

        # Calcular relevância
        relevancia = calculate_relevance_exact(
            query=query,
            text=conteudo,
            exact_match=False
        )

        # Gerar ID único
        result_id = generate_hash_id(
            "tcu_acordao",
            str(data_publicacao),
            identificador
        )

        # Extrair número do processo se disponível
        import re
        processos = []
        padrao_tc = re.compile(r"TC[\s-]*\d{2,6}\.\d{3}/\d{4}-\d")
        for m in padrao_tc.finditer(conteudo[:2000]):  # Primeiros 2000 chars
            proc = m.group(0)
            proc = re.sub(r"\s+", "", proc)
            proc = proc.replace("TC", "TC-").replace("--", "-")
            processos.append(proc)

        # Extrair relator se disponível
        relator = None
        padrao_relator = re.compile(r"Relator[:\s]+(.+?)(?:\n|Processo)", re.IGNORECASE)
        m_relator = padrao_relator.search(conteudo[:1000])
        if m_relator:
            relator = m_relator.group(1).strip()

        return UnifiedResult(
            id=result_id,
            termo_busca=query,
            fonte="TCU (Acórdãos DOU)",
            fonte_tipo=SourceType.TCU,
            orgao="Tribunal de Contas da União",
            orgao_uf=None,
            titulo=identificador,
            data_publicacao=data_publicacao,
            snippet=snippet,
            url_original=f"https://www.in.gov.br",
            relevancia=relevancia,
            metadados={
                "tipo": "acórdão",
                "secao_dou": secao,
                "processos": processos[:3] if processos else [],
                "relator": relator,
                "tamanho_texto": len(conteudo),
                "fonte_download": "INLabs PDF"
            }
        )

    async def exportar_acordaos_docx(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        output_dir: Path = None
    ) -> List[Path]:
        """
        Busca acórdãos e exporta para arquivos DOCX

        Args:
            query: Termo de busca
            data_inicio: Data inicial
            data_fim: Data final
            output_dir: Diretório de saída (padrão: /tmp/acordaos)

        Returns:
            Lista de caminhos dos arquivos gerados
        """
        if output_dir is None:
            output_dir = Path("/tmp/acordaos")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Buscar acórdãos
        if not data_fim:
            data_fim = date.today()
        if not data_inicio:
            data_inicio = data_fim - timedelta(days=7)

        print(f"📄 Exportando acórdãos para DOCX...")

        all_acordaos = []
        current_date = data_inicio

        while current_date <= data_fim:
            try:
                pdf_content = await self.inlabs.download_dou_pdf(
                    data_publicacao=current_date,
                    secao="do1",
                    use_cache=True
                )

                if pdf_content:
                    texto = extrair_texto_pdf(pdf_content)
                    acordaos_encontrados = encontrar_acordaos(texto, query)

                    for ident, conteudo in acordaos_encontrados:
                        all_acordaos.append((ident, conteudo))

            except Exception as e:
                print(f"⚠️  Erro ao processar {current_date}: {e}")

            current_date += timedelta(days=1)

        if not all_acordaos:
            print("Nenhum acórdão encontrado para exportar")
            return []

        # Gerar um único arquivo consolidado com quebras de página
        from unidecode import unidecode
        termo_limpo = re.sub(r"\s+", "_", unidecode(query).lower())
        data_hoje = date.today().strftime("%d-%m-%Y")
        filename = f"acordaos_{termo_limpo}_{data_hoje}.docx"
        docx_path = output_dir / filename

        # Gerar resumos
        blocos = []
        for ident, conteudo in all_acordaos:
            resumo = resumir_acordao(conteudo, ident)
            blocos.append("\n".join(resumo))

        # Juntar com quebras de página
        conteudo_doc = "\n<PAGE_BREAK>\n".join(blocos)

        # Gerar DOCX
        gerar_docx(conteudo_doc, docx_path)

        print(f"✓ Arquivo gerado: {docx_path}")
        print(f"  Total de acórdãos: {len(all_acordaos)}")

        return [docx_path]

    async def health_check(self) -> Dict[str, Any]:
        """Verifica disponibilidade do serviço"""
        # Verifica se INLabs está OK
        inlabs_health = await self.inlabs.health_check()

        if inlabs_health.get("status") == "online":
            return {
                "status": "online",
                "message": "Serviço de acórdãos TCU operacional",
                "inlabs_status": "online"
            }
        else:
            return {
                "status": "degraded",
                "message": "INLabs indisponível",
                "inlabs_status": inlabs_health.get("status")
            }

    def get_source_info(self) -> Dict[str, Any]:
        """Informações sobre a fonte"""
        return {
            "nome": "TCU Acórdãos (DOU PDF)",
            "tipo": "federal",
            "descricao": "Busca especializada de acórdãos do TCU no Diário Oficial da União",
            "cobertura": "Acórdãos do TCU publicados no DOU",
            "requer_autenticacao": True,
            "status": "operacional",
            "limitacoes": [
                "Requer credenciais INLabs",
                "Depende de download de PDFs (mais lento)",
                "Processamento de PDF pode ser intensivo"
            ],
            "vantagens": [
                "Busca específica por acórdãos do TCU",
                "Extração completa do texto",
                "Exportação para DOCX com resumos",
                "Identifica processos e responsáveis",
                "Cache de 72 horas para PDFs"
            ],
            "recursos": [
                "Extração de texto com PyMuPDF",
                "Identificação automática de acórdãos",
                "Resumo estruturado (processo, relator, decisão)",
                "Exportação consolidada em DOCX"
            ],
            "referencia": "Baseado em scripts fornecidos para extração de acórdãos"
        }
