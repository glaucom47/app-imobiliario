# STATUS DO PROJETO - FECHO (fecho.pt)

* **Última Atualização:** 28/09/2026 - 23:05
* **Fase Atual:** Fase 1 - Infraestrutura, Base do Projeto e PWA Shell
* **Status Geral:** Concluída (Git inicializado, auditado e sincronizado com o GitHub)

---

## 1. Visão Geral das Fases

| Fase | Descrição | Status |
|---|---|---|
| **Fase 1** | Infraestrutura, Base do Projeto e PWA Shell | Concluída |
| **Fase 2** | Banco de Dados, Persistência e Isolamento Multi-tenant | Pendente |
| **Fase 3** | Autenticação, Sessão e Controle de Acesso (RBAC) | Pendente |
| **Fase 4** | Imóveis e Gestão de Carteira Ativa | Pendente |
| **Fase 5** | Calculadora Visual de Viabilidade Financeira (Client-side / Offline) | Pendente |
| **Fase 6** | Visitas, Feedback por Voz e Objeções (Human-in-the-Loop) | Pendente |
| **Fase 7** | Conteúdo e Scripts de Vídeo Curto com Teleprompter | Pendente |
| **Fase 8** | Pós-Venda, Esfera de Influência e Notificações de Aniversário | Pendente |
| **Fase 9** | Backoffice Web da Agência, Métricas e Exportação CSV | Pendente |
| **Fase 10** | Auditoria de Segurança, Testes E2E e Polimento Final | Pendente |

---

## 2. Checklist por Fase

### Fase 1: Infraestrutura, Base do Projeto e PWA Shell
- [x] Leitura e alinhamento com `docs/FSD.md`, `docs/DESIGN.md` e `docs/INSUMOS.md`
- [x] Criação do plano de construção incremental (`docs/PLANO.md`)
- [x] Criação do arquivo de contexto para agentes de IA (`AGENTS.md`)
- [x] Criação dos arquivos vivos (`docs/STATUS.md` e `docs/ERROS.md`)
- [x] Criação da estrutura de pastas conforme arquitetura (`app/`, `config/`, `database/`, `logs/`, `static/`, `tests/`)
- [x] Criação de `requirements.txt` com as dependências centrais do FSD
- [x] Criação de `config/config.py` para parametrização técnica sem arquivos `.env`
- [x] Criação de `app/main.py` com aplicação ASGI FastAPI inicial, rota `/health` e montagem de `/static`
- [x] Criação de `alembic.ini` e estrutura de migrações (`database/migrations/`)
- [x] Criação de tokens CSS em `static/css/design-tokens.css` baseados no `docs/DESIGN.md`
- [x] Criação dos shells HTML `static/index.html` e `static/backoffice.html`
- [x] Criação de `static/manifest.json` e `static/sw.js` (PWA)
- [x] Cópia e posicionamento do insumo gráfico `docs/screen.png` para `static/img/screen.png` e `static/img/logo.png`
- [x] Criação de `.gitignore` para proteção do projeto (revisado com proteção estrita de segredos, logs e dependências)
- [x] Criação de `.gitattributes` para padronização de quebras de linha e arquivos binários
- [x] Inicialização do repositório Git local e definição da branch principal (`main`)
- [x] Verificação de proteção de arquivos sensíveis (sem vazamento de chaves, senhas, tokens ou caches)
- [x] Criação do commit inicial de infraestrutura do projeto (commit `f6ff02b`: "Estrutura inicial do projeto")
- [x] Conexão com repositório remoto no GitHub (`https://github.com/glaucom47/app-imobiliario.git`)
- [x] Envio (`git push`) para o GitHub com rastreamento da branch `main` concluído com sucesso

### Fase 2: Banco de Dados, Persistência e Isolamento Multi-tenant
- [ ] Configuração da conexão com PostgreSQL (`database/connection.py`)
- [ ] Modelagem da entidade `Tenant` (`app/models/tenant.py`)
- [ ] Modelagem da entidade `User` (`app/models/user.py`)
- [ ] Modelagem da entidade `Property` (`app/models/property.py`)
- [ ] Modelagem da entidade `Visit` (`app/models/visit.py`)
- [ ] Modelagem da entidade `Objection` (`app/models/objection.py`)
- [ ] Modelagem da entidade `Contact` (`app/models/contact.py`)
- [ ] Modelagem das entidades `Settings` e `Log`
- [ ] Configuração do `env.py` do Alembic para autogenerate
- [ ] Execução da primeira migração estrutural
- [ ] Script de seed inicial com dados de teste

### Fase 3: Autenticação, Sessão e Controle de Acesso (RBAC)
- [ ] Hash de senhas com passlib e bcrypt
- [ ] Geração e validação de tokens JWT (python-jose) com `agencia_id`
- [ ] Schemas Pydantic de autenticação
- [ ] Endpoints de login e perfil (`/api/v1/auth`)
- [ ] Dependências de segurança do FastAPI para injeção de usuário e tenant
- [ ] Controle de acesso por perfil (Diretor vs Consultor)

### Fase 4: Imóveis e Gestão de Carteira Ativa
- [ ] Schemas Pydantic de imóveis
- [ ] Serviço de imóveis com máquina de estados (*Ativo* → *Reservado* → *Vendido*)
- [ ] Endpoints REST de imóveis (`/api/v1/properties`) com isolamento multi-tenant
- [ ] Componente visual de listagem de imóveis ativos no mobile PWA

### Fase 5: Calculadora Visual de Viabilidade Financeira (Client-side / Offline)
- [ ] Motor matemático de IMT (Continente, Madeira e Açores; HPP e Secundária)
- [ ] Lógica de isenção de IMT Jovem
- [ ] Cálculo de Imposto do Selo (0,8%) de compra e financiamento
- [ ] Amortização pelo Sistema Price
- [ ] Interface tátil da calculadora com números tabulares
- [ ] Integração com Deep Link para partilha no WhatsApp

### Fase 6: Visitas, Feedback por Voz e Objeções (Human-in-the-Loop)
- [ ] Gravador de áudio no cliente (até 30 segundos)
- [ ] Schemas e serviço de transcrição e estruturação automática
- [ ] Endpoints de visitas e extração de objeções
- [ ] Ecrã de revisão (*Human-in-the-Loop*) antes do salvamento
- [ ] Geração de mensagem estruturada e Deep Link para WhatsApp do proprietário

### Fase 7: Conteúdo e Scripts de Vídeo Curto com Teleprompter
- [ ] Serviço de geração de roteiros em 3 blocos (Gancho, 2 Destaques, CTA)
- [ ] Endpoints de roteiros por objetivo (Angariação, Baixa de Preço, Open House)
- [ ] Interface do Teleprompter com fundo `#111111`, contagem 3-2-1 e rolagem suave
- [ ] Botão de cópia rápida para clipboard

### Fase 8: Pós-Venda, Esfera de Influência e Notificações de Aniversário
- [ ] Validação dos 3 campos ao passar imóvel para Vendido (*Nome*, *Telemóvel*, *Data da Escritura*)
- [ ] Cadastro e listagem de compradores na esfera de influência
- [ ] Notificação no telemóvel às 09:00 para aniversários de escritura
- [ ] Mensagens dinâmicas de pós-venda para WhatsApp em 1 clique
- [ ] Rotina de anonimização conforme RGPD

### Fase 9: Backoffice Web da Agência, Métricas e Exportação CSV
- [ ] Interface web de desktop/tablet em `static/backoffice.html`
- [ ] KPIs de assiduidade dos consultores e volume de visitas
- [ ] Gráfico consolidado de objeções por imóvel para renegociação de preços
- [ ] Gestão remota de catálogo de tags e parâmetros financeiros
- [ ] Exportação de relatórios em formato aberto CSV

### Fase 10: Auditoria de Segurança, Testes E2E e Polimento Final
- [ ] Testes automatizados unitários e de integração (pytest)
- [ ] Auditoria de isolamento multi-tenant
- [ ] Validação do modo offline e PWA
- [ ] Verificação de contraste sob luz solar intensa
- [ ] Manual operacional de deploy (Render / Railway)

---

## 3. Próximo Passo Recomendado

* **Próxima Fase:** **Fase 2 - Banco de Dados, Persistência e Isolamento Multi-tenant**.
* **Ação:** Em um novo chat ou iteração, iniciar a configuração do banco PostgreSQL local, implementação dos modelos SQLAlchemy (`Tenant`, `User`, `Property`, `Visit`, `Objection`, `Contact`, `Settings`, `Log`) e geração das migrações com Alembic.
