# STATUS DO PROJETO - FECHO (fecho.pt)

* **Última Atualização:** 04/10/2026 - 16:45
* **Fase Atual:** Evolução Contínua - Módulo de Direção Comercial & Gestão Ativa de Equipa (Fase 1 - MVP Completo: Backend & Frontend)
* **Status Geral:** Concluído, Documentado, Auditado e Operacional. O sistema conta com a implementação integral ponta a ponta (Backend e Frontend) do Módulo de Direção Comercial (FSD Seção 8): modelos relacionais SQLAlchemy (`Goal`, `PipelineDeal`, `WeeklyMeeting`, `MeetingCommitment`), migração Alembic aplicada, contratos Pydantic v2, serviços de negócio para KPIs consolidados, funil de 7 etapas, pipeline ponderado, semáforo de trajetória individual (🟢🟡🔴) e reuniões semanais com snapshot atômico congelado, além de endpoints REST sob `/api/v1/backoffice/` com controle de acesso estrito (`require_diretor`) e isolamento multi-tenant por agência. No Frontend do Backoffice (`static/backoffice.html`), corrigiu-se o carregamento e sincronização dinâmica dos consultores em todos os seletores e modais comerciais ("Definir Metas", "Novo Negócio", "Ficha Individual", "Reunião Semanal"), garantindo que novos consultores criados na aba da equipa apareçam imediatamente sem necessidade de recarregar a página. A suíte automatizada conta com **145 testes com 100% de aprovação**.

---

## 1. Visão Geral das Fases

| Fase | Descrição | Status |
|---|---|---|
| **Fase 1** | Infraestrutura, Base do Projeto e PWA Shell | Concluída |
| **Fase 2** | Banco de Dados, Persistência e Isolamento Multi-tenant | Concluída |
| **Fase 3** | Autenticação, Sessão e Controle de Acesso (RBAC) | Concluída |
| **Fase 4** | Imóveis e Gestão de Carteira Ativa | Concluída |
| **Fase 5** | Calculadora Visual de Viabilidade Financeira (Client-side / Offline) | Concluída |
| **Fase 6** | Visitas, Feedback por Voz e Objeções (Human-in-the-Loop) | Concluída |
| **Fase 7** | Conteúdo e Scripts de Vídeo Curto com Teleprompter | Concluída |
| **Fase 8** | Pós-Venda, Esfera de Influência e Notificações de Aniversário | Concluída |
| **Fase 9** | Backoffice Web da Agência, Métricas e Exportação CSV | Concluída |
| **Fase 10** | Auditoria de Segurança, Testes E2E e Polimento Final | Concluída |
| **Módulo Novo 1** | Captação e Angariação de Imóveis (Fontes Abertas: e-leiloes.pt e OLX FSBO) | Concluído |
| **Módulo Novo 2** | Estudo de Mercado Inteligente (ACM: INE 308 Concelhos, Caderneta, Voz, Casafari e Alfredo) | Concluído |
| **Módulo Comercial**| Direção Comercial & Gestão Ativa de Equipa (Fase 1 - MVP: Backend Completo) | Concluído |
| **Módulo RBAC** | Gestão de Consultores pela Direção, Ativação/Desativação e Isolamento Estrito | Concluído |
| **Documentação Final** | Manuais de Manutenção, FSD Atualizado e Modo Manutenção | Concluída |

---

## 2. Checklist da Documentação Final de Manutenção

- [x] **`docs/MANUTENCAO.md` criado:**
  - Visão geral completa (o que faz, para quem foi criado, problemas resolvidos, módulos principais);
  - Stack técnica detalhada e ambientes (local, testes e produção);
  - Guia passo a passo de como rodar localmente com credenciais de demonstração;
  - Mapa de pastas com orientações de quando mexer e cuidados por pasta;
  - Banco de dados e persistência (Alembic, SQLAlchemy, migrações, isolamento multi-tenant);
  - Autenticação e autorização (JWT, senhas com Bcrypt rounds=12, RBAC diretor/consultor);
  - Procedimento passo a passo para adicionar nova tela;
  - Procedimento passo a passo para adicionar novo campo a um cadastro;
  - Procedimento passo a passo para adicionar ou alterar regra de negócio;
  - Procedimento de testes (automatizados com `pytest` e testes manuais recomendados);
  - Cuidados críticos de segurança (10 pilares inegociáveis);
  - Registro de progresso e alertas do que NÃO fazer.
- [x] **`docs/COMO-PEDIR-MUDANCAS.md` criado:**
  - Orientações simples e didáticas para pessoas leigas pedirem mudanças para IA;
  - Regra de abertura de conversas futuras com leitura obrigatória dos arquivos vivos;
  - 8 modelos de prompts prontos adaptados à stack do Fecho (adicionar campo, criar tela, corrigir bug, alterar regra de negócio, ajustar visual conforme DESIGN.md, criar filtro/relatório, auditoria de segurança pós-mudança, preparar commit);
  - Checklist de 5 minutos antes de aceitar alterações da IA.
- [x] **`AGENTS.md` atualizado para Modo Manutenção:**
  - Contexto técnico consolidado da aplicação;
  - Protocolo mandatório de 7 passos antes de alterar e 5 passos depois de alterar;
  - Resumo de estrutura de pastas e comandos essenciais;
  - 10 regras de segurança inegociáveis;
  - Cuidados para não quebrar funcionalidades existentes;
  - Obrigatoriedade de rodar testes automatizados (`pytest -v`) e atualizar arquivos vivos.
- [x] **Módulo de Captação e Angariação de Imóveis (Fontes Abertas & FSBO):**
  - Entidades `LeadAngariacao` e `LeadBlacklist` com migração Alembic aplicada;
  - Scrapers modulares para `e-leiloes.pt` e `OLX Portugal` (Particulares);
  - Camada de serviço com conversão transacional em 1 clique gerando imóvel `Ativo`;
  - Governança RGPD com bloqueio por telefone em blacklist e mascaramento de dados;
  - Nova aba no Backoffice da Diretora com KPIs, filtros e modais com `escapeHtml`;
  - 7 novos testes automatizados dedicados cobrindo isolamento multi-tenant, conversão, auditoria e RGPD.
- [x] **Módulo de Estudo de Mercado Comparativo (ACM) com Leitura de Caderneta, Voz e Casafari/Alfredo:**
  - Base territorial dos 308 Concelhos de Portugal e 18 Distritos/Ilhas com medianas oficiais do INE (€/m²);
  - Parser inteligente e resiliente da Caderneta Predial Urbana emitida pela Autoridade Tributária;
  - Captura e análise multimodal de fotos reais dos cómodos com miniaturas;
  - Gravação de áudio nativa de até 30s do consultor com calibragem semântica ponderada (-20% a +25%);
  - Cálculo das 3 faixas estratégicas: Venda Rápida (45 dias), Preço Recomendado de Mercado e Preço Teto de Teste;
  - Conectores e matriz de benchmarking triplo com Casafari e Alfredo AI apurando o Índice de Convergência;
  - Relatório Executivo de 2 Páginas com diagramação A4 de luxo (`@media print`), disparo WhatsApp e link para Calculadora de IMT/Selo;
  - Service Worker elevado para `fecho-static-v14` com pré-cache offline completo de todos os novos recursos.
- [x] **Módulo de Direção Comercial & Gestão Ativa de Equipa (Fase 1 - MVP):**
  - Seção 8 do `docs/FSD.md` incorporada com especificação completa em Português Europeu;
  - Entidades SQLAlchemy criadas em `app/models/commercial.py`: `Goal`, `PipelineDeal`, `WeeklyMeeting` e `MeetingCommitment`;
  - Relações em cascata e foreign keys adicionadas em `Tenant`, `User` e `Property`;
  - Migração Alembic versionada gerada (`2295ed8b2647_cria_modulo_direcao_comercial_mvp.py`) e aplicada ao banco de dados;
  - Schemas Pydantic v2 estruturados em `app/schemas/commercial_schema.py` com validações rigorosas;
  - Camada de serviço de negócio implementada em `app/services/commercial_service.py` (filtros temporais, variações homólogas, funil de 7 etapas, pipeline ponderado, semáforo de trajetória);
  - Camada de reuniões semanais implementada em `app/services/meeting_service.py` (start com snapshot em tempo real e notas de visitas, gravação congelada e compromissos);
  - Endpoints REST da API implementados em `app/controllers/commercial_controller.py` e montados no ASGI com isolamento multi-tenant e RBAC `require_diretor`;
  - Frontend completo integrado no Backoffice Web (`static/backoffice.html`): aba "Direção Comercial", cards com variação homóloga, funil de 7 etapas interativo, tabela de desempenho da equipa com semáforo visual de trajetória (🟢 🟡 🔴) e 4 modais de gestão (Ficha Individual com 4 blocos analíticos, Sessão Semanal com snapshot congelado e compromissos, Gestão de Metas e Novo Deal no Pipeline);
  - Service Worker elevado para `fecho-static-v16` com renovação de cache;
  - 20 testes unitários e de integração dedicados em `tests/test_commercial_models.py` e `tests/test_commercial_api.py`.
- [x] **Módulo de RBAC: Gestão de Consultores pela Direção e Isolamento Multi-tenant Estrito:**
  - Schemas Pydantic v2 em `app/schemas/report_schema.py`: `ConsultorCreateRequest`, `ConsultorStatusUpdateRequest`, `ConsultorUpdateRequest`, `ConsultorResponse`;
  - Endpoints REST em `app/controllers/backoffice_controller.py` sob `/api/v1/backoffice/consultores`:
    - `POST /consultores`: Criação de novo consultor pela direção com injeção automática de `current_user.agencia_id`, validação de e-mail e hash Bcrypt (`rounds=12`);
    - `GET /consultores`: Listagem dos consultores pertencentes unicamente à agência do diretor logado;
    - `PATCH /consultores/{id}/status`: Ativação e desativação com bloqueio de login imediato para contas inativas e bloqueio de auto-desativação do diretor;
    - `PUT /consultores/{id}`: Edição de dados cadastrais e redefinição opcional de senha com Bcrypt (`rounds=12`);
  - Proteção e Isolamento Multi-tenant estritos: consultor de outra agência retorna HTTP 404; consultores são proibidos de aceder a dados de outros consultores e rotas de diretoria (HTTP 403 Forbidden);
  - Frontend no Backoffice (`static/backoffice.html` e `static/js/api.js`):
    - Nova aba "Equipa Comercial" na barra de navegação;
    - Tabela moderna com colunas de consultor, e-mail, telemóvel, pílula de status (Ativo/Inativo), data de registo e ações táteis;
    - Modal ágil `+ Novo Consultor` (Nome, E-mail, Telemóvel e Palavra-passe) e modal de edição;
    - Sanitização universal contra XSS via `escapeHtml(...)`;
  - Service Worker elevado para `fecho-static-v15` com cache invalidado;
  - 9 novos testes unitários e de integração dedicados em `tests/test_backoffice_consultores.py`.
- [x] **Validação Técnica e Suíte de Testes:**
  - 144 testes automatizados executados e 100% aprovados (`pytest -v`);
  - Zero falhas de sintaxe em scripts frontend (`node -c static/js/*.js`);
  - Guardrails de produção, rate limiting e proteção de isolamento multi-tenant validados.

---

## 3. Pendências

* **Nenhuma pendência técnica, funcional ou de documentação.**
* A Gestão de Consultores pela Direção, com isolamento multi-tenant estrito e controle de acessos RBAC, encontra-se 100% implementada, testada e auditada.

---

## 4. Próximo Passo Recomendado

* Prosseguir para a interface web de utilizador no Backoffice (`static/backoffice.html`), adicionando a nova aba e painel visual de "Direção Comercial" com os KPIs da agência, funil de vendas interativo, tabela de performance com semáforo visual e modal para reuniões semanais automatizadas, conforme tokens do `docs/DESIGN.md`.

