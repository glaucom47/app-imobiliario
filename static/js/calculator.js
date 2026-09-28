/**
 * Motor Matemático Client-side / Offline - Calculadora de IMT, Selo e Prestação Bancária
 * Fecho (fecho.pt) - Sistema Imobiliário de Alta Performance
 *
 * Regulamentação fiscal em vigor em Portugal:
 * - Código do Imposto Municipal sobre as Transmissões Onerosas de Imóveis (CIMT)
 * - Artigo 17.º do CIMT (Taxas do Continente e majoração de 25% nos escalões das Regiões Autónomas)
 * - Decreto-Lei n.º 48-A/2024 (Isenção e redução de IMT e Selo para Jovens até 35 anos)
 * - Código do Imposto do Selo (Verba 1.1: 0,8% aquisição; Verba 17.1.4: 0,6% crédito >= 5 anos)
 * - Sistema de Amortização Price (Crédito à Habitação com prestações constantes)
 */

const Calculator = {
  // Constantes de Região Fiscal
  REGIOES: {
    CONTINENTE: 'continente',
    MADEIRA: 'madeira',
    ACORES: 'acores'
  },

  // Constantes de Finalidade do Imóvel
  TIPOS: {
    HPP: 'hpp', // Habitação Própria e Permanente
    SECUNDARIA: 'secundaria' // Habitação Secundária ou Arrendamento
  },

  // Taxas de Imposto do Selo
  TAXA_SELO_AQUISICAO: 0.008, // 0,8% sobre o valor de aquisição
  TAXA_SELO_FINANCIAMENTO_LONGO_PRAZO: 0.006, // 0,6% para crédito >= 5 anos
  TAXA_SELO_FINANCIAMENTO_CURTO_PRAZO: 0.005, // 0,5% para crédito entre 1 e 5 anos

  /**
   * Escalões de IMT em vigor no Continente
   * Cada escalão define: limite superior (limite), taxa marginal (taxa) e parcela a abater (abater).
   * Para os dois últimos escalões (taxa única de 6% e 7,5%), o imposto é calculado diretamente
   * multiplicando o valor total pela taxa fixa (sem dedução).
   */
  ESCALOES_CONTINENTE: {
    HPP: [
      { limite: 101917, taxa: 0.0, abater: 0.0, taxaUnica: false },
      { limite: 139412, taxa: 0.02, abater: 2038.34, taxaUnica: false },
      { limite: 190086, taxa: 0.05, abater: 6220.70, taxaUnica: false },
      { limite: 316772, taxa: 0.07, abater: 10022.42, taxaUnica: false },
      { limite: 633453, taxa: 0.08, abater: 13190.14, taxaUnica: false },
      { limite: 1102920, taxa: 0.06, abater: 0.0, taxaUnica: true },
      { limite: Infinity, taxa: 0.075, abater: 0.0, taxaUnica: true }
    ],
    SECUNDARIA: [
      { limite: 101917, taxa: 0.01, abater: 0.0, taxaUnica: false },
      { limite: 139412, taxa: 0.02, abater: 1019.17, taxaUnica: false },
      { limite: 190086, taxa: 0.05, abater: 5201.53, taxaUnica: false },
      { limite: 316772, taxa: 0.07, abater: 9003.25, taxaUnica: false },
      { limite: 611116, taxa: 0.08, abater: 12170.97, taxaUnica: false },
      { limite: 1102920, taxa: 0.06, abater: 0.0, taxaUnica: true },
      { limite: Infinity, taxa: 0.075, abater: 0.0, taxaUnica: true }
    ]
  },

  /**
   * Escalões de IMT para as Regiões Autónomas (Madeira e Açores)
   * Conforme artigo 17.º, n.º 2 do CIMT, os limites dos escalões são majorados em 25% (fator 1,25).
   */
  ESCALOES_ILHAS: {
    HPP: [
      { limite: 127396, taxa: 0.0, abater: 0.0, taxaUnica: false },
      { limite: 174265, taxa: 0.02, abater: 2547.93, taxaUnica: false },
      { limite: 237608, taxa: 0.05, abater: 7775.88, taxaUnica: false },
      { limite: 395965, taxa: 0.07, abater: 12528.03, taxaUnica: false },
      { limite: 791816, taxa: 0.08, abater: 16487.68, taxaUnica: false },
      { limite: 1378650, taxa: 0.06, abater: 0.0, taxaUnica: true },
      { limite: Infinity, taxa: 0.075, abater: 0.0, taxaUnica: true }
    ],
    SECUNDARIA: [
      { limite: 127396, taxa: 0.01, abater: 0.0, taxaUnica: false },
      { limite: 174265, taxa: 0.02, abater: 1273.96, taxaUnica: false },
      { limite: 237608, taxa: 0.05, abater: 6501.91, taxaUnica: false },
      { limite: 395965, taxa: 0.07, abater: 11254.06, taxaUnica: false },
      { limite: 763895, taxa: 0.08, abater: 15213.71, taxaUnica: false },
      { limite: 1378650, taxa: 0.06, abater: 0.0, taxaUnica: true },
      { limite: Infinity, taxa: 0.075, abater: 0.0, taxaUnica: true }
    ]
  },

  /**
   * Limites legais do benefício fiscal "IMT Jovem" (DL n.º 48-A/2024)
   * Aplicável apenas para HPP e jovens até 35 anos.
   */
  LIMITES_IMT_JOVEM: {
    CONTINENTE: {
      ISENCAO_TOTAL: 316772, // Até ao 4.º escalão do IMT
      ISENCAO_PARCIAL_MAX: 633453 // Até ao dobro do 4.º escalão
    },
    ILHAS: {
      ISENCAO_TOTAL: 395965, // Até ao 4.º escalão das Ilhas
      ISENCAO_PARCIAL_MAX: 791816 // Até ao dobro do 4.º escalão das Ilhas
    }
  },

  /**
   * Retorna os escalões aplicáveis à região e finalidade informadas.
   */
  getEscaloes(regiao, tipo) {
    const isIlhas = regiao === this.REGIOES.MADEIRA || regiao === this.REGIOES.ACORES;
    const fonte = isIlhas ? this.ESCALOES_ILHAS : this.ESCALOES_CONTINENTE;
    return tipo === this.TIPOS.SECUNDARIA ? fonte.SECUNDARIA : fonte.HPP;
  },

  /**
   * Calcula o IMT sem benefícios especiais com base nas tabelas legais.
   */
  calculateBaseIMT(valorAquisicao, tipo = this.TIPOS.HPP, regiao = this.REGIOES.CONTINENTE) {
    if (!valorAquisicao || valorAquisicao <= 0) {
      return {
        valorIMT: 0,
        taxaMarginal: 0,
        parcelaAbater: 0,
        taxaEfetiva: 0,
        taxaUnica: false
      };
    }

    const escaloes = this.getEscaloes(regiao, tipo);

    for (let i = 0; i < escaloes.length; i++) {
      const esc = escaloes[i];
      if (valorAquisicao <= esc.limite) {
        let valorIMT = 0;
        if (esc.taxaUnica) {
          // Nos escalões superiores, a taxa aplica-se a todo o montante
          valorIMT = valorAquisicao * esc.taxa;
        } else {
          valorIMT = Math.max(0, (valorAquisicao * esc.taxa) - esc.abater);
        }

        // Arredondamento centesimal legal
        valorIMT = Math.round(valorIMT * 100) / 100;
        const taxaMarginal = Math.round(esc.taxa * 10000) / 100;
        const taxaEfetiva = valorAquisicao > 0 ? (valorIMT / valorAquisicao) * 100 : 0;

        return {
          valorIMT,
          taxaMarginal,
          parcelaAbater: esc.abater,
          taxaEfetiva: Math.round(taxaEfetiva * 100) / 100,
          taxaUnica: esc.taxaUnica
        };
      }
    }

    return { valorIMT: 0, taxaMarginal: 0, parcelaAbater: 0, taxaEfetiva: 0, taxaUnica: false };
  },

  /**
   * Calcula o IMT contemplando o regime IMT Jovem (DL 48-A/2024).
   *
   * Regras:
   * 1. Apenas se tipo === 'hpp' e isJovem === true.
   * 2. Se valor <= ISENCAO_TOTAL: isenção total (IMT = 0€).
   * 3. Se ISENCAO_TOTAL < valor <= ISENCAO_PARCIAL_MAX:
   *    Beneficia de isenção na parte até ISENCAO_TOTAL;
   *    Sobre a parcela excedente (valor - ISENCAO_TOTAL), incide a taxa de 8%.
   * 4. Se valor > ISENCAO_PARCIAL_MAX: não há benefício; aplica-se a tabela geral.
   */
  calculateIMT(valorAquisicao, tipo = this.TIPOS.HPP, regiao = this.REGIOES.CONTINENTE, isJovem = false) {
    const calculoBase = this.calculateBaseIMT(valorAquisicao, tipo, regiao);

    if (!isJovem || tipo !== this.TIPOS.HPP || valorAquisicao <= 0) {
      return {
        ...calculoBase,
        isencaoJovemAplicada: false,
        isencaoTotal: false,
        isencaoParcial: false,
        poupancaJovem: 0
      };
    }

    const isIlhas = regiao === this.REGIOES.MADEIRA || regiao === this.REGIOES.ACORES;
    const limites = isIlhas ? this.LIMITES_IMT_JOVEM.ILHAS : this.LIMITES_IMT_JOVEM.CONTINENTE;

    if (valorAquisicao <= limites.ISENCAO_TOTAL) {
      // Isenção Total de IMT
      return {
        valorIMT: 0,
        taxaMarginal: 0,
        parcelaAbater: 0,
        taxaEfetiva: 0,
        taxaUnica: false,
        isencaoJovemAplicada: true,
        isencaoTotal: true,
        isencaoParcial: false,
        poupancaJovem: calculoBase.valorIMT
      };
    }

    if (valorAquisicao <= limites.ISENCAO_PARCIAL_MAX) {
      // Isenção Parcial: 8% sobre a parcela excedente ao teto
      const excedente = valorAquisicao - limites.ISENCAO_TOTAL;
      const valorIMT = Math.round(excedente * 0.08 * 100) / 100;
      const poupanca = Math.max(0, Math.round((calculoBase.valorIMT - valorIMT) * 100) / 100);
      const taxaEfetiva = valorAquisicao > 0 ? (valorIMT / valorAquisicao) * 100 : 0;

      return {
        valorIMT,
        taxaMarginal: 8.0,
        parcelaAbater: 0,
        taxaEfetiva: Math.round(taxaEfetiva * 100) / 100,
        taxaUnica: false,
        isencaoJovemAplicada: true,
        isencaoTotal: false,
        isencaoParcial: true,
        poupancaJovem: poupanca
      };
    }

    // Acima do limite máximo, não há benefício
    return {
      ...calculoBase,
      isencaoJovemAplicada: false,
      isencaoTotal: false,
      isencaoParcial: false,
      poupancaJovem: 0
    };
  },

  /**
   * Calcula o Imposto do Selo sobre a Aquisição (Verba 1.1 da Tabela Geral: 0,8%).
   * Se for IMT Jovem (HPP e isJovem === true):
   * - Até ISENCAO_TOTAL: Isenção total de Selo (0€).
   * - Entre ISENCAO_TOTAL e ISENCAO_PARCIAL_MAX: Isento até ISENCAO_TOTAL, incide 0,8% sobre o excedente.
   * - Acima de ISENCAO_PARCIAL_MAX: 0,8% sobre o valor total.
   */
  calculateImpostoDeSelo(valorAquisicao, tipo = this.TIPOS.HPP, regiao = this.REGIOES.CONTINENTE, isJovem = false) {
    if (!valorAquisicao || valorAquisicao <= 0) {
      return { valorSelo: 0, poupancaJovem: 0, isencaoTotal: false, isencaoParcial: false };
    }

    const valorBaseSelo = Math.round(valorAquisicao * this.TAXA_SELO_AQUISICAO * 100) / 100;

    if (!isJovem || tipo !== this.TIPOS.HPP) {
      return {
        valorSelo: valorBaseSelo,
        poupancaJovem: 0,
        isencaoTotal: false,
        isencaoParcial: false
      };
    }

    const isIlhas = regiao === this.REGIOES.MADEIRA || regiao === this.REGIOES.ACORES;
    const limites = isIlhas ? this.LIMITES_IMT_JOVEM.ILHAS : this.LIMITES_IMT_JOVEM.CONTINENTE;

    if (valorAquisicao <= limites.ISENCAO_TOTAL) {
      return {
        valorSelo: 0,
        poupancaJovem: valorBaseSelo,
        isencaoTotal: true,
        isencaoParcial: false
      };
    }

    if (valorAquisicao <= limites.ISENCAO_PARCIAL_MAX) {
      const excedente = valorAquisicao - limites.ISENCAO_TOTAL;
      const valorSelo = Math.round(excedente * this.TAXA_SELO_AQUISICAO * 100) / 100;
      const poupanca = Math.max(0, Math.round((valorBaseSelo - valorSelo) * 100) / 100);
      return {
        valorSelo,
        poupancaJovem: poupanca,
        isencaoTotal: false,
        isencaoParcial: true
      };
    }

    return {
      valorSelo: valorBaseSelo,
      poupancaJovem: 0,
      isencaoTotal: false,
      isencaoParcial: false
    };
  },

  /**
   * Calcula o Imposto do Selo sobre o Financiamento Bancário (Verba 17.1 da Tabela Geral).
   * - 0,6% para crédito igual ou superior a 5 anos (caso canônico para habitação);
   * - 0,5% para crédito entre 1 e 5 anos.
   */
  calculateSeloFinanciamento(montanteFinanciado, prazoAnos = 30) {
    if (!montanteFinanciado || montanteFinanciado <= 0) return 0;
    const taxa = prazoAnos >= 5 ? this.TAXA_SELO_FINANCIAMENTO_LONGO_PRAZO : this.TAXA_SELO_FINANCIAMENTO_CURTO_PRAZO;
    return Math.round(montanteFinanciado * taxa * 100) / 100;
  },

  /**
   * Estima prestação bancária mensal pelo Sistema de Amortização Price (prestações constantes).
   * Fórmula: PMT = M * [r * (1 + r)^n] / [(1 + r)^n - 1]
   * onde:
   *   M = montante financiado
   *   r = taxa de juro mensal (TAN anual / 12 / 100)
   *   n = número de prestações mensais (prazoAnos * 12)
   */
  calculatePrestacaoPrice(montanteFinanciado, taxaAnualPercentual, prazoAnos) {
    if (!montanteFinanciado || montanteFinanciado <= 0 || !prazoAnos || prazoAnos <= 0) {
      return {
        prestacaoMensal: 0,
        totalPago: 0,
        totalJuros: 0,
        numeroPrestacoes: 0
      };
    }

    const n = Math.round(prazoAnos * 12);
    if (n <= 0) {
      return { prestacaoMensal: 0, totalPago: 0, totalJuros: 0, numeroPrestacoes: 0 };
    }

    const taxaAnual = parseFloat(taxaAnualPercentual) || 0;
    if (taxaAnual <= 0) {
      // Sem juros
      const prestacao = Math.round((montanteFinanciado / n) * 100) / 100;
      return {
        prestacaoMensal: prestacao,
        totalPago: montanteFinanciado,
        totalJuros: 0,
        numeroPrestacoes: n
      };
    }

    const r = (taxaAnual / 100) / 12;
    const fator = Math.pow(1 + r, n);
    const prestacaoMensal = montanteFinanciado * ((r * fator) / (fator - 1));
    const prestacaoArredondada = Math.round(prestacaoMensal * 100) / 100;
    const totalPago = Math.round(prestacaoArredondada * n * 100) / 100;
    const totalJuros = Math.max(0, Math.round((totalPago - montanteFinanciado) * 100) / 100);

    return {
      prestacaoMensal: prestacaoArredondada,
      totalPago,
      totalJuros,
      numeroPrestacoes: n
    };
  },

  /**
   * Executa a simulação fiscal e financeira completa e integrada.
   */
  simulate(params = {}) {
    const valorImovel = Math.max(0, parseFloat(params.valorImovel) || 0);
    const tipo = params.tipo || this.TIPOS.HPP;
    const regiao = params.regiao || this.REGIOES.CONTINENTE;
    const isJovem = Boolean(params.isJovem);

    // Financiamento bancário
    const percentualEntrada = params.percentualEntrada !== undefined
      ? parseFloat(params.percentualEntrada)
      : 20; // 20% padrão de mercado
    const prazoAnos = parseInt(params.prazoAnos, 10) || 30;
    const taxaJuroAnual = params.taxaJuroAnual !== undefined ? parseFloat(params.taxaJuroAnual) : 3.5;

    // Cálculo do montante de entrada e financiado
    let valorEntrada = Math.round(valorImovel * (percentualEntrada / 100) * 100) / 100;
    if (params.valorEntradaManual !== undefined && params.valorEntradaManual !== null) {
      valorEntrada = Math.max(0, Math.min(valorImovel, parseFloat(params.valorEntradaManual) || 0));
    }
    const montanteFinanciado = Math.max(0, Math.round((valorImovel - valorEntrada) * 100) / 100);

    // Cálculos Fiscais
    const imtResult = this.calculateIMT(valorImovel, tipo, regiao, isJovem);
    const seloCompraResult = this.calculateImpostoDeSelo(valorImovel, tipo, regiao, isJovem);
    const seloFinanciamento = this.calculateSeloFinanciamento(montanteFinanciado, prazoAnos);

    // Cálculo Bancário (Price)
    const priceResult = this.calculatePrestacaoPrice(montanteFinanciado, taxaJuroAnual, prazoAnos);

    // Totais Consolidados
    const totalImpostos = Math.round((imtResult.valorIMT + seloCompraResult.valorSelo + seloFinanciamento) * 100) / 100;
    const totalPoupancaJovem = Math.round((imtResult.poupancaJovem + seloCompraResult.poupancaJovem) * 100) / 100;
    const capitalInicialNecessario = Math.round((valorEntrada + totalImpostos) * 100) / 100;

    return {
      valorImovel,
      tipo,
      regiao,
      isJovem,
      percentualEntrada: valorImovel > 0 ? Math.round((valorEntrada / valorImovel) * 1000) / 10 : 0,
      valorEntrada,
      montanteFinanciado,
      prazoAnos,
      taxaJuroAnual,
      imt: imtResult,
      seloCompra: seloCompraResult,
      seloFinanciamento,
      financiamento: priceResult,
      totais: {
        totalImpostos,
        totalPoupancaJovem,
        capitalInicialNecessario
      }
    };
  },

  /**
   * Formata número em moeda Euro (€) padrão português.
   */
  formatCurrency(value) {
    const num = parseFloat(value) || 0;
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  },

  /**
   * Gera texto polido e editorial para partilha da simulação no WhatsApp.
   */
  generateWhatsAppText(simulation, propertyTitle = '') {
    const fmt = (val) => Calculator.formatCurrency(val);
    const tipoNome = simulation.tipo === this.TIPOS.HPP
      ? 'Habitação Própria e Permanente (HPP)'
      : 'Habitação Secundária / Arrendamento';
    const regiaoNome = simulation.regiao === this.REGIOES.MADEIRA
      ? 'R.A. Madeira'
      : (simulation.regiao === this.REGIOES.ACORES ? 'R.A. Açores' : 'Continente');

    let text = `🏡 *Simulação Fiscal & Financeira • Fecho.pt*\n`;
    if (propertyTitle) {
      text += `*Imóvel:* ${propertyTitle}\n`;
    }
    text += `*Valor de Aquisição:* ${fmt(simulation.valorImovel)}\n\n`;

    text += `📋 *Impostos & Escritura:*\n`;
    text += `• Regime: ${tipoNome}\n`;
    text += `• Região Fiscal: ${regiaoNome}\n`;

    if (simulation.isJovem && simulation.tipo === this.TIPOS.HPP) {
      if (simulation.imt.isencaoTotal) {
        text += `• Benefício IMT Jovem: *Isenção Total (100%)*\n`;
      } else if (simulation.imt.isencaoParcial) {
        text += `• Benefício IMT Jovem: *Isenção Parcial*\n`;
      }
    }

    text += `• IMT: ${fmt(simulation.imt.valorIMT)}\n`;
    text += `• Imposto do Selo Aquisição (0,8%): ${fmt(simulation.seloCompra.valorSelo)}\n`;
    if (simulation.montanteFinanciado > 0) {
      text += `• Imposto do Selo Financiamento (0,6%): ${fmt(simulation.seloFinanciamento)}\n`;
    }
    text += `👉 *Total de Impostos:* ${fmt(simulation.totais.totalImpostos)}\n`;

    if (simulation.totais.totalPoupancaJovem > 0) {
      text += `✨ *Poupança com IMT Jovem:* ${fmt(simulation.totais.totalPoupancaJovem)}\n`;
    }

    if (simulation.montanteFinanciado > 0) {
      text += `\n🏦 *Financiamento Bancário Estimado:*\n`;
      text += `• Entrada (${simulation.percentualEntrada}%): ${fmt(simulation.valorEntrada)}\n`;
      text += `• Financiamento: ${fmt(simulation.montanteFinanciado)}\n`;
      text += `• Prazo: ${simulation.prazoAnos} anos (${simulation.financiamento.numeroPrestacoes} meses)\n`;
      text += `• Taxa de Juro Indicativa (TAN): ${simulation.taxaJuroAnual.toFixed(2)}%\n`;
      text += `👉 *Prestação Mensal Estimada:* *${fmt(simulation.financiamento.prestacaoMensal)} / mês*\n`;
    }

    text += `\n💼 *Capital Próprio Inicial Necessário:* *${fmt(simulation.totais.capitalInicialNecessario)}*\n`;
    text += `_(Entrada Inicial + Totalidade de Impostos de Escritura)_\n\n`;
    text += `_Simulação elaborada com base no Código do IMT e DL 48-A/2024. Valores indicativos sujeitos a validação notarial e aprovação bancária._\n`;
    text += `*Fecho.pt* • Assistente de Fecho Imobiliário`;

    return text;
  }
};

// Exportação para ambiente Node/CommonJS (compatibilidade de testes) e browser global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Calculator;
}
