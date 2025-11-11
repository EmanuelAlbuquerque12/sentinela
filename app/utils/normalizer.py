"""
Normalizador de dados de diferentes fontes para formato unificado
"""
import hashlib
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from app.models.schemas import SourceType, UnifiedResult


class DataNormalizer:
    """
    Normaliza dados de diferentes fontes (Querido Diário, DataJud, TCU, DOU)
    para o formato UnifiedResult padrão.
    """

    @staticmethod
    def normalize_querido_diario(
        data: Dict[str, Any],
        query: str
    ) -> UnifiedResult:
        """
        Normaliza resposta do Querido Diário

        Input esperado:
        {
            "territory_id": "3550308",
            "date": "2024-11-10",
            "url": "https://...",
            "territory_name": "São Paulo",
            "state_code": "SP",
            "edition": "1234",
            "txt_url": "https://...",
            "excerpts": ["...texto..."]
        }
        """
        territory_id = data.get("territory_id", "")
        pub_date = data.get("date", "")

        # Gerar ID único
        result_id = DataNormalizer._generate_id(
            source="qd",
            identifier=f"{territory_id}_{pub_date}",
            query=query
        )

        # Extrair snippet dos excerpts
        excerpts = data.get("excerpts", [])
        snippet = excerpts[0] if excerpts else "Sem conteúdo disponível"
        snippet = DataNormalizer._truncate_snippet(snippet, max_length=300)

        # Calcular relevância baseada nos excerpts
        relevance = DataNormalizer._calculate_relevance(query, " ".join(excerpts))

        return UnifiedResult(
            id=result_id,
            termo_busca=query,
            fonte="Querido Diário",
            fonte_tipo=SourceType.MUNICIPAL,
            orgao=f"Prefeitura Municipal de {data.get('territory_name', 'Desconhecido')}",
            orgao_uf=data.get("state_code"),
            titulo=f"Diário Oficial - Edição {data.get('edition', 'S/N')}",
            data_publicacao=datetime.fromisoformat(pub_date).date() if pub_date else date.today(),
            snippet=snippet,
            url_original=data.get("url", ""),
            relevancia=relevance,
            metadados={
                "territory_id": territory_id,
                "edition": data.get("edition"),
                "is_extra_edition": data.get("is_extra_edition", False),
                "txt_url": data.get("txt_url"),
            }
        )

    @staticmethod
    def normalize_datajud(
        data: Dict[str, Any],
        query: str,
        tribunal: str = "CNJ"
    ) -> UnifiedResult:
        """
        Normaliza resposta do DataJud/CNJ

        Input esperado (Elasticsearch hits):
        {
            "_source": {
                "numeroProcesso": "0001234-56.2024.8.26.0100",
                "classe": {"nome": "Procedimento Comum"},
                "tribunal": "TJSP",
                "dataAjuizamento": "2024-01-15T00:00:00",
                "orgaoJulgador": {"nome": "1ª Vara Cível"},
                "assuntos": [{"nome": "Indenização"}],
                "movimentos": [...]
            }
        }
        """
        source = data.get("_source", data)
        numero_processo = source.get("numeroProcesso", "")

        # Gerar ID único
        result_id = DataNormalizer._generate_id(
            source="datajud",
            identifier=numero_processo,
            query=query
        )

        # Extrair informações
        classe = source.get("classe", {})
        orgao = source.get("orgaoJulgador", {})
        tribunal_nome = source.get("tribunal", tribunal)

        # Construir snippet dos movimentos e assuntos
        assuntos = [a.get("nome", "") for a in source.get("assuntos", [])]
        movimentos = source.get("movimentos", [])
        movimentos_texto = [
            f"{m.get('nome', '')} - {m.get('complementoNacional', '')}"
            for m in movimentos[:3]  # Pegar primeiros 3 movimentos
        ]

        snippet_parts = []
        if assuntos:
            snippet_parts.append(f"Assuntos: {', '.join(assuntos)}")
        if movimentos_texto:
            snippet_parts.append(f"Movimentos: {'; '.join(movimentos_texto)}")

        snippet = " | ".join(snippet_parts)
        snippet = DataNormalizer._truncate_snippet(snippet, max_length=300)

        # Data de ajuizamento
        data_ajuizamento = source.get("dataAjuizamento", "")
        pub_date = datetime.fromisoformat(data_ajuizamento.replace("Z", "+00:00")).date() if data_ajuizamento else date.today()

        # Relevância
        relevance = DataNormalizer._calculate_relevance(query, snippet)

        return UnifiedResult(
            id=result_id,
            termo_busca=query,
            fonte=f"DataJud/{tribunal_nome}",
            fonte_tipo=SourceType.JUDICIAL,
            orgao=f"{tribunal_nome} - {orgao.get('nome', 'Órgão desconhecido')}",
            orgao_uf=DataNormalizer._extract_uf_from_tribunal(tribunal_nome),
            titulo=f"Processo {numero_processo} - {classe.get('nome', 'Classe desconhecida')}",
            data_publicacao=pub_date,
            snippet=snippet,
            url_original=f"https://www.cnj.jus.br/processo/{numero_processo}",
            relevancia=relevance,
            metadados={
                "numeroProcesso": numero_processo,
                "classe": classe,
                "tribunal": tribunal_nome,
                "sistema": source.get("sistema"),
                "formato": source.get("formato", {}),
                "total_movimentos": len(movimentos)
            }
        )

    @staticmethod
    def normalize_tcu(
        data: Dict[str, Any],
        query: str
    ) -> UnifiedResult:
        """
        Normaliza resposta do TCU

        Input esperado:
        {
            "key": "12345",
            "tipo": "Acórdão",
            "anoAcordao": 2024,
            "numeroAcordao": 123,
            "colegiado": "Plenário",
            "dataSessao": "2024-11-10",
            "relator": "Ministro X",
            "sumario": "Texto...",
            "urlInteiro": "https://..."
        }
        """
        key = data.get("key", "")
        numero = data.get("numeroAcordao", "")
        ano = data.get("anoAcordao", "")

        # Gerar ID único
        result_id = DataNormalizer._generate_id(
            source="tcu",
            identifier=f"{ano}_{numero}",
            query=query
        )

        # Snippet do sumário
        sumario = data.get("sumario", "")
        snippet = DataNormalizer._truncate_snippet(sumario, max_length=300)

        # Data da sessão
        data_sessao = data.get("dataSessao", "")
        pub_date = datetime.fromisoformat(data_sessao).date() if data_sessao else date.today()

        # Relevância
        relevance = DataNormalizer._calculate_relevance(query, sumario)

        # Título
        tipo = data.get("tipo", "Acórdão")
        colegiado = data.get("colegiado", "")
        titulo = f"{tipo} nº {numero}/{ano} - {colegiado}"

        return UnifiedResult(
            id=result_id,
            termo_busca=query,
            fonte="TCU",
            fonte_tipo=SourceType.TCU,
            orgao="Tribunal de Contas da União",
            orgao_uf="DF",
            titulo=titulo,
            data_publicacao=pub_date,
            snippet=snippet,
            url_original=data.get("urlInteiro", ""),
            relevancia=relevance,
            metadados={
                "key": key,
                "tipo": tipo,
                "numeroAcordao": numero,
                "anoAcordao": ano,
                "colegiado": colegiado,
                "relator": data.get("relator"),
                "situacao": data.get("situacao"),
                "urlDocumento": data.get("urlDocumento")
            }
        )

    @staticmethod
    def normalize_dou(
        data: Dict[str, Any],
        query: str
    ) -> UnifiedResult:
        """
        Normaliza resposta do DOU (Dados Abertos)

        Input esperado:
        {
            "data_publicacao": "2024-11-10",
            "secao": "1",
            "pagina": 42,
            "titulo": "PORTARIA Nº 123...",
            "orgao": "Ministério da Fazenda",
            "conteudo": "Texto completo...",
            "edicao": "212",
            "url_certificacao": "https://..."
        }
        """
        pub_date_str = data.get("data_publicacao", "")
        secao = data.get("secao", "")
        edicao = data.get("edicao", "")

        # Gerar ID único
        result_id = DataNormalizer._generate_id(
            source="dou",
            identifier=f"{pub_date_str}_s{secao}_e{edicao}",
            query=query
        )

        # Snippet do conteúdo
        conteudo = data.get("conteudo", "")
        snippet = DataNormalizer._extract_context_snippet(query, conteudo, max_length=300)

        # Data de publicação
        pub_date = datetime.fromisoformat(pub_date_str).date() if pub_date_str else date.today()

        # Relevância
        relevance = DataNormalizer._calculate_relevance(query, conteudo)

        return UnifiedResult(
            id=result_id,
            termo_busca=query,
            fonte="DOU",
            fonte_tipo=SourceType.FEDERAL,
            orgao=data.get("orgao", "Órgão Federal"),
            orgao_uf="DF",
            titulo=data.get("titulo", "Sem título"),
            data_publicacao=pub_date,
            snippet=snippet,
            url_original=data.get("url_certificacao", "https://www.in.gov.br"),
            relevancia=relevance,
            metadados={
                "secao": secao,
                "pagina": data.get("pagina"),
                "edicao": edicao,
                "tipo_documento": data.get("tipo_documento")
            }
        )

    # --- Métodos auxiliares privados ---

    @staticmethod
    def _generate_id(source: str, identifier: str, query: str) -> str:
        """Gera ID único baseado em hash"""
        content = f"{source}_{identifier}_{query}"
        return f"{source}_{hashlib.md5(content.encode()).hexdigest()[:12]}"

    @staticmethod
    def _truncate_snippet(text: str, max_length: int = 300) -> str:
        """Trunca texto mantendo palavras completas"""
        text = text.strip()
        if len(text) <= max_length:
            return text

        truncated = text[:max_length]
        # Encontrar último espaço para não cortar palavras
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]

        return truncated + "..."

    @staticmethod
    def _extract_context_snippet(
        query: str,
        text: str,
        max_length: int = 300,
        context_chars: int = 150
    ) -> str:
        """
        Extrai snippet com contexto ao redor do termo buscado
        """
        text = text.strip()
        query_lower = query.lower()
        text_lower = text.lower()

        # Encontrar posição do termo
        pos = text_lower.find(query_lower)

        if pos == -1:
            # Termo não encontrado, retornar início do texto
            return DataNormalizer._truncate_snippet(text, max_length)

        # Calcular janela de contexto
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(query) + context_chars)

        snippet = text[start:end].strip()

        # Adicionar "..." se não começar/terminar no início/fim
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return DataNormalizer._truncate_snippet(snippet, max_length)

    @staticmethod
    def _calculate_relevance(query: str, text: str) -> float:
        """
        Calcula score de relevância simples (0-1) baseado em:
        - Frequência do termo
        - Posição no texto (mais cedo = mais relevante)
        """
        if not text:
            return 0.0

        query_lower = query.lower()
        text_lower = text.lower()

        # Contar ocorrências
        count = text_lower.count(query_lower)
        if count == 0:
            return 0.0

        # Score baseado em frequência (normalizado por tamanho do texto)
        frequency_score = min(count / 10.0, 0.7)  # Máximo 0.7 para frequência

        # Score baseado em posição (primeiro terço do texto = mais relevante)
        first_pos = text_lower.find(query_lower)
        position_score = 1.0 - (first_pos / len(text_lower))
        position_score = position_score * 0.3  # Máximo 0.3 para posição

        total_score = frequency_score + position_score
        return round(min(total_score, 1.0), 2)

    @staticmethod
    def _extract_uf_from_tribunal(tribunal: str) -> Optional[str]:
        """Extrai UF do nome do tribunal"""
        # Ex: TJSP -> SP, TRT3 -> MG, etc
        tribunal = tribunal.upper()

        # Tribunais com UF no final
        if len(tribunal) >= 4 and tribunal[:2] in ["TJ", "TR"]:
            uf = tribunal[2:4]
            if uf.isalpha() and len(uf) == 2:
                return uf

        # Tribunais regionais do trabalho (TRT + número)
        if tribunal.startswith("TRT"):
            # Mapear número do TRT para UF (simplificado)
            trt_map = {
                "TRT1": "RJ", "TRT2": "SP", "TRT3": "MG", "TRT4": "RS",
                "TRT5": "BA", "TRT6": "PE", "TRT7": "CE", "TRT8": "PA",
                "TRT9": "PR", "TRT10": "DF", "TRT11": "AM", "TRT12": "SC",
                "TRT13": "PB", "TRT14": "RO", "TRT15": "SP", "TRT16": "MA",
                "TRT17": "ES", "TRT18": "GO", "TRT19": "AL", "TRT20": "SE",
                "TRT21": "RN", "TRT22": "PI", "TRT23": "MT", "TRT24": "MS"
            }
            return trt_map.get(tribunal[:5])  # TRT + número

        # Tribunais superiores
        if tribunal in ["STF", "STJ", "TST", "TSE", "STM"]:
            return "DF"

        return None
