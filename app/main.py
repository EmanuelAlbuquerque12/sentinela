"""
Sentinela - Sistema de Busca Unificada em Diários Oficiais Brasileiros

FastAPI application main file
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import time
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routers import search_router


# Lifespan context manager para startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    # Startup
    print("🚀 Sentinela iniciando...")
    settings = get_settings()
    print(f"📊 Versão: {settings.app_version}")
    print(f"🔧 Debug: {settings.debug}")
    print(f"🔑 DataJud configurado: {settings.is_datajud_configured}")
    print("✅ Sentinela pronto!")

    yield

    # Shutdown
    print("👋 Sentinela encerrando...")


# Criar aplicação FastAPI
settings = get_settings()

app = FastAPI(
    title="Sentinela",
    description="""
    # 🔍 Sentinela - Busca Unificada em Diários Oficiais Brasileiros

    Sistema completo de busca textual unificada em todos os diários oficiais,
    cadernos judiciais e publicações oficiais do Brasil, integrando **apenas
    APIs gratuitas, públicas ou projetos open-source**.

    ## 📋 Fontes Integradas

    - **Querido Diário** (OKBR) - 600+ municípios
    - **DataJud/CNJ** - Todos os tribunais brasileiros
    - **TCU** - Tribunal de Contas da União
    - **DOU** - Diário Oficial da União (em implementação)

    ## 🚀 Características

    - ✅ **100% Gratuito** - Apenas APIs públicas
    - ⚡ **Busca Paralela** - Consultas simultâneas
    - 🔄 **Dados Normalizados** - JSON unificado
    - 📚 **Ampla Cobertura** - Centenas de fontes

    ## 🔧 Autenticação

    **DataJud/CNJ** requer API Key gratuita.
    Outras fontes não requerem autenticação.

    ## 📖 Documentação Completa

    - [GitHub Repository](https://github.com/EmanuelAlbuquerque12/sentinela)
    - [Documentação das APIs](docs/APIs.md)

    ---

    **Desenvolvido com 💚 para facilitar acesso à informação pública brasileira**
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# Configurar CORS
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de requisições com tempo de resposta"""
    start_time = time.time()

    response = await call_next(request)

    duration_ms = int((time.time() - start_time) * 1000)

    # Log básico (em produção, usar logger apropriado)
    print(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration_ms}ms"
    )

    # Adicionar header com tempo de resposta
    response.headers["X-Process-Time"] = str(duration_ms)

    return response


# Exception handler global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.debug else "Ocorreu um erro interno",
            "path": str(request.url.path)
        }
    )


# Incluir routers
app.include_router(search_router)


# Rota raiz
@app.get("/", tags=["root"])
async def root():
    """
    Informações básicas da API
    """
    return {
        "app": "Sentinela",
        "version": settings.app_version,
        "description": "Sistema de Busca Unificada em Diários Oficiais Brasileiros",
        "status": "online",
        "docs": "/docs",
        "health": "/api/v1/health",
        "sources": "/api/v1/sources",
        "search": "/api/v1/search",
        "repository": "https://github.com/EmanuelAlbuquerque12/sentinela"
    }


# OpenAPI customization
def custom_openapi():
    """Customiza OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Sentinela API",
        version=settings.app_version,
        description=app.description,
        routes=app.routes,
    )

    # Adicionar informações de contato e licença
    openapi_schema["info"]["contact"] = {
        "name": "Sentinela Project",
        "url": "https://github.com/EmanuelAlbuquerque12/sentinela",
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }

    # Adicionar tags
    openapi_schema["tags"] = [
        {
            "name": "search",
            "description": "Endpoints de busca unificada em diários oficiais"
        },
        {
            "name": "root",
            "description": "Informações básicas da API"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Script de execução direta
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
