"""
Teste de verificação de integridade da aplicação FastAPI.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Valida se o endpoint /health responde 200 OK com status correto."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Fecho"
