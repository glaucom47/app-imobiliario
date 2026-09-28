"""
Suíte de Testes Automatizados - Motor de Cálculo Financeiro e Fiscal
Fecho (fecho.pt) - Fase 5: Calculadora Visual (Client-side / Offline)

Testa com precisão matemática os cálculos de IMT, Imposto do Selo,
benefício de IMT Jovem (DL 48-A/2024) e amortização bancária pelo Sistema Price.
Executa o próprio arquivo client-side `static/js/calculator.js` através do Node.js
para garantir validação 100% fiel da implementação entregue no navegador.
"""

import json
import subprocess
from pathlib import Path

CALCULATOR_JS_PATH = Path("static/js/calculator.js").resolve()


def run_calculator_fn(fn_name: str, *args):
    """Executa uma função do objeto Calculator em static/js/calculator.js via Node.js."""
    args_json = json.dumps(args)
    js_code = f"""
    const Calculator = require({json.dumps(str(CALCULATOR_JS_PATH).replace('\\\\', '/'))});
    const result = Calculator.{fn_name}(...{args_json});
    console.log(JSON.stringify(result));
    """
    proc = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True
    )
    return json.loads(proc.stdout.strip())


def test_imt_continente_hpp_isencao_primeiro_escalao():
    """Valida isenção de IMT para HPP no Continente até 101.917€."""
    res = run_calculator_fn("calculateIMT", 80000, "hpp", "continente", False)
    assert res["valorIMT"] == 0.0
    assert res["taxaMarginal"] == 0.0
    assert res["isencaoJovemAplicada"] is False


def test_imt_continente_hpp_escaloes_intermediarios():
    """Valida cálculo de IMT nos escalões com taxas marginais e parcelas a abater."""
    # 2.º Escalão: 120.000€ (Taxa 2%, Abate 2.038,34€)
    # (120000 * 0.02) - 2038.34 = 2400 - 2038.34 = 361.66€
    res2 = run_calculator_fn("calculateIMT", 120000, "hpp", "continente", False)
    assert res2["valorIMT"] == 361.66
    assert res2["taxaMarginal"] == 2.0

    # 3.º Escalão: 160.000€ (Taxa 5%, Abate 6.220,70€)
    # (160000 * 0.05) - 6220.70 = 8000 - 6220.70 = 1779.30€
    res3 = run_calculator_fn("calculateIMT", 160000, "hpp", "continente", False)
    assert res3["valorIMT"] == 1779.30
    assert res3["taxaMarginal"] == 5.0

    # 4.º Escalão: 250.000€ (Taxa 7%, Abate 10.022,42€)
    # (250000 * 0.07) - 10022.42 = 17500 - 10022.42 = 7477.58€
    res4 = run_calculator_fn("calculateIMT", 250000, "hpp", "continente", False)
    assert res4["valorIMT"] == 7477.58
    assert res4["taxaMarginal"] == 7.0

    # 5.º Escalão: 400.000€ (Taxa 8%, Abate 13.190,14€)
    # (400000 * 0.08) - 13190.14 = 32000 - 13190.14 = 18809.86€
    res5 = run_calculator_fn("calculateIMT", 400000, "hpp", "continente", False)
    assert res5["valorIMT"] == 18809.86
    assert res5["taxaMarginal"] == 8.0


def test_imt_continente_hpp_taxas_unicas_superiores():
    """Valida escalões de taxa única (sem parcela a abater) acima de 633.453€."""
    # 6.º Escalão: 800.000€ (Taxa única 6%)
    # 800000 * 0.06 = 48.000€
    res6 = run_calculator_fn("calculateIMT", 800000, "hpp", "continente", False)
    assert res6["valorIMT"] == 48000.00
    assert res6["taxaUnica"] is True

    # 7.º Escalão: 1.500.000€ (Taxa única 7,5%)
    # 1500000 * 0.075 = 112.500€
    res7 = run_calculator_fn("calculateIMT", 1500000, "hpp", "continente", False)
    assert res7["valorIMT"] == 112500.00
    assert res7["taxaUnica"] is True


def test_imt_continente_secundaria():
    """Valida tabela de habitação secundária e arrendamento no Continente."""
    # Até 101.917€ paga 1% (sem isenção de 1º escalão)
    res1 = run_calculator_fn("calculateIMT", 80000, "secundaria", "continente", False)
    assert res1["valorIMT"] == 800.00

    # 200.000€: Taxa 7%, Abate 9.003,25€ -> (200000 * 0.07) - 9003.25 = 14000 - 9003.25 = 4996.75€
    res2 = run_calculator_fn("calculateIMT", 200000, "secundaria", "continente", False)
    assert res2["valorIMT"] == 4996.75


def test_imt_regioes_autonomas_majoracao():
    """Valida majoração de 25% nos limites dos escalões para Madeira e Açores."""
    # No Continente, 120.000€ paga IMT (361,66€)
    # Na Madeira/Açores, o 1.º escalão de isenção vai até 127.396€ (101.917 * 1.25)
    res_madeira = run_calculator_fn("calculateIMT", 120000, "hpp", "madeira", False)
    assert res_madeira["valorIMT"] == 0.0

    res_acores = run_calculator_fn("calculateIMT", 120000, "hpp", "acores", False)
    assert res_acores["valorIMT"] == 0.0


def test_imt_jovem_continente_isencao_total():
    """Valida isenção total de IMT e Selo para Jovens até 316.772€ no Continente."""
    res_imt = run_calculator_fn("calculateIMT", 280000, "hpp", "continente", True)
    assert res_imt["valorIMT"] == 0.0
    assert res_imt["isencaoTotal"] is True
    assert res_imt["poupancaJovem"] > 0

    res_selo = run_calculator_fn("calculateImpostoDeSelo", 280000, "hpp", "continente", True)
    assert res_selo["valorSelo"] == 0.0
    assert res_selo["isencaoTotal"] is True
    assert res_selo["poupancaJovem"] == 2240.00  # 280.000 * 0.008


def test_imt_jovem_continente_isencao_parcial():
    """Valida isenção parcial de IMT e Selo para Jovens entre 316.772€ e 633.453€."""
    valor = 350000.0
    res_imt = run_calculator_fn("calculateIMT", valor, "hpp", "continente", True)
    excedente = valor - 316772.0
    imt_esperado = round(excedente * 0.08, 2)  # 33.228 * 0.08 = 2.658,24€
    assert res_imt["valorIMT"] == imt_esperado
    assert res_imt["isencaoParcial"] is True

    res_selo = run_calculator_fn("calculateImpostoDeSelo", valor, "hpp", "continente", True)
    selo_esperado = round(excedente * 0.008, 2)  # 33.228 * 0.008 = 265,82€
    assert res_selo["valorSelo"] == selo_esperado
    assert res_selo["isencaoParcial"] is True


def test_imt_jovem_acima_do_limite_sem_beneficio():
    """Valida que acima de 633.453€ no Continente o benefício de IMT Jovem cessa."""
    valor = 700000.0
    res_imt = run_calculator_fn("calculateIMT", valor, "hpp", "continente", True)
    assert res_imt["isencaoJovemAplicada"] is False
    assert res_imt["valorIMT"] == 42000.00  # 700.000 * 0.06

    res_selo = run_calculator_fn("calculateImpostoDeSelo", valor, "hpp", "continente", True)
    assert res_selo["valorSelo"] == 5600.00  # 700.000 * 0.008


def test_imposto_do_selo_financiamento():
    """Valida o Imposto do Selo sobre o financiamento (0,6% para prazo >= 5 anos)."""
    # 200.000€ a 30 anos: 200.000 * 0.006 = 1.200€
    selo = run_calculator_fn("calculateSeloFinanciamento", 200000, 30)
    assert selo == 1200.00

    # 100.000€ a 3 anos: 100.000 * 0.005 = 500€
    selo_curto = run_calculator_fn("calculateSeloFinanciamento", 100000, 3)
    assert selo_curto == 500.00


def test_sistema_price_amortizacao_mensal():
    """Valida estimativa de prestação bancária mensal pelo Sistema Price."""
    # Financiamento: 200.000€, Taxa TAN: 3.5%, Prazo: 30 anos (360 meses)
    # PMT esperada: 898,09€
    res = run_calculator_fn("calculatePrestacaoPrice", 200000, 3.5, 30)
    assert res["numeroPrestacoes"] == 360
    assert abs(res["prestacaoMensal"] - 898.09) <= 0.05
    assert res["totalPago"] > 200000
    assert res["totalJuros"] > 0


def test_simulacao_completa_integrada_e_whatsapp():
    """Valida o método simulate() integrado e a geração de texto formatado para WhatsApp."""
    params = {
        "valorImovel": 350000,
        "tipo": "hpp",
        "regiao": "continente",
        "isJovem": True,
        "percentualEntrada": 20,
        "prazoAnos": 30,
        "taxaJuroAnual": 3.5
    }
    sim = run_calculator_fn("simulate", params)

    assert sim["valorImovel"] == 350000.0
    assert sim["valorEntrada"] == 70000.0
    assert sim["montanteFinanciado"] == 280000.0
    assert sim["imt"]["isencaoParcial"] is True
    assert sim["totais"]["totalImpostos"] > 0
    assert sim["totais"]["capitalInicialNecessario"] == sim["valorEntrada"] + sim["totais"]["totalImpostos"]

    # Geração do texto para WhatsApp
    texto_wa = run_calculator_fn("generateWhatsAppText", sim, "T3 Avenida da Liberdade")
    assert "Simulação Fiscal & Financeira" in texto_wa
    assert "T3 Avenida da Liberdade" in texto_wa
    assert "€" in texto_wa
    assert "350" in texto_wa
    assert "Benefício IMT Jovem: *Isenção Parcial*" in texto_wa
    assert "Prestação Mensal Estimada" in texto_wa
    assert "Capital Próprio Inicial Necessário" in texto_wa
