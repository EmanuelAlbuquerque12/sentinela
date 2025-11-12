"""
Serviço de integração com dados do Diário Oficial da União (DOU)
Implementa busca offline: download PDF → cache → extração → busca
"""
import asyncio
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
import re
from app.config import get_settings
from app.models.schemas import UnifiedResult, SourceType
from app.services.inlabs import INLabsService
from app.utils.pdf_helpers import extrair_texto_pdf
from app.utils.helpers import (
    generate_hash_id,
    extract_snippet_with_highlight,
    calculate_relevance_exact,
    matches_exact_query
)


class DOUService:
    """
    Integração com DOU usando abordagem offline:
    1. Baixa PDF do DOU via INLabs
    2. Armazena em cache no diretório temporário
    3. Extrai texto do PDF usando PyMuPDF
    4. Realiza busca no texto extraído

    Esta abordagem garante estabilidade e independência da conexão.
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
        secao: Optional[str] = None,
        size: int = 10,
        offset: int = 0,
        exact_match: bool = False,
        **kwargs
    ) -> List[UnifiedResult]:
        """
        Busca no DOU usando abordagem offline (download → cache → busca)

        Args:
            query: Termo de busca
            data_inicio: Data inicial de publicação
            data_fim: Data final de publicação
            secao: Seção do DOU (None = todas, ou "do1", "do2", "do3")
            size: Quantidade de resultados
            offset: Offset para paginação
            exact_match: Se True, busca apenas matches exatos

        Returns:
            Lista de resultados normalizados
        """
        # Se não especificou datas, usar últimos 7 dias
        if not data_fim:
            data_fim = date.today()
        if not data_inicio:
            data_inicio = data_fim - timedelta(days=7)

        print(f"🔍 Buscando no DOU: '{query}' ({data_inicio} a {data_fim})")
        print(f"   Abordagem: Download PDF → Cache → Busca Offline")

        all_results = []
        current_date = data_inicio

        # Definir seções a buscar
        secoes = []
        if secao:
            secoes = [secao]
        else:
            secoes = ["do1", "do2", "do3"]  # Todas as seções

        # Iterar sobre datas e seções
        while current_date <= data_fim:
            for sec in secoes:
                try:
                    # PASSO 1: Baixar PDF (com cache automático)
                    pdf_content = await self.inlabs.download_dou_pdf(
                        data_publicacao=current_date,
                        secao=sec,
                        use_cache=True  # Cache de 72 horas
                    )

                    if not pdf_content:
                        continue

                    # PASSO 2: Extrair texto do PDF
                    texto_completo = extrair_texto_pdf(pdf_content)

                    if not texto_completo:
                        print(f"⚠️  PDF vazio ou não legível: {current_date} {sec}")
                        continue

                    # PASSO 3: Buscar termo no texto
                    resultados_encontrados = self._buscar_no_texto(
                        texto=texto_completo,
                        query=query,
                        data_publicacao=current_date,
                        secao=sec,
                        exact_match=exact_match
                    )

                    if resultados_encontrados:
                        print(f"✓ {len(resultados_encontrados)} resultado(s) em {current_date} {sec}")
                        all_results.extend(resultados_encontrados)

                except Exception as e:
                    print(f"⚠️  Erro ao processar {current_date} {sec}: {e}")

            current_date += timedelta(days=1)

        print(f"📊 Total de resultados DOU: {len(all_results)}")

        # Ordenar por relevância
        all_results.sort(key=lambda x: x.relevancia, reverse=True)

        # Aplicar paginação
        return all_results[offset:offset + size]

    def _buscar_no_texto(
        self,
        texto: str,
        query: str,
        data_publicacao: date,
        secao: str,
        exact_match: bool = False
    ) -> List[UnifiedResult]:
        """
        Busca o termo no texto extraído do PDF

        Args:
            texto: Texto completo extraído do PDF
            query: Termo de busca
            data_publicacao: Data de publicação
            secao: Seção do DOU
            exact_match: Se True, busca apenas matches exatos

        Returns:
            Lista de resultados encontrados
        """
        results = []

        # Verificar se tem o termo
        if not matches_exact_query(texto, query):
            return results

        # Dividir texto em artigos/matérias (separados por linhas em branco duplas)
        # Isso ajuda a criar resultados individuais ao invés de um único resultado gigante
        blocos = re.split(r'\n\s*\n\s*\n', texto)
        blocos = [b.strip() for b in blocos if b.strip() and len(b.strip()) > 100]

        # Se não conseguiu dividir bem, usar o texto todo como um bloco
        if len(blocos) == 0:
            blocos = [texto]

        # Buscar em cada bloco
        for idx, bloco in enumerate(blocos):
            # Verificar se bloco contém o termo
            if not matches_exact_query(bloco, query):
                continue

            # Extrair título (primeira linha do bloco, até 200 chars)
            linhas = bloco.split('\n')
            titulo = linhas[0][:200] if linhas else "Publicação DOU"

            # Limpar título
            titulo = titulo.strip()
            if not titulo:
                titulo = "Publicação DOU"

            # Extrair snippet com destaque
            snippet = extract_snippet_with_highlight(
                text=bloco,
                query=query,
                exact_match=exact_match,
                max_length=500
            )

            # Calcular relevância
            relevancia = calculate_relevance_exact(
                query=query,
                text=bloco,
                exact_match=exact_match
            )

            # Gerar ID único
            result_id = generate_hash_id(
                "dou",
                str(data_publicacao),
                secao,
                str(idx)
            )

            # Criar resultado normalizado
            result = UnifiedResult(
                id=result_id,
                termo_busca=query,
                fonte="DOU (PDF Offline)",
                fonte_tipo=SourceType.FEDERAL,
                orgao="Diário Oficial da União",
                orgao_uf=None,
                titulo=titulo,
                data_publicacao=data_publicacao,
                snippet=snippet,
                url_original=f"https://www.in.gov.br/web/dou/-/{data_publicacao.strftime('%Y%m%d')}",
                relevancia=relevancia,
                metadados={
                    "secao": secao,
                    "tipo_busca": "offline_pdf",
                    "exact_match": exact_match,
                    "fonte_download": "INLabs",
                    "bloco_numero": idx + 1
                }
            )

            results.append(result)

        return results

    async def get_latest_edition(self, secao: str = "1") -> Dict[str, Any]:
        """
        Obtém informações da última edição disponível do DOU

        Args:
            secao: Seção do DOU (1, 2, 3, Extra)

        Returns:
            Informações da última edição
        """
        try:
            # Tentar baixar edição de hoje
            pdf = await self.inlabs.download_dou_pdf(
                data_publicacao=date.today(),
                secao=f"do{secao}",
                use_cache=True
            )

            if pdf:
                return {
                    "secao": secao,
                    "data": date.today().isoformat(),
                    "status": "disponível",
                    "tamanho_bytes": len(pdf)
                }
            else:
                return {
                    "secao": secao,
                    "status": "não disponível",
                    "mensagem": "Edição de hoje ainda não publicada"
                }
        except Exception as e:
            return {
                "secao": secao,
                "status": "erro",
                "mensagem": str(e)
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica disponibilidade do serviço DOU (via INLabs)
        """
        # Verificar se INLabs está OK
        inlabs_health = await self.inlabs.health_check()

        if inlabs_health.get("status") == "online":
            return {
                "status": "online",
                "message": "Serviço DOU operacional (via INLabs PDF)",
                "metodo": "Download PDF → Cache → Busca Offline",
                "inlabs_status": "online"
            }
        else:
            return {
                "status": "degraded",
                "message": "INLabs indisponível",
                "inlabs_status": inlabs_health.get("status")
            }

    def get_source_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a fonte"""
        return {
            "nome": "DOU (PDF Offline)",
            "tipo": "federal",
            "descricao": "Diário Oficial da União - Busca offline em PDFs baixados via INLabs",
            "cobertura": "Todas as seções do DOU (1, 2, 3)",
            "requer_autenticacao": True,
            "status": "operacional",
            "limitacoes": [
                "Requer credenciais INLabs",
                "Download de PDFs pode ser lento para períodos longos",
                "Processamento de PDF é intensivo"
            ],
            "vantagens": [
                "Busca completa no texto do PDF",
                "Independente da conexão após download",
                "Cache de 72 horas para PDFs",
                "Garante estabilidade e precisão",
                "Suporta busca exata e flexível"
            ],
            "implementacao": "Download PDF → Cache em temp → Extração PyMuPDF → Busca offline",
            "cache": "Diretório temporário do sistema (72 horas)",
            "portal": "https://www.in.gov.br/consulta"
        }
