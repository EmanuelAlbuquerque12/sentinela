"""
Helpers para manipulação de PDFs e extração de acórdãos
Baseado nos scripts fornecidos para extração de acórdãos do TCU
"""
import re
import zipfile
from pathlib import Path
from typing import List, Tuple, Dict, Any
from io import BytesIO

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from unidecode import unidecode
except ImportError:
    # Fallback se unidecode não estiver disponível
    def unidecode(text: str) -> str:
        return text


def extrair_texto_pdf(pdf_content: bytes) -> str:
    """
    Extrai todo o texto de um PDF usando PyMuPDF

    Args:
        pdf_content: Conteúdo binário do PDF

    Returns:
        Texto extraído do PDF
    """
    if not fitz:
        raise ImportError("PyMuPDF (fitz) não está instalado")

    # Abrir PDF a partir de bytes
    doc = fitz.open(stream=pdf_content, filetype="pdf")

    textos = []
    for page in doc:
        textos.append(page.get_text("text"))

    doc.close()

    return "\n".join(t for t in textos if t)


def encontrar_acordaos(texto: str, termo: str) -> List[Tuple[str, str]]:
    """
    Procura acórdãos no texto que contenham o termo de busca

    Args:
        texto: Texto completo do DOU
        termo: Termo a buscar

    Returns:
        Lista de tuplas (identificador, conteúdo_completo)
    """
    # Normaliza termo para busca insensível a acentos e maiúsculas
    termo_norm = unidecode(termo).upper()

    # Padrão de início de acórdão: ACÓRDÃO ou ACORDAO, seguido de "N" e número
    padrao_inicio = re.compile(
        r"AC[ÓO]RD[ÃA]O\s+N[º°oO]*\s*\d+[\d/]*",
        re.IGNORECASE
    )

    # Encontra todos os índices onde começa um acórdão no texto original
    inicios = [m.start() for m in padrao_inicio.finditer(texto)]

    if not inicios:
        return []

    # Adiciona posição final
    inicios.append(len(texto))

    resultados = []

    for i in range(len(inicios) - 1):
        bloco_original = texto[inicios[i]:inicios[i + 1]]

        # Normaliza bloco para pesquisa do termo
        bloco_norm = unidecode(bloco_original).upper()

        if termo_norm in bloco_norm:
            # Extrai identificador
            ident_match = re.search(
                r"AC[ÓO]RD[ÃA]O\s+[Nn][º°oO]*\s*\d+[\d\/]*",
                bloco_original,
                re.IGNORECASE
            )
            identificador = ident_match.group(0).strip() if ident_match else f"Acordao_{i+1}"
            resultados.append((identificador, bloco_original.strip()))

    return resultados


def resumir_acordao(conteudo: str, ident: str) -> List[str]:
    """
    Extrai informações relevantes de um acórdão:
    - Número do acórdão
    - Número(s) do processo
    - Nomes com CPF
    - Trecho da decisão (ACORDAM)

    Args:
        conteudo: Texto completo do acórdão
        ident: Identificação do acórdão

    Returns:
        Lista de linhas com o resumo
    """
    linhas_resumo: List[str] = []

    # Número do acórdão
    linhas_resumo.append(f"Número do acórdão: {ident}")

    # Procurar números de processos
    processos: List[str] = []
    padrao_tc = re.compile(r"TC[\s-]*\d{2,6}\.\d{3}/\d{4}-\d")
    padrao_proc_num = re.compile(r"\b\d{3,}\.?\d*/\d{4}-\d\b")
    padrao_proc_label = re.compile(
        r"Processo\s*n[ºo]?\s*[:]?\s*([\d\.]+/[\d-]+)",
        re.IGNORECASE
    )

    for line in conteudo.splitlines():
        if re.search(r"Processo", line, re.IGNORECASE):
            # Busca por TC-...
            for m in padrao_tc.finditer(line):
                proc = m.group(0)
                proc = re.sub(r"\s+", "", proc)
                proc = proc.replace("TC", "TC-").replace("--", "-")
                processos.append(proc)

            # Busca por número após "Processo nº"
            m2 = padrao_proc_label.search(line)
            if m2:
                processos.append(m2.group(1))

            # Busca outros padrões de processo genéricos
            for m3 in padrao_proc_num.finditer(line):
                processos.append(m3.group(0))

    # Remover duplicados
    proc_unicos = []
    for p in processos:
        if p not in proc_unicos:
            proc_unicos.append(p)

    if proc_unicos:
        if len(proc_unicos) > 5:
            linhas_resumo.append(
                "Processo(s): " + "; ".join(proc_unicos[:5]) +
                f" … (+{len(proc_unicos)-5} outros)"
            )
        else:
            linhas_resumo.append("Processo(s): " + "; ".join(proc_unicos))
    else:
        linhas_resumo.append("Processo(s): não identificado")

    linhas_resumo.append("")

    # Procurar nomes com CPF
    padrao_cpf = re.compile(
        r"([A-Za-zÀ-ÖØ-öø-ÿ\s\.\'-]+)\s*\((\d{3}\.\d{3}\.\d{3}-\d{2})\)",
        re.UNICODE
    )
    nomes_cpfs: List[str] = []

    for nome, cpf in padrao_cpf.findall(conteudo):
        nome = nome.strip()
        if nome and cpf:
            nomes_cpfs.append(f"{nome} ({cpf})")

    if nomes_cpfs:
        linhas_resumo.append("Interessados/Responsáveis:")
        linhas_resumo.append("")
        for item in nomes_cpfs:
            linhas_resumo.append(f"{item}")
        linhas_resumo.append("")

    # Trecho da decisão
    texto_norm = unidecode(conteudo).upper()
    idx = texto_norm.find("ACORDAM")

    if idx != -1:
        decisao = conteudo[idx:].strip()
        linhas_resumo.append("Decisão:")
        linhas_resumo.append("")

        for linha in decisao.splitlines():
            linha = linha.strip()
            if linha:
                linhas_resumo.append(linha)

    return linhas_resumo


def gerar_docx(conteudo: str, destino: Path) -> None:
    """
    Gera um arquivo DOCX minimalista a partir de texto

    Suporta <PAGE_BREAK> para inserir quebras de página

    Args:
        conteudo: Texto a ser convertido em DOCX
        destino: Caminho do arquivo DOCX a ser criado
    """
    linhas = conteudo.splitlines()
    body_elements = []

    for linha in linhas:
        # Insere salto de página
        if linha.strip() == "<PAGE_BREAK>":
            body_elements.append('    <w:p><w:r><w:br w:type="page"/></w:r></w:p>')
            continue

        # Escapa caracteres XML
        linha_esc = (
            linha.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        body_elements.append(
            f'    <w:p><w:r><w:t xml:space="preserve">{linha_esc}</w:t></w:r></w:p>'
        )

    body_xml = "\n".join(body_elements)

    # document.xml
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        '  <w:body>\n'
        f'{body_xml}\n'
        '    <w:sectPr/>\n'
        '  </w:body>\n'
        '</w:document>'
    )

    # styles.xml
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        '  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">\n'
        '    <w:name w:val="Normal"/>\n'
        '    <w:qFormat/>\n'
        '    <w:pPr/>\n'
        '    <w:rPr/>\n'
        '  </w:style>\n'
        '</w:styles>'
    )

    # [Content_Types].xml
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/xml"/>\n'
        '  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        '  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>\n'
        '</Types>'
    )

    # _rels/.rels
    rels_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
        '</Relationships>'
    )

    # word/_rels/document.xml.rels
    doc_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )

    # Criar ZIP (DOCX)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as docx_zip:
        docx_zip.writestr("[Content_Types].xml", content_types_xml)
        docx_zip.writestr("_rels/.rels", rels_rels_xml)
        docx_zip.writestr("word/document.xml", document_xml)
        docx_zip.writestr("word/styles.xml", styles_xml)
        docx_zip.writestr("word/_rels/document.xml.rels", doc_rels_xml)
