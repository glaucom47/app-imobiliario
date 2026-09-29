# PROTOCOLO DE TESTES DE CAMPO E HOMOLOGAÇÃO (UAT) - FECHO (fecho.pt)

Este documento estabelece o roteiro prático de **Testes de Aceitação do Utilizador** (*User Acceptance Testing - UAT*), desenhado especificamente para validar em campo a ergonomia tátil, a resiliência offline e a eficácia operacional do sistema **Fecho** (`fecho.pt`) com consultores imobiliários e diretores de agências em Portugal.

---

## 1. Perfis de Utilizadores e Ambientes de Teste

| Perfil | Dispositivo Primário | Contexto Típico de Utilização | Foco Principal do Teste |
|---|---|---|---|
| **Consultor Imobiliário (Campo)** | Smartphone (iOS Safari / Android Chrome) | Na rua, em deslocações, em visitas a imóveis, caves e luz solar direta | Rapidez (< 1 minuto), operação com uma mão, modo offline e disparos WhatsApp |
| **Diretor Comercial / Broker (Escritório)** | Desktop / Tablet (Chrome / Safari / Edge) | Na agência, reuniões de equipa e reuniões com proprietários | KPIs de assiduidade, distribuição de objeções para renegociação e CSV |

---

## 2. Preparação Inicial e Instalação do PWA

Antes de iniciar os testes em campo:

1. **Aceder à Aplicação:**
   - No telemóvel, aceda a `https://fecho.pt` (ou ao endereço de teste local/homologação).
2. **Instalar no Ecrã Principal (PWA):**
   - **No iOS (Safari):** Toque no botão de partilha do Safari (ícone de quadrado com seta para cima) → Selecione **"Ecrã principal"** ou **"Adicionar ao ecrã principal"** → Confirme o nome **"Fecho"**.
   - **No Android (Chrome):** Toque no menu de três pontos do Chrome → Selecione **"Instalar aplicação"** ou **"Adicionar ao ecrã inicial"**.
3. **Autenticação Rápida:**
   - Toque no atalho de demonstração **"Consultor Demo"** (ou insira as credenciais profissionais fornecidas pela agência).
   - Confirme a exibição do crachá de perfil no cabeçalho.

---

## 3. Roteiro Passo a Passo de Cenários de Teste

### Cenário 1: Operação sob Luz Solar Intensa (Outdoor UX)
* **Objetivo:** Validar a legibilidade tipográfica e o contraste sob reflexo solar em visitas externas (rua, terraços, obras).
* **Passos:**
  1. Ao ar livre, toque no botão **"☀️ Luz Solar"** no canto superior direito do cabeçalho;
  2. Observe a elevação instantânea do contraste (fundo branco puro `#FFFFFF`, molduras reforçadas a 1.5px preto `#000000` e tipografia sólida);
  3. Verifique a leitura clara dos valores em euros (`€ 2.850.000`) e títulos de imóveis sem necessidade de proteger o ecrã com a mão.
* **Critério de Aceitação:** 100% dos textos essenciais legíveis sob radiação solar direta; botões de ação e números tabulares (`tnum`) nítidos e distinguíveis.

---

### Cenário 2: Visita em Cave / Garagem Subterrânea (Modo Offline e Fila Local)
* **Objetivo:** Garantir que o consultor não perde apontamentos de visita ao descer a garagens sem cobertura de rede móvel (3G/4G/5G).
* **Passos:**
  1. No telemóvel, ative o **Modo de Voo (Sem Rede)**;
  2. Confirme o aparecimento do banner negro: `⚡ Modo Offline Ativo • Calculadora e Teleprompter 100% Operacionais`;
  3. No ecrã principal, selecione o imóvel em foco e toque em **"Gravar Feedback de Visita (30s)"**;
  4. Grave um relato oral de 15 a 25 segundos (ou clique em **"💡 Simular Nota Demo"**);
  5. No ecrã de revisão (*Human-in-the-Loop*), ajuste o texto, selecione **4 estrelas** e marque a tag **"Ruído da Rua / Zona Movimentada"**;
  6. Toque em **"Guardar Visita & Enviar no WhatsApp"**;
  7. Observe a notificação de contingência: a visita é guardada na fila local do telemóvel;
  8. Repare no cabeçalho superior: surge o badge dourado `⚡ 1 local`;
  9. Desative o Modo de Voo (restabeleça a ligação de dados/Wi-Fi);
  10. Observe a sincronização automática: o badge pisca em verde notarizado (`✓ 1 sincronizada`) e confirma a sincronização;
  11. A ligação de WhatsApp (`wa.me`) é aberta com a mensagem formatada pronta para envio ao proprietário.
* **Critério de Aceitação:** Zero perda de dados na ausência de sinal; o badge local reflete com fidelidade as notas pendentes; a sincronização é automática e transparente ao recuperar a rede.

---

### Cenário 3: Simulação de IMT e Viabilidade Financeira com o Comprador
* **Objetivo:** Fornecer esclarecimento financeiro e fiscal imediato durante uma visita presencial em menos de 30 segundos.
* **Passos:**
  1. Na barra inferior tátil, toque no ícone **"🧮 Calculadora"**;
  2. Selecione a finalidade: **Habitação Própria Permanente (HPP)**;
  3. Região Fiscal: **Continente**;
  4. Nos chips de atalhos rápidos de valor, toque em **350k** (350.000 €);
  5. Ative o alternador **"Benefício IMT Jovem (Até 35 anos)"**;
  6. Observe o recalculo instantâneo no cliente (0ms de latência de rede):
     - Exibição do banner dourado: `✨ Poupança com IMT Jovem: € 7.502,74`;
     - IMT de Aquisição exibido como `€ 0,00` com badge `Isento`;
  7. Ajuste o controle deslizante (*slider*) de entrada de capital próprio para **20%**;
  8. Verifique o valor em escala da **Prestação Mensal Estimada** e o **Capital Próprio Inicial** total;
  9. Toque em **"Partilhar no WhatsApp"** (ou **"Copiar Simulação"**) e valide o texto polido pronto para envio ao cliente.
* **Critério de Aceitação:** Valores em total conformidade com a tabela oficial da AT e DL n.º 48-A/2024; funcionamento 100% offline; partilha no WhatsApp em 1 clique.

---

### Cenário 4: Ensaio de Vídeo Curto com Teleprompter (Formato Vertical 9:16)
* **Objetivo:** Apoiar o consultor na gravação rápida de vídeos de divulgação no Instagram Reels, TikTok ou WhatsApp Status.
* **Passos:**
  1. Na barra inferior, toque no ícone **"🎬 Scripts"**;
  2. Escolha o objetivo comercial: **"Baixa de Preço (Oportunidade)"**;
  3. Verifique a divisão do roteiro nos 3 blocos cronometrados (*1. Gancho Magnético*, *2. Dois Destaques*, *3. CTA*);
  4. Toque em **"🚀 Iniciar no Teleprompter"**;
  5. O ecrã entra no modo escuro profundo (`#111111`);
  6. Ajuste os controles superiores: velocidade da rolagem (`-` / `+`) e tamanho da fonte (`A-` / `A+`);
  7. Posicione o telemóvel na vertical na altura dos olhos e toque em **"▶ Iniciar"**;
  8. Acompanhe a contagem regressiva imersiva `3 - 2 - 1` e a rolagem suave do texto;
  9. Observe a **linha-guia de fixação do olhar** (*Reading Eye Guide*) no terço superior: ao ler naquela linha, os olhos do consultor apontam perfeitamente para a lente da câmera frontal do telemóvel.
* **Critério de Aceitação:** Transição suave de rolagem sem travamentos; controles acessíveis com uma mão; botão de cópia de texto funcional.

---

### Cenário 5: Fecho de Venda, Esfera de Influência e Alerta das 09:00
* **Objetivo:** Validar a integridade da máquina de estados (*Ativo* → *Reservado* → *Vendido*) e a retenção de clientes pós-venda.
* **Passos:**
  1. Na barra inferior, toque em **"🏢 Carteira"**;
  2. Selecione um imóvel ativo e toque no botão **"Alterar Estado"**;
  3. No modal, altere para **"Vendido"**;
  4. Repare que a secção de requisitos de fecho expande imediatamente:
     - Tente submeter sem preencher: a regra de negócio do FSD bloqueia e exige os 3 campos obrigatórios;
     - Preencha: *Nome do Comprador*, *Telemóvel* e a *Data da Escritura* (coloque a data de hoje para forçar o teste do aniversário);
     - Confirme a transição;
  5. Volte ao ecrã inicial: surge o banner matinal de destaque `🎉 Alerta Matinal das 09:00 - Aniversário de Escritura Hoje!`;
  6. Toque em **"Felicitar"** e dispare uma mensagem de relacionamento calorosa e personalizada via WhatsApp em 1 clique.
* **Critério de Aceitação:** Impossível marcar como vendido sem os 3 campos; comprador entra imediatamente na Esfera de Influência; disparo ao WhatsApp em 1 toque.

---

### Cenário 6: Painel Analítico da Direção Comercial (Backoffice Web)
* **Objetivo:** Validar as ferramentas analíticas exclusivas para Diretores e Brokers da agência.
* **Passos:**
  1. Num computador ou tablet, aceda a `/backoffice`;
  2. Autentique-se como **"Diretora Demo"**;
  3. **Aba Painel & Assiduidade:**
     - Alterne os períodos (7 dias, 30 dias, 90 dias);
     - Analise a taxa de adesão ao feedback por voz e o ranking individual dos consultores da equipa;
  4. **Aba Objeções por Imóvel:**
     - Selecione um imóvel específico da carteira;
     - Analise as barras de distribuição de objeções (ex: 60% apontam "Preço Elevado", 40% "Ruído");
     - Leia a caixa de **Parecer Técnico para Proprietário** com argumentação pronta fundamentada nos dados reais das visitas;
     - Teste o botão de envio direto por WhatsApp ao proprietário para sugerir reposicionamento de preço;
  5. **Aba Centro de Exportação CSV:**
     - Clique em **"Exportar Métricas CSV"** e **"Exportar Objeções CSV"**;
     - Abra os ficheiros no Excel / Numbers e valide a formatação limpa em UTF-8 com separação por vírgulas.
* **Critério de Aceitação:** RBAC bloqueia consultores nesta rota; filtros operam com rapidez; exportação CSV aberta e sem bibliotecas de PDF pesadas.

---

## 4. Formulário de Validação de Campo e Registro de Apontamentos

| Cenário de Teste | Dispositivo / SO Utilizado | Status (Aprovado / Observação / Falha) | Apontamentos do Consultor / Diretor |
|---|---|:---:|---|
| **1. Luz Solar Intensa** | | [ ] Aprovado | |
| **2. Visita Offline (Cave)** | | [ ] Aprovado | |
| **3. Calculadora & IMT Jovem** | | [ ] Aprovado | |
| **4. Teleprompter (Vídeo 9:16)** | | [ ] Aprovado | |
| **5. Fecho & Alerta 09:00** | | [ ] Aprovado | |
| **6. Backoffice da Direção** | | [ ] Aprovado | |

---

## 5. Critérios Finais de Homologação para Lançamento

O sistema **Fecho** será considerado apto para lançamento corporativo definitivo após:
1. 100% dos 6 cenários principais aprovados por pelo menos 2 consultores em trabalho de rua;
2. Confirmação de zero incidentes de perda de notas de visitas em zonas sem cobertura móvel;
3. Aceite formal da direção da agência sobre o relatório e gráficos de fundamentação de baixa de preço.
