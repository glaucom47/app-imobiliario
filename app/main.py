"""
Ponto de entrada da aplicação ASGI FastAPI - Fecho (fecho.pt).
"""
import os
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config.config import settings
from app.controllers import auth_controller

# Inicialização da aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Assistente imobiliário focado em visitas, cálculo fiscal (IMT/Selo), scripts e inteligência de mercado.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores da API REST (v1)
app.include_router(auth_controller.router, prefix=settings.API_V1_STR)

# Montagem dos arquivos estáticos do frontend/PWA
if os.path.exists(settings.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")


@app.get("/health", tags=["Sistema"])
async def health_check():
    """Endpoint de verificação de integridade da API."""
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION
    }


@app.get("/", tags=["Interface PWA"])
async def serve_pwa_shell():
    """Serve a casca principal da aplicação PWA móvel para consultores."""
    index_path = os.path.join(settings.STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "PWA shell não encontrado."}
    )


@app.get("/backoffice", tags=["Backoffice Web"])
async def serve_backoffice_shell():
    """Serve o painel web de gestão da agência para diretores e brokers."""
    backoffice_path = os.path.join(settings.STATIC_DIR, "backoffice.html")
    if os.path.exists(backoffice_path):
        return FileResponse(backoffice_path)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Backoffice shell não encontrado."}
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Tratamento de exceções HTTP da aplicação preservando código de status e cabeçalhos."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Tratamento de erros de validação de schemas Pydantic."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Parâmetros de requisição inválidos.", "errors": exc.errors()}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Tratamento centralizado de exceções inesperadas do servidor."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Ocorreu um erro interno no servidor.",
            "path": str(request.url.path)
        }
    )
