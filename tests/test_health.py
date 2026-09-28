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


def test_static_files_and_calculator_served():
    """Valida se os arquivos estáticos da aplicação e da calculadora são servidos corretamente."""
    # Shell principal
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Calculadora de Viabilidade" in res_root.text

    # Motor matemático da calculadora
    res_calc = client.get("/static/js/calculator.js")
    assert res_calc.status_code == 200
    assert "calculateIMT" in res_calc.text
    assert "LIMITES_IMT_JOVEM" in res_calc.text

    # Manifesto PWA
    res_manifest = client.get("/static/manifest.json")
    assert res_manifest.status_code == 200

