# PLANO DE IMPLEMENTAÇÃO - FECHO (fecho.pt)

Este documento estabelece o roteiro incremental de desenvolvimento do sistema **Fecho**, derivado estritamente das diretrizes de arquitetura, negócio e escopo de `docs/FSD.md` e do guia visual `docs/DESIGN.md`.

---

## Visão Geral das Fases

- [x] **Fase 1: Infraestrutura, Base do Projeto e PWA Shell**
- [ ] **Fase 2: Banco de Dados, Persistência e Isolamento Multi-tenant**
- [ ] **Fase 3: Autenticação, Sessão e Controle de Acesso (RBAC)**
- [ ] **Fase 4: Imóveis e Gestão de Carteira Ativa**
- [ ] **Fase 5: Calculadora Visual de Viabilidade Financeira (Client-side / Offline)**
- [ ] **Fase 6: Visitas, Feedback por Voz e Objeções (Human-in-the-Loop)**
- [ ] **Fase 7: Conteúdo e Scripts de Vídeo Curto com Teleprompter**
- [ ] **Fase 8: Pós-Venda, Esfera de Influência e Notificações de Aniversário**
- [ ] **Fase 9: Backoffice Web da Agência, Métricas e Exportação CSV**
- [ ] **Fase 10: Auditoria de Segurança, Testes E2E e Polimento Final**

---

## Detalhamento das Fases

### Fase 1: Infraestrutura, Base do Projeto e PWA Shell
* **Objetivo:** Estabelecer a fundação do repositório, ambiente virtual, servidor web ASGI FastAPI, configuração técnica sem arquivos `.env`, manifesto PWA, Service Worker offline, tokens de design e tratamento de insumos gráficos.
* **Checklist de Tarefas:**
  - [x] Criar estrutura de diretórios do projeto conforme arquitetura MVC/REST (`app/`, `config/`, `database/`, `logs/`, `static/`, `tests/`).
  - [x] Definir dependências centrais em `requirements.txt` (FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic, Passlib, python-jose, psycopg2-binary).
  - [x] Criar arquivo de configuração técnica em código `config/config.py` (sem `.env`, com segredos em código/painel PaaS).
  - [x] Configurar ponto de entrada ASGI `app/main.py` com FastAPI, roteamento estático, CORS e tratamento de erros.
  - [x] Configurar inicialização do Alembic (`alembic.ini` e `database/migrations/`).
  - [x] Extrair tokens do `docs/DESIGN.md` para `static/css/design-tokens.css` (cores Editorial PropTech Luxury, tipografia Plus Jakarta Sans, números tabulares, elevação e espaçamentos).
  - [x] Criar shells HTML semânticos `static/index.html` (Mobile PWA) e `static/backoffice.html` (Backoffice Web).
  - [x] Criar manifesto PWA `static/manifest.json` e esqueleto de Service Worker `static/sw.js`.
  - [x] Tratar insumo gráfico `docs/screen.png`, copiando para a pasta pública `static/img/screen.png`.
  - [x] Criar `.gitignore` para proteger arquivos de ambiente, cache e logs.
* **Critérios de Pronto:** Servidor FastAPI inicializa com sucesso em `http://localhost:8000`, rota `/health` responde `200 OK`, arquivos estáticos são servidos, PWA shell e tokens CSS carregam sem erros no navegador.
* **Arquivos e Pastas:** `app/`, `config/`, `database/`, `static/`, `logs/`, `alembic.ini`, `requirements.txt`, `.gitignore`.
* **Dependências:** Nenhuma.

---

### Fase 2: Banco de Dados, Persistência e Isolamento Multi-tenant
* **Objetivo:** Modelar as entidades relacionais no PostgreSQL via SQLAlchemy, implementar isolamento estrito por agência (`agencia_id`), configurar o motor de migrações Alembic e script de carga inicial (seed) para desenvolvimento.
* **Checklist de Tarefas:**
  - [ ] Implementar conexão e sessão do SQLAlchemy em `database/connection.py`.
  - [ ] Criar entidade `Tenant` (`app/models/tenant.py`) representando as agências imobiliárias.
  - [ ] Criar entidade `User` (`app/models/user.py`) com perfis `diretor` e `consultor`.
  - [ ] Criar entidade `Property` (`app/models/property.py`) com estados (*Ativo*, *Reservado*, *Vendido*).
  - [ ] Criar entidade `Visit` (`app/models/visit.py`) vinculada a imóvel, consultor e nível de interesse (1-5).
  - [ ] Criar entidade `Objection` (`app/models/objection.py`) com catálogo de tags padronizadas da agência.
  - [ ] Criar entidade `Contact` (`app/models/contact.py`) para esfera de influência e compradores pós-venda.
  - [ ] Criar entidades `Settings` (`app/models/settings.py`) e `Log` (`app/models/log.py`).
  - [ ] Configurar `database/migrations/env.py` para detecção automática dos modelos.
  - [ ] Gerar migração inicial de criação das tabelas via Alembic.
  - [ ] Criar script de seed de desenvolvimento com tenant demo, usuários de teste e catálogo inicial de objeções.
* **Critérios de Pronto:** Migração executada com sucesso no PostgreSQL; todas as chaves estrangeiras, índices e colunas `agencia_id` criados e validados.
* **Arquivos e Pastas:** `app/models/`, `database/connection.py`, `database/migrations/`.
* **Dependências:** Fase 1 concluída e serviço PostgreSQL ativo.

---

### Fase 3: Autenticação, Sessão e Controle de Acesso (RBAC)
* **Objetivo:** Implementar ciclo seguro de autenticação com senhas protegidas por Bcrypt, emissão de tokens JWT com claims de agência e perfil, e middleware/dependências de autorização para isolamento multi-tenant.
* **Checklist de Tarefas:**
  - [ ] Implementar utilitários de hash de senha (`passlib[bcrypt]`) em `app/services/auth_service.py`.
  - [ ] Implementar geração e decodificação de tokens JWT (`python-jose`) com tempo de expiração e claims obrigatórios (`sub`, `agencia_id`, `role`).
  - [ ] Criar esquemas Pydantic de autenticação (`LoginRequest`, `TokenResponse`, `UserResponse`) em `app/schemas/auth_schema.py`.
  - [ ] Criar dependências de injeção FastAPI (`get_current_user`, `get_current_tenant`, `require_diretor`, `require_consultor`).
  - [ ] Implementar endpoints em `app/controllers/auth_controller.py`: `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/refresh`.
  - [ ] Integrar fluxo de login na interface PWA e no backoffice web com armazenamento seguro de token no client.
* **Critérios de Pronto:** Consultores e diretores conseguem autenticar; endpoints protegidos rejeitam requisições sem token válido; contexto de agência (`agencia_id`) é injetado com segurança em todas as requisições autenticadas.
* **Arquivos e Pastas:** `app/controllers/auth_controller.py`, `app/services/auth_service.py`, `app/schemas/auth_schema.py`, `static/js/api.js`.
* **Dependências:** Fase 2 concluída.

---

### Fase 4: Imóveis e Gestão de Carteira Ativa
* **Objetivo:** Disponibilizar a gestão operacional de imóveis com validação rigorosa da máquina de estados (*Ativo* → *Reservado* → *Vendido*), filtragem estrita por agência e interface ágil para telemóveis.
* **Checklist de Tarefas:**
  - [ ] Criar esquemas Pydantic em `app/schemas/property_schema.py` (criação, atualização, exibição).
  - [ ] Implementar regras de transição de status no `app/services/property_service.py`.
  - [ ] Implementar endpoints REST em `app/controllers/properties_controller.py` (`GET`, `POST`, `PUT`, transição de status).
  - [ ] Desenvolver componente visual no frontend mobile para listagem de imóveis ativos em cartões no estilo *Editorial PropTech Luxury*.
  - [ ] Implementar seletor rápido de imóvel ativo no topo do fluxo operacional móvel.
* **Critérios de Pronto:** Operações de CRUD de imóveis funcionam; transições de status inválidas são rejeitadas pela regra de negócio; listagem no mobile é rápida e responsiva.
* **Arquivos e Pastas:** `app/controllers/properties_controller.py`, `app/services/property_service.py`, `app/schemas/property_schema.py`, `static/js/app.js`.
* **Dependências:** Fase 3 concluída.

---

### Fase 5: Calculadora Visual de Viabilidade Financeira (Client-side / Offline)
* **Objetivo:** Implementar o motor de cálculo financeiro e fiscal 100% no cliente (`calculator.js`), sem requisições de rede, suportando IMT (Continente e Ilhas), Imposto do Selo (0,8%), isenção de IMT Jovem e estimativa de prestação bancária (Sistema Price), com partilha estruturada no WhatsApp.
* **Checklist de Tarefas:**
  - [ ] Mapear tabelas oficiais de escalões de IMT em vigor em Portugal (Regimes HPP e Habitação Secundária; Continente, Região Autónoma da Madeira e Região Autónoma dos Açores).
  - [ ] Implementar lógica de isenção/redução de IMT Jovem até os limites legais.
  - [ ] Implementar cálculo de Imposto do Selo de aquisição (0,8%) e sobre financiamento bancário.
  - [ ] Implementar fórmula de amortização do Sistema Price para prestação mensal estimada (Euribor + Spread).
  - [ ] Criar interface da calculadora com tipografia de números tabulares (`tnum`), alternadores táteis HPP/Secundária e Continente/Ilhas.
  - [ ] Implementar botão de partilha formatada de simulação diretamente para o WhatsApp do cliente com texto polido e legível.
  - [ ] Validar funcionamento 100% offline via Service Worker.
* **Critérios de Pronto:** Valores simulados coincidem exatamente com simulações da Autoridade Tributária; cálculos reagem instantaneamente na digitação sem requisição ao servidor; simulação é copiada/partilhada no WhatsApp em 1 clique.
* **Arquivos e Pastas:** `static/js/calculator.js`, `static/index.html`, `static/css/style.css`.
* **Dependências:** Fase 1 concluída (pode ser desenvolvida em paralelo com a Fase 4).

---

### Fase 6: Visitas, Feedback por Voz e Objeções (Human-in-the-Loop)
* **Objetivo:** Permitir ao consultor gravar áudios de até 30 segundos após uma visita, orquestrar a transcrição e estruturação automática de notas com extração de nível de interesse e tags de objeção, tela de revisão obrigatória e disparo de feedback ao proprietário via WhatsApp.
* **Checklist de Tarefas:**
  - [ ] Implementar módulo de gravação de áudio no cliente (`static/js/audio_recorder.js`) com limite de 30s e suporte a fila offline.
  - [ ] Criar esquema Pydantic para registro de visita e transcrição estruturada (`app/schemas/visit_schema.py`).
  - [ ] Implementar serviço de transcrição e extração semântica em `app/services/speech_service.py` e `app/services/visit_service.py`.
  - [ ] Implementar endpoints em `app/controllers/visits_controller.py` (`POST /api/v1/visits/audio`, `POST /api/v1/visits`).
  - [ ] Construir ecrã móvel de revisão (*Human-in-the-Loop*) permitindo ajuste manual de texto, nível de interesse (1 a 5) e tags de objeção antes do salvamento.
  - [ ] Gerar texto polido de prestação de contas e acoplar Deep Link de envio direto para o WhatsApp do proprietário do imóvel ativo.
* **Critérios de Pronto:** Consultor grava áudio em campo; dados são estruturados e apresentados para validação prévia; visita é persistida com tags de objeção; link direto abre o WhatsApp com mensagem formatada pronta para envio.
* **Arquivos e Pastas:** `static/js/audio_recorder.js`, `app/controllers/visits_controller.py`, `app/services/speech_service.py`, `app/services/visit_service.py`, `app/schemas/visit_schema.py`.
* **Dependências:** Fase 4 concluída.

---

### Fase 7: Conteúdo e Scripts de Vídeo Curto com Teleprompter
* **Objetivo:** Fornecer geração ágil de roteiros de marketing imobiliário em 3 blocos estruturados (Gancho, 2 Destaques e CTA) orientados por objetivo comercial, integrados a um leitor de teleprompter otimizado para ensaio e gravação em vídeo.
* **Checklist de Tarefas:**
  - [ ] Implementar serviço de geração de roteiros em `app/services/script_service.py` cobrindo objetivos: *Angariação*, *Baixa de Preço* e *Open House*.
  - [ ] Criar endpoints em `app/controllers/scripts_controller.py` para sugerir e salvar scripts por imóvel.
  - [ ] Construir componente de Teleprompter em `static/js/teleprompter.js` com interface de alto contraste (fundo `#111111`, tipografia legível sob luz solar).
  - [ ] Implementar controles no teleprompter: contagem regressiva 3-2-1, velocidade de rolagem ajustável, pausar/retomar e botão de cópia de texto integral para clipboard.
* **Critérios de Pronto:** Roteiro é gerado em menos de 1 segundo para o imóvel selecionado; teleprompter rola suavemente no ecrã do telemóvel sem travas; botão de cópia copia o roteiro formatado.
* **Arquivos e Pastas:** `app/controllers/scripts_controller.py`, `app/services/script_service.py`, `static/js/teleprompter.js`, `static/index.html`.
* **Dependências:** Fase 4 concluída.

---

### Fase 8: Pós-Venda, Esfera de Influência e Notificações de Aniversário
* **Objetivo:** Capturar dados ágeis do comprador no momento da transição para "Vendido" (3 campos obrigatórios), alimentar a esfera de influência, notificar o consultor às 09:00 no aniversário da escritura e fornecer mensagens de relacionamento via WhatsApp em 1 toque, com respeito a regras de anonimização RGPD.
* **Checklist de Tarefas:**
  - [ ] Vincular a transição para estado "Vendido" à recolha obrigatória de: *Nome do Comprador*, *Telemóvel* e *Data da Escritura*.
  - [ ] Criar esquema e endpoints para contatos de pós-venda em `app/schemas/contact_schema.py` e `app/controllers/contacts_controller.py`.
  - [ ] Implementar rotina de alerta de aniversário de escritura em `app/services/contact_service.py`.
  - [ ] Criar templates de mensagens dinâmicas de felicitações/relacionamento com abertura direta no WhatsApp.
  - [ ] Implementar mecanismo de conformidade RGPD para anonimização definitiva de compradores quando solicitado ("Cliente Anonimizado").
* **Critérios de Pronto:** Imóvel só transita para Vendido com preenchimento dos 3 campos; consultor visualiza aniversariantes do dia; disparo de felicitações abre WhatsApp em 1 toque; rotina RGPD anonimiza registros sem quebrar integridade histórica.
* **Arquivos e Pastas:** `app/controllers/contacts_controller.py`, `app/services/contact_service.py`, `app/models/contact.py`.
* **Dependências:** Fase 4 concluída.

---

### Fase 9: Backoffice Web da Agência, Métricas e Exportação CSV
* **Objetivo:** Construir o painel web para Diretores e Brokers com KPIs de adesão e assiduidade dos consultores, mapa visual consolidado de objeções acumuladas por imóvel para renegociação de preços, parametrização remota de taxas e exportação aberta em CSV.
* **Checklist de Tarefas:**
  - [ ] Desenvolver interface web desktop/tablet em `static/backoffice.html` alinhada ao design system.
  - [ ] Implementar endpoints de agregação e KPIs em `app/controllers/backoffice_controller.py`:
    - Volume de visitas por consultor e taxa de adesão ao feedback por voz;
    - Gráfico consolidado de distribuição de objeções por imóvel (fundamentação de baixa de preço com proprietários);
    - Gestão do catálogo corporativo padronizado de tags de objeção da agência;
    - Gestão remota de parâmetros financeiros padrão (taxas de juros, spreads de referência).
  - [ ] Implementar serviço de exportação de dados em formato aberto CSV em `app/services/export_service.py` (sem dependência de bibliotecas de PDF).
  - [ ] Garantir que o acesso ao backoffice é restrito a usuários com perfil `diretor`.
* **Critérios de Pronto:** Diretores visualizam gráficos de objeções consolidadas por imóvel; filtros por período e consultor funcionam; exportação de CSV gera arquivos formatados em UTF-8 compatíveis com Excel/Numbers; consultores não têm acesso a estas rotas.
* **Arquivos e Pastas:** `static/backoffice.html`, `app/controllers/backoffice_controller.py`, `app/services/export_service.py`.
* **Dependências:** Fases 3, 4 e 6 concluídas.

---

### Fase 10: Auditoria de Segurança, Testes E2E e Polimento Final
* **Objetivo:** Executar testes unitários e de integração, auditar o isolamento lógico multi-tenant em 100% dos endpoints, validar resiliência offline do PWA e revisar a conformidade visual e técnica com `docs/FSD.md` e `docs/DESIGN.md`.
* **Checklist de Tarefas:**
  - [ ] Escrever suite de testes automatizados com `pytest` e `httpx` (TestClient do FastAPI) cobrindo autenticação, isolamento multi-tenant e regras de transição.
  - [ ] Auditar e garantir ausência total de vazamento de dados entre diferentes agências (`agencia_id`).
  - [ ] Validar comportamento da calculadora sob todos os escalões fiscais de Portugal (HPP, Secundária, Ilhas, IMT Jovem).
  - [ ] Testar instalação PWA, Service Worker e cache estático em navegadores móveis (Safari iOS e Chrome Android).
  - [ ] Validar contraste tipográfico e legibilidade sob luz solar intensa conforme especificação do design system.
  - [ ] Revisar documentação operacional de implantação em PaaS (Render / Railway).
* **Critérios de Pronto:** 100% dos testes passam sem falhas; isolamento multi-tenant verificado; PWA instala no ecrã inicial e calcula offline; sistema pronto para produção.
* **Arquivos e Pastas:** `tests/`, `static/sw.js`, `app/`, `docs/`.
* **Dependências:** Todas as fases anteriores concluídas.
