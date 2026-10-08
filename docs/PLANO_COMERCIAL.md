# PLANO COMERCIAL, MODELO DE NEGÓCIOS E TABELA DE PREÇOS
## Plataforma SaaS Imobiliária Fecho (`meufecho.pt`) - Mercado Portugal

---

## 1. Visão Geral Executiva

O **Fecho (`meufecho.pt`)** é uma plataforma SaaS (*Software as a Service*) de inteligência comercial e produtividade móvel (PWA + Backoffice Web), desenvolvida especificamente para o mercado imobiliário em Portugal.

O sistema resolve a principal dor das agências imobiliárias portuguesas: **a perda de eficiência operacional no terreno e a falta de dados estruturados para fechar angariações e baixas de preço**. Através de captação FSBO/hastas públicas, notas de voz de 30s pós-visita com inteligência artificial (Gemini 1.5 Flash + Whisper), Estudo de Mercado Comparativo (ACM) com leitura da Caderneta Predial Urbana (AT) e medianas do INE (308 Concelhos), teleprompter de vídeo e calculadoras fiscais 100% offline (IMT, Selo e Isenção IMT Jovem), o Fecho transforma o telemóvel do consultor num centro produtivo de alto rendimento.

---

## 2. Modelos de Planos & Pacotes (*Pricing & Packaging*)

A arquitetura comercial é dividida em 3 níveis escaláveis (*Tiers*), atendendo desde o consultor autónomo até grandes redes de franquias imobiliárias em Portugal (Remax, ERA, Century 21, Zome, KW, Predimed, IAD e independentes).

| Recurso / Indicador | Plano Consultor Solo | Plano Agência / Loja *(Mais Popular)* | Plano Rede / Franquia |
|---|---|---|---|
| **Público-Alvo** | Consultor Autónomo / Agente Independente | Agências Locais / Lojas de Rede (1 Loja) | Grupos de Lojas / Redes Franqueadas |
| **Utilizadores Incluídos** | 1 Consultor | 1 Diretor Comercial + 10 Consultores | 3 Lojas (3 Diretores + 35 Consultores) |
| **Consultor Adicional** | N/A (Migra para Agência) | +€10 / mês por consultor | +€8 / mês por consultor |
| **Loja Adicional** | N/A | N/A | +€99 / mês por loja extra |
| **Preço Mensal** | **€39 / mês** + IVA | **€149 / mês** + IVA | **€399 / mês** + IVA |
| **Preço Anual (Desconto)**| **€32 / mês** (€384/ano) | **€119 / mês** (€1.428/ano) | **€329 / mês** (€3.948/ano) |
| **Desconto no Anual** | ~18% OFF | ~20% OFF | ~18% OFF |

---

## 3. Matriz de Funcionalidades por Plano

| Funcionalidade / Módulo | Consultor Solo (€32/mês) | Agência / Loja (€119/mês) | Rede / Franquia (€329/mês) |
|---|:---:|:---:|:---:|
| **Imóveis Ativos na Carteira** | Até 30 Imóveis | **Ilimitado** | **Ilimitado** |
| **Calculadoras Fiscais Offline (IMT/Selo/IMT Jovem)** | Sem Limites | Sem Limites | Sem Limites |
| **Visitas & Feedback por Voz (30s)** | Sem Limites | Sem Limites | Sem Limites |
| **Conteúdo & Scripts com Teleprompter** | Sem Limites | Sem Limites | Sem Limites |
| **Notificações Aniversário Escritura (Pós-Venda)**| Sem Limites | Sem Limites | Sem Limites |
| **Assistente IA Gemini (`/chat`)** | 50 consultas/mês | 500 consultas/mês/loja | **Ilimitado** |
| **ACM Inteligente com Caderneta & INE** | 15 estudos/mês | 150 estudos/mês/loja | **Ilimitado** |
| **Varredura FSBO (OLX) & Leilões (`e-leiloes.pt`)** | 30 leads/mês | 300 leads/mês/loja | **Ilimitado** (Fair Use 1.000/mês) |
| **Módulo Direção Comercial (Funil & Semáforo 🟢🟡🔴)** | ❌ | **Incluído** | **Incluído** |
| **Reuniões Semanais Automatizadas com Snapshot** | ❌ | **Incluído** | **Incluído** |
| **Gestão de RBAC (Ativar/Desativar Consultores)** | ❌ | **Incluído** | **Incluído** |
| **Relatórios de Objeções da Agência** | ❌ | **Incluído** | **Incluído** |
| **Exportação de Dados CSV / RGPD** | ❌ | **Incluído** | **Incluído** |
| **Painel Consolidador Multi-Loja** | ❌ | ❌ | **Incluído** |
| **Suporte Técnico & Onboarding** | Email / Chat (24h) | Onboarding VIP + WhatsApp (4h) | Gestor Dedicado + SLA 2h |

---

## 4. Análise Económica & Margem de Lucro (Unit Economics)

A infraestrutura do Fecho foi projetada para ter custos variáveis extremamente baixos, alavancando a API assíncrona FastAPI, PWA offline-first e processamento client-side.

### 4.1 Custo Direto por Agência (COGS - Cost of Goods Sold) no Plano Agência (€119/mês):

1. **Infraestrutura SaaS (Render PaaS + PostgreSQL Gerenciado):**
   - Servidor ASGI + DB PostgreSQL rateado por agência ativa: **~€3,50 / mês**.
2. **Consumo de APIs de IA (Google Gemini 1.5 Flash + Whisper API):**
   - Gemini 1.5 Flash (prompts de ACM, Chat e Scripts): ~$0.0003 por chamada. 500 chamadas = **~€0,20 / mês**.
   - Transcrição de Voz Whisper (30s por visita): ~$0.003 por transcrição. 200 visitas/mês = **~€0,55 / mês**.
3. **Manutenção de Dados INE / Leilões:**
   - Atualização de medianas dos 308 concelhos e scrapers: **~€0,45 / mês**.
4. **Total COGS por Agência:** **~€4,70 / mês**.

### 4.2 Demonstrativo de Margem por Subscrição Agência (€119/mês no plano anual):

* **Receita Mensal Recorrente (MRR):** €119,00
* **Custos Diretos (COGS):** -€4,70
* **Taxas de Gateway de Pagamento (Stripe/Multibanco - 1.4% + €0.25):** -€1,92
* **Margem Bruta (Gross Margin):** **€112,38 (94,4%)**
* **Custo de Suporte & Customer Success (Rateado):** -€12,00
* **CAC Amortizado (Marketing & Vendas):** -€25,00
* **Margem Líquida Operacional Estimada (EBITDA Margin):** **~€75,38 (63,3%)**

---

## 5. Proposta de Valor e Argumentário de Vendas (ROI para o Diretor de Loja)

### 5.1 O Diagnóstico da Dor do Diretor Comercial
> *"Sr. Diretor, os seus consultores passam horas no escritório a preencher relatórios de visitas que ninguém lê, hesitam ao calcular taxas de IMT e Selo à frente do comprador, e quando um imóvel fica parado 3 meses no mercado, a agência não tem dados reais para provar ao proprietário que o preço precisa de baixar."*

### 5.2 A Solução Fecho
> *"O Fecho é a ferramenta móvel que o consultor usa na rua. Em 30 segundos de voz pós-visita, a IA transcreve, categoriza as objeções do cliente (ex: 'cozinha pequena', 'preço alto') e gera o relatório automático para o proprietário no WhatsApp. O consultor ganha tempo de rua, e a direção ganha um gráfico estatístico imbatível de objeções para fechar a baixa de preço com o proprietário."*

### 5.3 O Cálculo Irrefutável do ROI (Retorno sobre o Investimento)

```text
Custo Anual do Fecho (Plano Agência - 1 Diretor + 10 Consultores): €1.428 + IVA / ano

Média de Comissão Imobiliária em Portugal (5% sobre imóvel de €200.000): €10.000 de honorários para a agência.

REGRAS DO ROI:
• Se o Fecho ajudar a sua agência a fechar APENAS 1 ANGARIAÇÃO OU VENDA EXTRA NO ANO INTEIRO:
  ➜ Receita Gerada: €10.000
  ➜ Custo do Fecho: €1.428
  ➜ Lucro Líquido Adicional: €8.572
  ➜ ROI Líquido: 600% de Retorno (7x o valor investido)!

Conclusão: 1 ÚNICA VENDA ADICIONAL PAGA 7 ANOS DE SUBSCRÇÃO DO FECHO PARA TODA A EQUIPA!
```

---

## 6. Estratégia de Lançamento & Teste Grátis (*Free Trial & Onboarding*)

### 6.1 Modelo de Experimentação: 14 Dias Grátis sem Cartão de Crédito
- **Acesso Total ao Plano Agência:** 14 dias de teste sem restrições para a loja (1 Diretor + 5 Consultores-chave).
- **Garantia de Não Bloqueio:** Sem necessidade de inserir cartão no registo para eliminar fricção.

### 6.2 Programa "Fecho Fast-Track em 24 Horas" (Onboarding de Alto Engajamento)
1. **Dia 1 (30 min - Reunião com a Direção):** Configuração da agência, definição das metas da equipa e ativação dos consultores via modal do Backoffice.
2. **Dia 1 (15 min - Formação Expressa da Equipa):** Vídeo de 3 minutos + demonstração ao vivo de como gravar a nota de voz de 30s e gerar a simulação de IMT Jovem em visita.
3. **Desafio 24h:** O consultor que registar a primeira visita por voz no primeiro dia ganha acesso a 5 captações exclusivas FSBO geradas pelo scraper do Fecho nas zonas da agência.

### 6.3 Estratégia de Go-To-Market (GTM) em Portugal
1. **Parcerias com Formadores & Academias Imobiliárias:** Acordos de recomendação com influenciadores e coaches de vendas imobiliárias em Portugal.
2. **Campanha B2B Direta no LinkedIn & WhatsApp:** Prospeção cirúrgica direcionada a Brokers e Diretores Comerciais da Remax, ERA, Century 21, Zome e KW.
3. **Efeito Viral "Proprietário-Consultor":** O relatório de visita estruturado enviado pelo consultor ao proprietário via WhatsApp contém a assinatura *"Gerado por Fecho - Inteligência Imobiliária em Portugal"*, criando awareness orgânico na rede de proprietários e investidores.

---
*Documento aprovado pela Estratégia Comercial & Arquitetura de Negócios do Fecho (meufecho.pt).*
