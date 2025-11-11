"""
Funções auxiliares gerais
"""
import hashlib
import re
from typing import Optional


def generate_hash_id(source: str, *args) -> str:
    """
    Gera ID único baseado em hash MD5

    Args:
        source: Nome da fonte (ex: 'qd', 'datajud', 'tcu')
        *args: Argumentos adicionais para compor o hash

    Returns:
        ID no formato: {source}_{hash_12_chars}
    """
    content = "_".join([source] + [str(arg) for arg in args])
    hash_str = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"{source}_{hash_str}"


def extract_snippet(
    text: str,
    query: Optional[str] = None,
    max_length: int = 300,
    context_chars: int = 150
) -> str:
    """
    Extrai snippet de um texto, opcionalmente centralizado no termo de busca

    Args:
        text: Texto completo
        query: Termo de busca (opcional)
        max_length: Tamanho máximo do snippet
        context_chars: Caracteres de contexto ao redor do termo

    Returns:
        Snippet truncado
    """
    text = text.strip()

    if not text:
        return ""

    # Se não há query, retornar início do texto
    if not query:
        return _truncate(text, max_length)

    query_lower = query.lower()
    text_lower = text.lower()

    # Encontrar posição do termo
    pos = text_lower.find(query_lower)

    if pos == -1:
        # Termo não encontrado, retornar início
        return _truncate(text, max_length)

    # Calcular janela de contexto
    start = max(0, pos - context_chars)
    end = min(len(text), pos + len(query) + context_chars)

    snippet = text[start:end].strip()

    # Adicionar "..." se necessário
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return _truncate(snippet, max_length)


def _truncate(text: str, max_length: int) -> str:
    """Trunca texto mantendo palavras completas"""
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    # Encontrar último espaço
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + "..."


def calculate_relevance(query: str, text: str) -> float:
    """
    Calcula score de relevância simples (0-1)

    Baseado em:
    - Frequência do termo no texto
    - Posição da primeira ocorrência

    Args:
        query: Termo de busca
        text: Texto para análise

    Returns:
        Score de 0.0 a 1.0
    """
    if not text or not query:
        return 0.0

    query_lower = query.lower()
    text_lower = text.lower()

    # Contar ocorrências
    count = text_lower.count(query_lower)
    if count == 0:
        return 0.0

    # Score de frequência (normalizado, máx 0.7)
    frequency_score = min(count / 10.0, 0.7)

    # Score de posição (primeira ocorrência no início = mais relevante)
    first_pos = text_lower.find(query_lower)
    position_score = 1.0 - (first_pos / len(text_lower))
    position_score = position_score * 0.3  # Máximo 0.3

    total = frequency_score + position_score
    return round(min(total, 1.0), 2)


def clean_html(html: str) -> str:
    """Remove tags HTML de um texto"""
    clean_text = re.sub(r'<[^>]+>', '', html)
    # Remover múltiplos espaços
    clean_text = re.sub(r'\s+', ' ', clean_text)
    return clean_text.strip()


def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ (formato básico)"""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    return len(cnpj) == 14 and cnpj.isdigit()


def validate_cpf(cpf: str) -> bool:
    """Valida CPF (formato básico)"""
    cpf = re.sub(r'[^0-9]', '', cpf)
    return len(cpf) == 11 and cpf.isdigit()


def extract_numero_processo(text: str) -> Optional[str]:
    """
    Extrai número de processo judicial do CNJ (padrão NNNNNNN-DD.AAAA.J.TR.OOOO)

    Returns:
        Número do processo ou None se não encontrado
    """
    pattern = r'\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}'
    match = re.search(pattern, text)
    return match.group(0) if match else None
