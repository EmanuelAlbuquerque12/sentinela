"""
Funções auxiliares gerais
"""
import hashlib
import re
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Any


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


def parse_search_query(query: str) -> Tuple[str, bool]:
    """
    Faz parse da query de busca para detectar busca exata

    Exemplos:
        "licitação" -> ("licitação", False)  # busca normal
        '"processo 123"' -> ("processo 123", True)  # busca exata

    Args:
        query: Query de busca com possíveis aspas

    Returns:
        Tupla (termo_limpo, is_exact_match)
    """
    query = query.strip()

    # Detectar se está entre aspas
    if (query.startswith('"') and query.endswith('"')) or \
       (query.startswith("'") and query.endswith("'")):
        # Busca exata - remover aspas
        clean_query = query[1:-1].strip()
        return (clean_query, True)

    return (query, False)


def highlight_term_in_text(text: str, query: str, exact_match: bool = False) -> str:
    """
    Adiciona marcadores de destaque no termo buscado

    Args:
        text: Texto original
        query: Termo a destacar
        exact_match: Se True, destaca apenas match exato

    Returns:
        Texto com marcadores <mark>termo</mark>
    """
    if not query or not text:
        return text

    # Se busca exata, usar match literal
    if exact_match:
        # Escape de caracteres especiais do regex
        escaped_query = re.escape(query)
        pattern = re.compile(f'({escaped_query})', re.IGNORECASE)
    else:
        # Busca flexível - aceitar variações
        # Dividir query em palavras
        words = query.split()
        if len(words) > 1:
            # Múltiplas palavras - criar padrão flexível
            escaped_words = [re.escape(w) for w in words]
            pattern = re.compile(f'({"|".join(escaped_words)})', re.IGNORECASE)
        else:
            # Palavra única
            escaped_query = re.escape(query)
            pattern = re.compile(f'({escaped_query})', re.IGNORECASE)

    # Substituir com marcador
    highlighted = pattern.sub(r'<mark>\1</mark>', text)
    return highlighted


def extract_snippet_with_highlight(
    text: str,
    query: str,
    exact_match: bool = False,
    max_length: int = 300,
    context_chars: int = 150
) -> str:
    """
    Extrai snippet destacando o termo buscado

    Args:
        text: Texto completo
        query: Termo de busca
        exact_match: Se True, busca exata
        max_length: Tamanho máximo do snippet
        context_chars: Caracteres de contexto ao redor do termo

    Returns:
        Snippet com termo destacado
    """
    # Primeiro extrair snippet
    snippet = extract_snippet(text, query, max_length, context_chars)

    # Depois destacar o termo
    highlighted = highlight_term_in_text(snippet, query, exact_match)

    return highlighted


def matches_exact_query(text: str, query: str) -> bool:
    """
    Verifica se o texto contém o termo exato buscado

    Args:
        text: Texto para buscar
        query: Termo a buscar

    Returns:
        True se encontrou match exato
    """
    if not query or not text:
        return False

    # Busca case-insensitive mas match exato da sequência
    text_lower = text.lower()
    query_lower = query.lower()

    return query_lower in text_lower


def calculate_relevance_exact(query: str, text: str, exact_match: bool = False) -> float:
    """
    Calcula relevância considerando busca exata ou flexível

    Args:
        query: Termo de busca
        text: Texto para análise
        exact_match: Se True, prioriza matches exatos

    Returns:
        Score de 0.0 a 1.0
    """
    if not text or not query:
        return 0.0

    query_lower = query.lower()
    text_lower = text.lower()

    if exact_match:
        # Para busca exata, score binário mais posição
        if query_lower not in text_lower:
            return 0.0

        # Encontrou - calcular score baseado em posição
        first_pos = text_lower.find(query_lower)
        # Match exato tem score mínimo de 0.7
        position_score = 1.0 - (first_pos / len(text_lower))
        return round(0.7 + (position_score * 0.3), 2)
    else:
        # Busca flexível - usar cálculo original
        return calculate_relevance(query, text)


# Sistema de cache para diários
_CACHE_DIR = Path(tempfile.gettempdir()) / "sentinela_cache"


def get_cache_dir() -> Path:
    """Retorna diretório de cache, criando se necessário"""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def cache_diario(
    source: str,
    data: datetime,
    content: Any,
    metadata: Optional[dict] = None
) -> Path:
    """
    Armazena diário em cache

    Args:
        source: Nome da fonte (dou, inlabs, etc)
        data: Data da publicação
        content: Conteúdo do diário (XML, JSON, etc)
        metadata: Metadados opcionais

    Returns:
        Path do arquivo em cache
    """
    cache_dir = get_cache_dir() / source
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Nome do arquivo com data
    filename = f"{data.strftime('%Y-%m-%d')}.cache"
    filepath = cache_dir / filename

    # Criar estrutura de cache
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "data_publicacao": data.isoformat(),
        "metadata": metadata or {},
        "content": content if isinstance(content, (dict, list)) else str(content)
    }

    # Salvar como JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

    return filepath


def get_cached_diario(
    source: str,
    data: datetime,
    max_age_hours: int = 24
) -> Optional[dict]:
    """
    Recupera diário do cache se válido

    Args:
        source: Nome da fonte
        data: Data da publicação
        max_age_hours: Idade máxima do cache em horas

    Returns:
        Dados em cache ou None se não encontrado/expirado
    """
    cache_dir = get_cache_dir() / source
    filename = f"{data.strftime('%Y-%m-%d')}.cache"
    filepath = cache_dir / filename

    if not filepath.exists():
        return None

    # Verificar idade do cache
    file_age = datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)
    if file_age > timedelta(hours=max_age_hours):
        # Cache expirado
        return None

    # Ler cache
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        return cache_data
    except Exception:
        return None


def clear_old_cache(days: int = 7):
    """
    Remove arquivos de cache mais antigos que N dias

    Args:
        days: Número de dias para manter
    """
    cache_dir = get_cache_dir()
    if not cache_dir.exists():
        return

    cutoff_time = datetime.now() - timedelta(days=days)
    removed_count = 0

    for cache_file in cache_dir.rglob("*.cache"):
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_time < cutoff_time:
            cache_file.unlink()
            removed_count += 1

    if removed_count > 0:
        print(f"🧹 Removidos {removed_count} arquivos de cache antigos")
