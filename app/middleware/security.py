"""
Middlewares Avançados de Segurança - Fecho (fecho.pt).

Implementa:
1. SecurityHeadersMiddleware: Cabeçalhos defensivos HTTP (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Cache-Control em APIs);
2. RateLimitMiddleware: Proteção contra ataques de força bruta e DoS com sliding window em memória;
3. PayloadLimitMiddleware: Bloqueio de requisições com carga excessiva para proteção de memória e Slowloris.
"""
from collections import defaultdict
import threading
import time
from typing import Dict, List, Tuple
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config.config import settings


class RateLimiter:
    """
    Controlador de taxa de requisições baseado em janela deslizante (Sliding Window).
    Thread-safe com bloqueio por mutex.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # Mapeia 'ip:scope' -> list de timestamps
        self._records: Dict[str, List[float]] = defaultdict(list)
        # Configurações de limite: (max_requests, window_seconds)
        self.limits: Dict[str, Tuple[int, int]] = {
            "login": (10, 60),      # 10 tentativas por minuto para login
            "api_general": (300, 60) # 300 requisições por minuto para APIs gerais
        }
        self.enabled: bool = True

    def reset(self):
        """Limpa todos os registros de taxa (útil para suítes de testes)."""
        with self._lock:
            self._records.clear()

    def get_client_ip(self, request: Request) -> str:
        """Extrai o IP real do cliente considerando cabeçalhos de proxy reverso (Render/Railway)."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Pega o primeiro IP da cadeia (cliente original)
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def is_rate_limited(self, ip: str, scope: str) -> Tuple[bool, int, int]:
        """
        Avalia se a requisição deve ser bloqueada.
        Retorna (is_limited, remaining_requests, retry_after_seconds).
        """
        if not self.enabled:
            return False, 999, 0

        max_reqs, window = self.limits.get(scope, self.limits["api_general"])
        now = time.monotonic()
        cutoff = now - window

        with self._lock:
            key = f"{ip}:{scope}"
            timestamps = self._records[key]

            # Remove registros fora da janela atual
            timestamps = [t for t in timestamps if t > cutoff]
            self._records[key] = timestamps

            if len(timestamps) >= max_reqs:
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + window - now))
                return True, 0, retry_after

            # Registra a requisição atual
            timestamps.append(now)
            remaining = max(0, max_reqs - len(timestamps))
            return False, remaining, 0


# Instância global do RateLimiter
rate_limiter = RateLimiter()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware para injeção de cabeçalhos de segurança HTTP em todas as respostas.
    Protege contra XSS, Clickjacking, MIME Sniffing e vazamento de informações.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # 1. Content-Security-Policy (CSP) estrito
        # Permite fontes Google, CDNs oficiais de Bootstrap/scripts e execução própria
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: blob:",
            "connect-src 'self'",
            "media-src 'self' blob:",
            "frame-ancestors 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # 2. Proteção contra Clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Proteção contra MIME Sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 4. Filtro XSS do Navegador
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 5. Política de Referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 6. Política de Permissões (Microfone permitido apenas para 'self' para notas de voz em visitas)
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(self)"

        # 7. HTTP Strict Transport Security (HSTS)
        # Aplicado em produção ou requisições HTTPS
        if settings.ENVIRONMENT == "production" or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # 8. Política de Cache anti-vazamento para endpoints sensíveis de API REST
        if request.url.path.startswith(settings.API_V1_STR):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware que intercepta requisições HTTP e aplica controle de taxa (Rate Limiting).
    Bloqueia ataques de força bruta no endpoint de login e requisições abusivas em endpoints gerais.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Determina o escopo da requisição
        scope = None
        if path == f"{settings.API_V1_STR}/auth/login":
            scope = "login"
        elif path.startswith(settings.API_V1_STR):
            scope = "api_general"

        if scope:
            client_ip = rate_limiter.get_client_ip(request)
            is_limited, remaining, retry_after = rate_limiter.is_rate_limited(client_ip, scope)

            if is_limited:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Limite de requisições excedido. Por favor, aguarde alguns momentos antes de tentar novamente.",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(rate_limiter.limits[scope][0]),
                        "X-RateLimit-Remaining": "0",
                    }
                )

        response = await call_next(request)

        if scope and isinstance(response, Response):
            # Injeta cabeçalho indicativo do limite
            max_limit = rate_limiter.limits[scope][0]
            response.headers["X-RateLimit-Limit"] = str(max_limit)

        return response


class PayloadLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware que rejeita requisições com corpo excessivamente grande.
    Protege contra ataques de DoS por esgotamento de memória e upload abusivo.
    """
    # 15MB para upload de áudio (visitas de até 30s)
    AUDIO_MAX_BYTES = 15 * 1024 * 1024
    # 2MB para outras requisições JSON
    DEFAULT_MAX_BYTES = 2 * 1024 * 1024

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                max_allowed = (
                    self.AUDIO_MAX_BYTES
                    if request.url.path == f"{settings.API_V1_STR}/visits/audio"
                    else self.DEFAULT_MAX_BYTES
                )
                if length > max_allowed:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"O tamanho da requisição ({length} bytes) excede o limite máximo permitido ({max_allowed} bytes)."
                        }
                    )
            except ValueError:
                pass

        return await call_next(request)
