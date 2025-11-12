"""
Configurações da aplicação Sentinela
"""
from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Aplicação
    app_name: str = "Sentinela"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    # APIs Externas - DataJud/CNJ
    # Chave pública - documentação em https://datajud-wiki.cnj.jus.br/api-publica/
    datajud_api_key: str = Field(
        default="cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
        description="API Key pública do DataJud/CNJ"
    )
    datajud_base_url: str = "https://api-publica.datajud.cnj.jus.br"

    # APIs Externas - Querido Diário
    querido_diario_base_url: str = "https://api.queridodiario.ok.org.br"

    # APIs Externas - TCU
    tcu_base_url: str = "https://dados-abertos.apps.tcu.gov.br/api"

    # APIs Externas - DOU (Dados Abertos - fallback)
    dou_dados_abertos_url: str = "http://dados.gov.br/dataset/diario-oficial-da-uniao"

    # APIs Externas - INLabs (Imprensa Nacional - acesso completo ao DOU)
    inlabs_username: str = Field(
        default="emanuelcarlosalbuquerque@servidor.adv.br",
        description="Email de login no INLabs"
    )
    inlabs_password: str = Field(
        default="Aq1sw2$&@",
        description="Senha do INLabs"
    )
    inlabs_base_url: str = "https://inlabs.in.gov.br"

    # Timeouts
    http_timeout: int = 30
    aggregator_timeout: int = 120

    # Cache Redis
    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_ttl: int = 86400  # 24 horas

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # Paginação
    default_page_size: int = 10
    max_page_size: int = 100

    # Busca
    max_sources_parallel: int = 5
    retry_attempts: int = 3
    retry_backoff_factor: float = 2.0

    # CORS
    cors_enabled: bool = True
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Logging
    log_format: str = "json"
    log_file: str = "logs/sentinela.log"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"

    # Elasticsearch (opcional)
    elasticsearch_enabled: bool = False
    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_index: str = "sentinela"

    @property
    def datajud_headers(self) -> dict:
        """Retorna headers para requisições ao DataJud"""
        if not self.datajud_api_key:
            return {}
        return {
            "Authorization": f"APIKey {self.datajud_api_key}",
            "Content-Type": "application/json"
        }

    @property
    def is_datajud_configured(self) -> bool:
        """Verifica se DataJud está configurado"""
        return bool(self.datajud_api_key and len(self.datajud_api_key) > 10)

    @property
    def is_inlabs_configured(self) -> bool:
        """Verifica se INLabs está configurado"""
        return bool(
            self.inlabs_username and
            self.inlabs_password and
            "@" in self.inlabs_username
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.
    Usa lru_cache para evitar recarregar o .env em cada chamada.
    """
    return Settings()
