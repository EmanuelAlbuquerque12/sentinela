"""
Serviço de integração com DOU Dados Abertos
Fonte: http://dados.gov.br/dataset/diario-oficial-da-uniao

Acessa dados estruturados mensais via CKAN API
"""
import asyncio
import csv
import json
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx

from app.config import get_settings
from app.models.schemas import UnifiedResult, SourceType
from app.utils.helpers import (
    cache_diario,
    get_cached_diario,
    matches_exact_query,
    extract_snippet_with_highlight,
    calculate_relevance_exact,
    generate_hash_id
)


class DOUDadosAbertosService:
    """
    Serviço de acesso aos dados abertos mensais do DOU via dados.gov.br

    Este serviço acessa os datasets estruturados (CSV/JSON) disponibilizados
    mensalmente pelo governo federal.
    """

    def __init__(self):
        self.settings = get_settings()
        # API CKAN do dados.gov.br
        self.ckan_url = "https://dados.gov.br/api/3"
        self.dataset_id = "diario-oficial-da-uniao"
        self.timeout = 60

        # Fallback: URLs diretas conhecidas
        self.direct_urls = {
            "2024": "https://www.gov.br/imprensa-nacional/pt-br/dados-abertos",
            "2025": "https://www.gov.br/imprensa-nacional/pt-br/dados-abertos"
        }

    async def search(
        self,
        query: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        size: int = 10,
        offset: int = 0,
        exact_match: bool = False,
        **kwargs
    ) -> List[UnifiedResult]:
        """
        Busca em dados abertos mensais do DOU

        Args:
            query: Termo de busca
            data_inicio: Data inicial
            data_fim: Data final
            size: Quantidade de resultados
            offset: Offset
            exact_match: Busca exata

        Returns:
            Lista de resultados
        """
        # Se não especificou datas, usar mês corrente
        if not data_fim:
            data_fim = date.today()
        if not data_inicio:
            data_inicio = data_fim.replace(day=1)  # Primeiro dia do mês

        results = []

        # Buscar recursos do dataset via CKAN
        recursos = await self._fetch_dataset_resources()

        if not recursos:
            print("⚠️  Nenhum recurso de dados abertos encontrado")
            return []

        # Filtrar recursos por data
        recursos_filtrados = self._filter_resources_by_date(
            recursos,
            data_inicio,
            data_fim
        )

        print(f"📊 {len(recursos_filtrados)} recursos de dados abertos disponíveis")

        # Processar cada recurso
        for recurso in recursos_filtrados[:5]:  # Limitar a 5 arquivos por performance
            if len(results) >= (size + offset):
                break

            dados = await self._fetch_resource_data(recurso)
            if dados:
                # Filtrar por query
                filtered = self._filter_dados(dados, query, exact_match)
                results.extend(filtered)

        # Aplicar paginação
        return results[offset:offset + size]

    async def _fetch_dataset_resources(self) -> List[Dict[str, Any]]:
        """
        Busca lista de recursos (arquivos) do dataset via CKAN API

        Returns:
            Lista de recursos disponíveis
        """
        try:
            url = f"{self.ckan_url}/action/package_show"
            params = {"id": self.dataset_id}

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        recursos = data.get("result", {}).get("resources", [])
                        print(f"✓ {len(recursos)} recursos encontrados via CKAN")
                        return recursos

            # Se CKAN não funcionar, retornar lista vazia
            # Em produção, poderia tentar URLs diretas conhecidas
            print("⚠️  CKAN API não retornou dados")
            return []

        except Exception as e:
            print(f"❌ Erro ao buscar recursos CKAN: {e}")
            return []

    def _filter_resources_by_date(
        self,
        recursos: List[Dict[str, Any]],
        data_inicio: date,
        data_fim: date
    ) -> List[Dict[str, Any]]:
        """
        Filtra recursos (arquivos) por período de datas

        Args:
            recursos: Lista de recursos
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Recursos filtrados
        """
        filtrados = []

        for recurso in recursos:
            # Tentar extrair data do nome ou metadados
            nome = recurso.get("name", "").lower()
            descricao = recurso.get("description", "").lower()

            # Procurar padrões de data no nome: AAAA-MM, AAAA_MM, mes-AAAA, etc
            # Exemplo: "dou_2024_01.csv", "janeiro-2024.json"

            # Por simplicidade, aceitar todos se não conseguir parsear data
            # Em produção, implementar parsing robusto de datas
            filtrados.append(recurso)

        return filtrados

    async def _fetch_resource_data(
        self,
        recurso: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Baixa e parseia dados de um recurso (arquivo CSV/JSON)

        Args:
            recurso: Metadados do recurso

        Returns:
            Lista de registros parseados
        """
        url = recurso.get("url")
        formato = recurso.get("format", "").lower()

        if not url:
            return []

        try:
            # Verificar cache
            resource_id = recurso.get("id", url[-20:])
            cached = get_cached_diario(
                source=f"dou_dados_abertos_{resource_id}",
                data=datetime.now(),
                max_age_hours=24 * 30  # 30 dias (dados mensais)
            )

            if cached:
                print(f"✓ Cache dados abertos: {recurso.get('name', 'recurso')}")
                return cached.get("content", [])

            # Download
            print(f"⏬ Downloading: {recurso.get('name', url)[:50]}...")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                content = response.text

            # Parse baseado no formato
            if formato in ['csv', 'text/csv']:
                dados = self._parse_csv(content)
            elif formato in ['json', 'application/json']:
                dados = self._parse_json(content)
            else:
                # Tentar detectar automaticamente
                if content.strip().startswith('[') or content.strip().startswith('{'):
                    dados = self._parse_json(content)
                else:
                    dados = self._parse_csv(content)

            # Salvar em cache
            if dados:
                cache_diario(
                    source=f"dou_dados_abertos_{resource_id}",
                    data=datetime.now(),
                    content=dados,
                    metadata={"recurso": recurso.get("name"), "total": len(dados)}
                )
                print(f"✓ {len(dados)} registros parseados e cached")

            return dados

        except Exception as e:
            print(f"❌ Erro ao baixar/parsear recurso: {e}")
            return []

    def _parse_csv(self, content: str) -> List[Dict[str, Any]]:
        """Parse CSV content"""
        try:
            reader = csv.DictReader(StringIO(content))
            return [row for row in reader]
        except Exception as e:
            print(f"❌ Erro ao parsear CSV: {e}")
            return []

    def _parse_json(self, content: str) -> List[Dict[str, Any]]:
        """Parse JSON content"""
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Tentar extrair lista de dentro do dict
                for key in ['data', 'items', 'results', 'records']:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]  # Dict único
            return []
        except Exception as e:
            print(f"❌ Erro ao parsear JSON: {e}")
            return []

    def _filter_dados(
        self,
        dados: List[Dict[str, Any]],
        query: str,
        exact_match: bool
    ) -> List[UnifiedResult]:
        """
        Filtra e normaliza dados baseado na query

        Args:
            dados: Lista de registros
            query: Termo de busca
            exact_match: Se True, apenas matches exatos

        Returns:
            Lista de resultados normalizados
        """
        results = []

        for registro in dados:
            # Campos comuns em dados abertos DOU
            titulo = registro.get("titulo", registro.get("title", ""))
            conteudo = registro.get("conteudo", registro.get("content", registro.get("texto", "")))
            orgao = registro.get("orgao", registro.get("orgao_responsavel", "Órgão Federal"))
            data_pub = registro.get("data_publicacao", registro.get("data", ""))

            # Concatenar para busca
            texto_completo = f"{titulo} {conteudo}"

            # Verificar match
            if not matches_exact_query(texto_completo, query):
                continue

            # Criar resultado normalizado
            snippet = extract_snippet_with_highlight(
                text=conteudo or titulo,
                query=query,
                exact_match=exact_match,
                max_length=400
            )

            relevancia = calculate_relevance_exact(
                query=query,
                text=texto_completo,
                exact_match=exact_match
            )

            # Parse data
            try:
                if isinstance(data_pub, str):
                    data_publicacao = datetime.fromisoformat(data_pub.split('T')[0]).date()
                else:
                    data_publicacao = date.today()
            except:
                data_publicacao = date.today()

            result_id = generate_hash_id(
                "dou_dados_abertos",
                str(data_publicacao),
                titulo[:50]
            )

            result = UnifiedResult(
                id=result_id,
                termo_busca=query,
                fonte="DOU (Dados Abertos)",
                fonte_tipo=SourceType.FEDERAL,
                orgao=orgao,
                orgao_uf=None,
                titulo=titulo or "Publicação DOU",
                data_publicacao=data_publicacao,
                snippet=snippet,
                url_original=registro.get("url", registro.get("link", "https://www.in.gov.br")),
                relevancia=relevancia,
                metadados={
                    "secao": registro.get("secao"),
                    "edicao": registro.get("edicao"),
                    "exact_match": exact_match,
                    "source": "dados_abertos_mensais"
                }
            )

            results.append(result)

        return results

    async def health_check(self) -> Dict[str, Any]:
        """Verifica disponibilidade do serviço"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Testar API CKAN
                response = await client.get(f"{self.ckan_url}/action/site_read")

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        return {
                            "status": "online",
                            "message": "CKAN API disponível",
                            "api": "dados.gov.br"
                        }

                return {
                    "status": "degraded",
                    "message": "CKAN API com problemas"
                }

        except Exception as e:
            return {
                "status": "offline",
                "erro": str(e)
            }

    def get_source_info(self) -> Dict[str, Any]:
        """Informações sobre a fonte"""
        return {
            "nome": "DOU (Dados Abertos Mensais)",
            "tipo": "federal",
            "descricao": "Dados estruturados mensais do DOU via dados.gov.br",
            "cobertura": "Todas as seções do DOU (dados históricos mensais)",
            "requer_autenticacao": False,
            "status": "operacional",
            "limitacoes": [
                "Dados disponibilizados com atraso (mensal)",
                "Não serve para busca em tempo real",
                "Depende da disponibilidade do portal dados.gov.br",
                "Estrutura dos dados pode variar"
            ],
            "vantagens": [
                "Dados estruturados e validados",
                "Acesso via API CKAN",
                "Cache de 30 dias",
                "Histórico completo disponível",
                "Formatos padronizados (CSV/JSON)"
            ],
            "fonte_oficial": "http://dados.gov.br/dataset/diario-oficial-da-uniao",
            "api": "CKAN 3.0"
        }
