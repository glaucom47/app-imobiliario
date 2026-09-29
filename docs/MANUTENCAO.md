# MANUAL DE MANUTENÇÃO, OPERAÇÃO E EVOLUÇÃO - FECHO (fecho.pt)

Este documento é a referência definitiva para engenheiros de software e assistentes de Inteligência Artificial responsáveis por manter, corrigir, testar e evoluir o sistema **Fecho** (`fecho.pt`).

---

## 1. Visão Geral

### 1.1 O que o sistema faz
O **Fecho** é um assistente móvel e plataforma web especializada no setor imobiliário de Portugal (compra, venda e angariação). Ele elimina a necessidade de preenchimento de formulários densos de secretária através de automações de voz de 30 segundos, simulações financeiras e fiscais instantâneas em visita (IMT, Selo e Prestação Bancária) e teleprompter integrado para roteiros de marketing em vídeo. Na retaguarda, fornece à direção da agência métricas de assiduidade dos consultores e inteligência consolidada de mercado sobre as objeções acumuladas por imóvel, municiando o consultor e o broker com dados concretos para renegociar preços de venda com os proprietários.

### 1.2 Para quem foi criado
* **Consultores Imobiliários em Campo:** Operam pelo telemóvel durante visitas a imóveis, reuniões com clientes e deslocações externas.
* **Diretores Comerciais e Brokers de Agências:** Operam pelo computador ou tablet no escritório da agência através do painel de Backoffice.

### 1.3 Problemas que resolve
1. **Perda de feedback pós-visita:** O consultor costuma adiar o relato da visita por falta de tempo. No Fecho, grava uma nota de voz de 30 segundos logo após a visita, que é transcrita, categorizada e estruturada em feedback pronto para envio ao proprietário via WhatsApp com validação prévia (*Human-in-the-Loop*).
2. **Insegurança nos custos fiscais em visita:** Compradores hesitam em fazer propostas por não saberem o valor exato do IMT, Imposto do Selo e prestação bancária. A calculadora do Fecho calcula tudo instantaneamente no próprio telemóvel, 100% offline, considerando regimes Continente/Ilhas e isenções do IMT Jovem (DL n.º 48-A/2024).
3. **Dificuldade na produção de vídeos de marketing:** Falta de roteiro ou esquecimento de falas durante a gravação de vídeos curtos (Reels/Stories/WhatsApp). O Fecho gera scripts em 3 blocos (Gancho, 2 Destaques e CTA) e disponibiliza um teleprompter de alto contraste com rolagem temporizada no ecrã.
4. **Falta de acompanhamento no pós-venda:** O Fecho registra automaticamente compradores na transição do imóvel para "Vendido" e notifica o consultor às 09:00 no aniversário da celebração da escritura com mensagens relacionais prontas no WhatsApp.
5. **Dificuldade em convencer proprietários a baixar preço:** O painel de Backoffice compila e cruza todas as objeções reais relatadas nas visitas (ex.: "preço elevado para a zona", "ruído exterior", "falta de garagem"), gerando argumentos estatísticos irrefutáveis para renegociação de preços.

### 1.4 Módulos Principais
1. **Gestão de Carteira e Imóvel em Foco (`properties`):** Cadastro e seleção ágil do imóvel ativo com máquina de estados rigorosa (*Ativo* → *Reservado* → *Vendido*).
2. **Visitas e Feedback por Voz (`visits`):** Gravação de áudio de 30s, transcrição e estruturação automática de notas com extração de nível de interesse (1 a 5) e tags de objeção, revisão human-in-the-loop e Deep Link para WhatsApp do proprietário.
3. **Calculadora Visual de Viabilidade Financeira (`calculator`):** Motor fiscal e financeiro 100% client-side/offline em JavaScript puro para IMT (Continente, Madeira e Açores; HPP e Secundária), IMT Jovem, Imposto do Selo (0,8% aquisição e 0,6% crédito) e amortização pelo Sistema Price.
4. **Conteúdo e Scripts de Vídeo com Teleprompter (`scripts`):** Gerador de roteiros por objetivo comercial (*Angariação*, *Baixa de Preço*, *Open House*) e leitor de teleprompter com rolagem e contagem regressiva 3-2-1.
5. **Pós-Venda e Esfera de Influência (`contacts`):** Notificação de aniversário da escritura às 09:00, mensagens dinâmicas de WhatsApp em 1 clique e rotina de conformidade RGPD ("Cliente Anonimizado").
6. **Backoffice Web e Governança (`backoffice`):** Painel administrativo para diretores com rankings de visitas, gráfico consolidado de objeções por imóvel, catálogo padronizado de tags, parametrização remota de taxas financeiras e exportação CSV higienizada contra injeção de fórmulas.

---

## 2. Stack e Ambientes

### 2.1 Stack Tecnológica
* **Backend:** Python (versão 3.11 ou superior). Validação de dados e contratos via Pydantic v2.
* **Framework Web:** FastAPI com servidor ASGI Uvicorn.
* **Banco de Dados:** PostgreSQL (versão 15 ou superior) como banco primário.
* **ORM e Migrações:** SQLAlchemy 2.0+ com Alembic para versionamento de schema.
* **Autenticação e Criptografia:** `bcrypt` nativo (`rounds=12`) para hash de senhas e `python-jose[cryptography]` para emissão e validação de tokens JWT (`HS256`).
* **Frontend:** HTML5 semântico, CSS3 baseado nos tokens do `docs/DESIGN.md` (*Editorial PropTech Luxury*), JavaScript moderno (Vanilla ES6+) e Bootstrap v5.3+ empacotado localmente.
* **Arquitetura de Cliente:** Progressive Web App (PWA) instalável, Service Worker (`static/sw.js`) para suporte offline e Web App Manifest (`static/manifest.json`).

### 2.2 Ambientes
* **Ambiente Local (Desenvolvimento):**
  - Interpretador Python isolado em ambiente virtual (`venv`).
  - Uvicorn escutando em `http://localhost:8000` (ou `http://127.0.0.1:8000`).
  - PostgreSQL na porta 5432. Em desenvolvimento local, `database/connection.py` possui fallback automático e resiliente para SQLite local (`database/fecho_dev.db`) com seed automático caso o PostgreSQL local esteja inacessível.
* **Ambiente de Testes:**
  - Suíte automatizada com `pytest` e `httpx` (TestClient do FastAPI), executada localmente antes de commits.
* **Ambiente de Produção:**
  - Plataforma PaaS gerenciada em nuvem (**Render** ou **Railway**), com processo contínuo ASGI (`Procfile`), PostgreSQL gerenciado com SSL e certificado HTTPS para `fecho.pt`.
  - Configuração via variáveis de ambiente da plataforma PaaS (`ENVIRONMENT=production`, `SECRET_KEY`, `DATABASE_URL`).
  - Guardrails de segurança: em produção, o sistema recusa inicialização se `SECRET_KEY` for insegura/padrão ou se houver tentativa de fallback para SQLite.

### 2.3 Comandos Principais
| Ação | Comando |
|---|---|
| Ativar venv (Windows) | `.\venv\Scripts\Activate.ps1` |
| Ativar venv (Linux/macOS) | `source venv/bin/activate` |
| Instalar dependências | `pip install -r requirements.txt` |
| Iniciar servidor local | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| Executar suite de testes | `pytest -v` |
| Gerar nova migração | `alembic revision --autogenerate -m "descricao_da_migracao"` |
| Aplicar migrações | `alembic upgrade head` |
| Executar seed inicial | `python database/seed.py` |
| Validar sintaxe JS | `node -c static/js/*.js` |

---

## 3. Como Rodar Localmente

Siga o passo a passo para inicializar o ambiente de desenvolvimento local:

1. **Clonar ou abrir o repositório:**
   Abra o terminal na raiz do projeto (`c:\Projetos\app-imobiliario` ou equivalente).

2. **Ativar o ambiente virtual Python:**
   - No Windows PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - No Linux ou macOS:
     ```bash
     source venv/bin/activate
     ```

3. **Verificar ou atualizar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verificar a base de dados:**
   - Se possuir o PostgreSQL rodando localmente na porta 5432 com banco `fecho_db`, o sistema se conectará automaticamente.
   - Caso o PostgreSQL não esteja ativo, o sistema iniciará de forma resiliente usando o SQLite local (`database/fecho_dev.db`) com criação automática das tabelas e carga inicial de dados de demonstração.

5. **Iniciar o servidor de desenvolvimento:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Acessar a aplicação no navegador:**
   - **Interface Móvel (PWA para Consultores):** `http://localhost:8000/`
   - **Backoffice da Agência (Diretores/Brokers):** `http://localhost:8000/backoffice`
   - **Verificação de Saúde (Healthcheck):** `http://localhost:8000/health`

7. **Credenciais Padrão de Demonstração (Seed):**
   - **Diretora:** `diretora@fecho.pt` / `senha123` (acesso total ao mobile e ao backoffice)
   - **Consultor:** `consultor@fecho.pt` / `senha123` (acesso à operação móvel de campo; bloqueado no backoffice)

---

## 4. Mapa de Pastas e Arquivos

```text
├── app/
│   ├── main.py                     # Ponto de entrada ASGI, middlewares e montagem de rotas
│   ├── dependencies.py             # Injeção de dependências (auth, tenant, RBAC: require_diretor)
│   ├── controllers/                # Routers HTTP da API REST (Validação Pydantic e isolamento multi-tenant)
│   │   ├── auth_controller.py      # Login, refresh e me (/api/v1/auth)
│   │   ├── properties_controller.py# CRUD e transições de imóveis (/api/v1/properties)
│   │   ├── visits_controller.py    # Processamento de áudio e notas de visita (/api/v1/visits)
│   │   ├── scripts_controller.py   # Roteiros em 3 blocos para teleprompter (/api/v1/scripts)
│   │   ├── contacts_controller.py  # Pós-venda, esfera de influência e RGPD (/api/v1/contacts)
│   │   └── backoffice_controller.py# KPIs, métricas de objeções e exportação (/api/v1/backoffice)
│   ├── services/                   # Camada de regras de negócio
│   │   ├── auth_service.py         # Bcrypt rounds=12, JWT encode/decode
│   │   ├── property_service.py     # Máquina de estados (Ativo->Reservado->Vendido) e validações
│   │   ├── visit_service.py        # Registro de visitas e vínculo de objeções
│   │   ├── script_service.py       # Templates e geração de roteiros em 3 blocos
│   │   ├── contact_service.py      # Gestão de compradores, aniversários e anonimização RGPD
│   │   ├── speech_service.py       # Extração semântica de interesse (1-5) e tags de áudio
│   │   └── export_service.py       # Exportação CSV com sanitização contra formula injection
│   ├── models/                     # Entidades relacionais SQLAlchemy
│   │   ├── tenant.py               # Agência imobiliária (agencia_id)
│   │   ├── user.py                 # Usuários (roles: diretor, consultor)
│   │   ├── property.py             # Imóveis com máquina de estados e 3 campos de venda
│   │   ├── visit.py                # Visitas realizadas e nível de interesse
│   │   ├── objection.py            # Catálogo de tags (ObjectionTag) e vínculos (VisitObjection)
│   │   ├── contact.py              # Contatos de compradores pós-venda
│   │   ├── settings.py             # Parâmetros de taxas da agência
│   │   └── log.py                  # Trilha de auditoria (audit_logs)
│   ├── schemas/                    # Contratos de dados Pydantic (Request/Response)
│   │   ├── auth_schema.py
│   │   ├── property_schema.py
│   │   ├── visit_schema.py
│   │   ├── contact_schema.py
│   │   ├── script_schema.py
│   │   └── backoffice_schema.py
│   └── middleware/
│       └── security.py             # SecurityHeaders, RateLimiter (sliding window) e PayloadLimiter
├── config/
│   └── config.py                   # Configurações estruturais em código (sem .env)
├── database/
│   ├── connection.py               # Conexão SQLAlchemy, pool e fallback seguro em dev
│   ├── seed.py                     # Script de carga inicial de dados
│   └── migrations/                 # Migrações versionadas do Alembic
│       ├── env.py
│       └── versions/
├── static/                         # Frontend / Shell PWA da aplicação
│   ├── index.html                  # Shell da aplicação móvel (PWA)
│   ├── backoffice.html             # Shell do painel da direção / agência
│   ├── manifest.json               # Manifesto PWA instalável
│   ├── sw.js                       # Service Worker com cache e suporte offline
│   ├── css/
│   │   ├── design-tokens.css       # Tokens extraídos do DESIGN.md (Editorial PropTech Luxury)
│   │   └── style.css               # Estilos base, modais, gavetas e modo luz solar
│   ├── js/
│   │   ├── api.js                  # Cliente HTTP REST, gestão de tokens e endpoints
│   │   ├── app.js                  # Roteamento de tela móvel, eventos e sanitização XSS
│   │   ├── calculator.js           # Motor matemático fiscal 100% offline (IMT, Selo, Price)
│   │   ├── teleprompter.js         # Controle tátil de rolagem, contagem 3-2-1 e gerador offline
│   │   └── audio_recorder.js       # Captura de 30s de áudio e fila offline
│   └── img/
│       ├── screen.png              # Logotipo oficial (símbolo preto, ponto ouro, fecho.pt)
│       └── logo.png
├── tests/                          # Suíte automatizada de testes com pytest (101 testes)
├── alembic.ini                     # Configuração do Alembic
├── Procfile                        # Comando de inicialização para PaaS
├── render.yaml / railway.json      # Configurações de deploy em nuvem
└── requirements.txt                # Dependências fixadas do Python
```

### Guia de Manutenção por Pasta:
* **`app/controllers/`**: Alterar apenas ao adicionar novas rotas REST ou modificar parâmetros de endpoints. *Cuidado:* Nunca aceitar `agencia_id` via parâmetro; sempre injetar do JWT através de `current_user.agencia_id`.
* **`app/services/`**: Alterar para adicionar ou refinar regras de negócio, cálculos ou transições de estado. *Cuidado:* Manter os métodos puros e isolados de frameworks HTTP.
* **`app/models/` e `app/schemas/`**: Alterar ao adicionar novas entidades ou novos campos a cadastros existentes. *Cuidado:* Toda alteração em `models/` exige geração de migração no Alembic.
* **`static/js/calculator.js`**: Alterar apenas em caso de atualização legislativa dos escalões de IMT no Orçamento do Estado em Portugal. *Cuidado:* Manter 100% livre de dependências de rede e testar via `tests/test_calculator.py`.
* **`static/js/app.js` e `static/backoffice.html`**: Alterar ao modificar telas ou componentes de interface. *Cuidado:* Toda interpolação em `innerHTML` deve usar obrigatoriamente `escapeHtml(...)` para prevenir ataques de Cross-Site Scripting (XSS).

---

## 5. Banco de Dados e Persistência

### 5.1 Onde ficam as definições
* **Modelos SQLAlchemy:** Em `app/models/`.
* **Conexão e Sessões:** Em `database/connection.py`.
* **Migrações Alembic:** Em `database/migrations/versions/`.
* **Script de Seed:** Em `database/seed.py`.

### 5.2 Como criar e aplicar alterações de banco
1. Modifique ou adicione os campos no modelo correspondente em `app/models/` (ex.: `app/models/property.py`).
2. Se o campo for exposto na API, atualize o schema correspondente em `app/schemas/` (ex.: `app/schemas/property_schema.py`).
3. Gere o arquivo de migração do Alembic:
   ```bash
   alembic revision --autogenerate -m "adiciona_campo_x_em_properties"
   ```
4. Revise o arquivo gerado dentro de `database/migrations/versions/` para garantir que as alterações estão corretas.
5. Aplique a migração ao banco:
   ```bash
   alembic upgrade head
   ```

### 5.3 Cuidados Críticos
* **Isolamento Multi-tenant:** Toda nova tabela de negócio DEVE possuir a coluna `agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)`.
* **Índices de Performance:** Sempre criar índices em colunas utilizadas em filtros frequentes (`agencia_id`, `status`, `consultor_id`, `data_visita`, `data_escritura`).
* **Proteção de Integridade Referencial:** Não remover registros que possuam vínculos históricos; priorizar soft deletes ou status inativos.
* **Testes com SQLite:** Os testes automatizados utilizam SQLite em memória (`sqlite:///:memory:` com `StaticPool`). Evite tipos específicos de PostgreSQL sem tratamento (como colunas proprietárias não suportadas por dialetos genéricos).

---

## 6. Autenticação, Autorização e Usuários

### 6.1 Funcionamento do Login
1. O cliente envia `POST /api/v1/auth/login` com `email` e `password`.
2. O `auth_service.py` valida o usuário no banco de dados e verifica a senha com `bcrypt.checkpw`.
3. Se válido, emite um token JWT assinado com `HS256`, contendo:
   - `sub`: ID do usuário (`int`);
   - `agencia_id`: ID da agência contratante (`int`);
   - `role`: Perfil de acesso (`diretor` ou `consultor`);
   - `email`: E-mail corporativo;
   - `exp`: Timestamp de expiração.
4. O cliente armazena o token e o envia no cabeçalho `Authorization: Bearer <token>` em todas as requisições subsequentes.

### 6.2 Perfis de Acesso (RBAC)
* **`diretor` (Diretor / Broker):** Acesso irrestrito a todos os dados da agência, visualização de carteira global, acesso ao painel de Backoffice (`/backoffice`), consulta de rankings de assiduidade de consultores, gráficos consolidados de objeções, edição de tags corporativas e parametrização financeira.
* **`consultor` (Consultor Imobiliário):** Acesso à operação móvel de campo (carteira de imóveis, foco ativo, visitas com notas de voz, teleprompter, calculadora, contatos de pós-venda). Bloqueado de acessar qualquer rota administrativa ou de métricas da diretoria (`require_diretor` retorna HTTP 403 Forbidden).

### 6.3 Verificação de Permissões
As permissões são validadas através de dependências do FastAPI em `app/dependencies.py`:
```python
# Rota que exige qualquer usuário autenticado e ativo
@router.get("/exemplo")
def rota_comum(current_user: User = Depends(get_current_user)):
    ...

# Rota restrita exclusivamente a Diretores da agência
@router.get("/relatorio-geral")
def rota_diretoria(current_user: User = Depends(require_diretor)):
    ...
```

---

## 7. Como Adicionar uma Nova Tela

1. **Definir se a tela pertence ao PWA Móvel ou ao Backoffice Web:**
   - Telas operacionais de campo ficam em `static/index.html`.
   - Painéis analíticos da direção ficam em `static/backoffice.html`.
2. **Adicionar o container HTML:**
   - Crie a seção ou gaveta modal (`<div class="fecho-modal-overlay">...</div>`) com classes semânticas.
3. **Aplicar os tokens de design (`static/css/design-tokens.css` e `static/css/style.css`):**
   - Utilize cores estruturais (`#111111`, `#FFFFFF`, `#FBFBFB`, `#C5A880`, `#1D4ED8`).
   - Use fontes Plus Jakarta Sans e classes com números tabulares (`tnum`) para valores e contadores.
4. **Adicionar a lógica de controle no JavaScript (`static/js/app.js` ou script do backoffice):**
   - Registre os ouvintes de abertura e fechamento da tela.
   - Conecte as chamadas assíncronas ao `static/js/api.js`.
5. **Sanitização Obrigatória:**
   - Em qualquer renderização de dados do usuário via `innerHTML`, invoque `escapeHtml(dado)`.
6. **Atualizar a versão do Service Worker (`static/sw.js`):**
   - Incremente a constante `CACHE_NAME` (ex.: `fecho-static-v6`) para invalidar o cache dos clientes após publicar a nova tela.

---

## 8. Como Adicionar um Novo Campo a um Cadastro

Exemplo: Adicionar o campo `certificado_energetico` ao cadastro de Imóveis (`Property`).

1. **Atualizar o Modelo de Banco (`app/models/property.py`):**
   ```python
   certificado_energetico = Column(String(10), nullable=True, default=None)
   ```
2. **Atualizar os Schemas Pydantic (`app/schemas/property_schema.py`):**
   - Adicionar o campo opcional em `PropertyBase`, `PropertyCreate`, `PropertyUpdate` e `PropertyResponse`.
3. **Gerar e aplicar a migração Alembic:**
   ```bash
   alembic revision --autogenerate -m "adiciona_certificado_energetico_em_properties"
   alembic upgrade head
   ```
4. **Atualizar o Serviço (`app/services/property_service.py`):**
   - Garantir que o campo é tratado no `create_property` e `update_property` se houver regra de negócio específica.
5. **Atualizar o Formulário no Frontend (`static/index.html`):**
   - Adicionar o campo `<input>` ou `<select>` no modal de cadastro `#modal-new-property`.
6. **Atualizar a Coleta no JavaScript (`static/js/app.js`):**
   - Capturar o valor do campo ao submeter o formulário e enviar ao payload da API.
   - Adicionar a exibição do campo nos cards de listagem com `escapeHtml(property.certificado_energetico)`.
7. **Atualizar a Exportação CSV (`app/services/export_service.py`):**
   - Incluir a coluna correspondente no cabeçalho e nos dados de exportação, se aplicável.
8. **Atualizar e Executar os Testes Automatizados:**
   - Adicionar asserções em `tests/test_properties.py` e rodar `pytest -v`.

---

## 9. Como Adicionar ou Alterar uma Regra de Negócio

1. **Conferir o FSD (`docs/FSD.md`):** Verifique se a regra proposta não conflita com as diretrizes centrais do produto.
2. **Localizar o Serviço Específico (`app/services/`):**
   - Regras fiscais e financeiras de visita: `static/js/calculator.js`.
   - Máquina de estados de imóveis: `app/services/property_service.py`.
   - Regras de transcrição e tags de visita: `app/services/speech_service.py` e `visit_service.py`.
   - Regras de pós-venda, aniversários e RGPD: `app/services/contact_service.py`.
   - Regras de roteiros em 3 blocos: `app/services/script_service.py`.
3. **Modificar a Regra com Abordagem Defensiva:**
   - Trate sempre condições de contorno, campos nulos e entradas anômalas.
   - Emita exceções claras (`HTTPException` com códigos apropriados como 400 ou 422).
4. **Criar ou Ajustar Testes Unitários:**
   - Crie testes específicos em `tests/` cobrindo o cenário de sucesso e os cenários de erro e violação da regra.
5. **Rodar a Suíte de Testes:**
   - Execute `pytest -v` e confirme que a nova regra funciona e nenhum outro teste quebrou.

---

## 10. Como Testar Alterações

### 10.1 Execução de Testes Automatizados
O projeto conta com mais de 100 testes automatizados cobrindo autenticação, integridade de modelos, isolamento multi-tenant, regras fiscais, permissões RBAC, geração de scripts e resiliência.
Execute no terminal:
```bash
pytest -v
```
Critério de aceitação: 100% dos testes devem passar (`PASSED`). Nenhuma falha é tolerada.

### 10.2 Testes Manuais Recomendados por Fluxo
* **Fluxo de Autenticação:** Testar login como diretora e como consultor; validar que consultor é bloqueado no `/backoffice`.
* **Fluxo de Imóveis:** Criar imóvel ativo; transitar para "Reservado"; tentar transitar para "Vendido" sem os 3 campos (deve falhar); transitar com os 3 campos e confirmar que o contato foi gerado na esfera de influência.
* **Fluxo de Calculadora:** Simular compra de 300.000 € e 600.000 € em HPP e Secundária no Continente e Ilhas; verificar benefício do IMT Jovem; clicar em partilhar WhatsApp e conferir formatação.
* **Fluxo de Visita por Voz:** Simular gravação de áudio; validar tela de revisão; confirmar persistência e Deep Link de WhatsApp do proprietário.
* **Fluxo de Teleprompter:** Gerar roteiro de *Baixa de Preço*; iniciar contagem 3-2-1; testar rolagem e botão de cópia.
* **Fluxo de Backoffice:** Acessar `/backoffice`; verificar gráfico de objeções; testar exportação CSV e abrir o arquivo no Excel para verificar ausência de caracteres corrompidos.

### 10.3 Quando Atualizar `docs/ERROS.md`
Qualquer erro inesperado, exceção de biblioteca, problema de ambiente ou falha de teste cuja resolução demandou investigação DEVE ser registrado em `docs/ERROS.md` seguindo o modelo:
- **Sintoma:** Descrição e mensagem de erro.
- **Causa:** Causa raiz diagnosticada.
- **Solução aplicada:** O que foi modificado no código.
- **Como evitar no futuro:** Lição aprendida e boas práticas.

---

## 11. Cuidados Críticos de Segurança

Em qualquer manutenção ou evolução, os seguintes 10 pilares de segurança devem ser rigorosamente respeitados:

1. **Isolamento Multi-tenant Obrigatório:** Toda busca, inserção ou atualização no banco deve filtrar por `agencia_id`. Nunca confie no ID da agência passado pelo cliente; extraia-o exclusivamente do token JWT decodificado (`current_user.agencia_id`).
2. **Prevenção Universal contra XSS:** No Vanilla JS, jamais faça interpolação direta de variáveis dinâmicas em `innerHTML` sem usar `escapeHtml(...)`.
3. **Prevenção contra SQL Injection:** Utilize exclusivamente a API expressa do SQLAlchemy ORM. Nunca monte consultas concatenando strings SQL.
4. **Prevenção contra CSV Formula Injection:** Toda exportação de CSV em `export_service.py` deve prefixar com apóstrofo (`'`) células que iniciem com caracteres perigosos (`=`, `+`, `-`, `@`, `\t`, `\r`, `%`).
5. **Proteção de Senhas:** Utilizar exclusivamente `bcrypt` com custo 12. Nunca logar senhas em texto puro.
6. **Proteção de Segredos:** Proibido utilizar arquivos `.env`. As configurações residem em `config/config.py` e em variáveis do painel PaaS em produção. Nunca commitar chaves privadas ou tokens no repositório.
7. **Guardrails de Produção Ativos:** O sistema não deve inicializar em produção (`ENVIRONMENT=production`) se `SECRET_KEY` tiver menos de 32 caracteres ou for o valor default de desenvolvimento, e o fallback para SQLite é expressamente proibido.
8. **Rate Limiting e Proteção DoS:** Manter ativos os middlewares `RateLimitMiddleware` (com limite severo em `/api/v1/auth/login`) e `PayloadSizeLimiterMiddleware` contra esgotamento de memória.
9. **Cabeçalhos de Segurança HTTP:** Manter a injeção dos headers de segurança: CSP, HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` e `Cache-Control: no-store` em rotas da API.
10. **Conformidade com RGPD:** Manter suporte à funcionalidade de anonimização ("Cliente Anonimizado") para expurgo de dados de compradores a pedido, preservando os registros de fechamento e transações históricas da agência.

---

## 12. Como Registrar Progresso

Toda manutenção ou alteração futura no repositório deve obrigatoriamente:
1. Atualizar o checklist e o status da versão em `docs/STATUS.md`.
2. Registrar problemas e soluções encontrados em `docs/ERROS.md`.
3. Criar commit descritivo no Git.

---

## 13. O Que NÃO Fazer

* **NÃO** instale frameworks ou bibliotecas pesadas de frontend (como React, Angular, Vue ou Tailwind) que descaracterizem a arquitetura leve Vanilla JS + Bootstrap local definida no FSD.
* **NÃO** instale bibliotecas pesadas de renderização de PDF (como WeasyPrint ou wkhtmltopdf); todos os relatórios devem ser mantidos em formato aberto CSV.
* **NÃO** remova a filtragem por `agencia_id` sob pretexto de "simplificar consultas".
* **NÃO** remova as validações de transição de estado de imóveis (o fechamento para *Vendido* exige imperativamente os 3 campos: *Nome*, *Telemóvel* e *Data da Escritura*).
* **NÃO** crie arquivos `.env` contendo senhas ou segredos versionados.
* **NÃO** mova os cálculos de IMT e Selo para o backend; eles devem permanecer 100% no cliente (`calculator.js`) para garantir operação instantânea e offline.
* **NÃO** desative testes automatizados existentes para "passar o build rápido"; se um teste falhou, o código deve ser corrigido para honrar a especificação.
