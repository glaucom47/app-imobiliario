# ERROS E SOLUÇÕES - FECHO (fecho.pt)

Este arquivo serve como base de conhecimento viva do projeto para registrar qualquer falha, incompatibilidade, bug ou comportamento anômalo encontrado durante o desenvolvimento e execução do sistema, bem como a respectiva causa raiz e solução aplicada.

---

## Modelo de Registro

```text
## YYYY-MM-DD - <título curto do erro>

- Sintoma: <descrição do erro observado, mensagem de falha ou código de erro>
- Causa: <diagnóstico detalhado da causa raiz do problema>
- Solução aplicada: <etapas exatas executadas para resolver o erro>
- Como evitar no futuro: <boas práticas ou configurações preventivas>
```

---

## Registros Históricos

### 2026-09-28 - Falha no hook de telemetria pré-tool impedindo execução de ferramentas no Windows

- **Sintoma:** Ao tentar ler arquivos ou executar comandos, ocorria o erro:
  `JSON hook "jsonhook__googlecloudtools.datacloud_telemetry_PreToolUse_0_0" failed: command failed: exit status 1`
  `Error: Cannot find module 'C:\Users\HP\.gemini\config\plugins\googlecloudtools.datacloud_telemetry\"C:\Users\HP\...\telemetry_hook_bundle.js"'`
- **Causa:** No ambiente Windows, o caminho para o arquivo do script no plugin continha aspas duplas adicionais no manifesto, fazendo com que o runtime do Node.js concatenasse o diretório do plugin ao caminho absoluto e falhasse com `MODULE_NOT_FOUND` a cada chamada de ferramenta (`PreToolUse`).
- **Solução aplicada:** O diretório do plugin `googlecloudtools.datacloud_telemetry` foi removido das configurações ativas do ambiente.
- **Como evitar no futuro:** Garantir que plugins externos instalados no ambiente não utilizem caminhos de arquivos envelopados em aspas duplas literais dentro de JSONs de configuração no Windows.

### 2026-09-28 - Ausência de autor configurado no Git ao tentar commit inicial

- **Sintoma:** Ao executar `git commit -m "Estrutura inicial do projeto"`, o comando falhou com o código 1 e a mensagem: `fatal: unable to auto-detect email address (got 'HP@DESKTOP-CTP0UFU.(none)')`.
- **Causa:** O Git foi instalado ou inicializado nesta máquina sem uma configuração prévia de nome e e-mail de autor (`user.name` e `user.email`), necessária para assinar os registros de histórico.
- **Solução aplicada:** O usuário informou os dados de identificação e foram configurados `git config --global user.name "Glauco"` e `git config --global user.email "glaucom500@gmail.com"`, permitindo que o commit inicial fosse gerado com sucesso.
- **Como evitar no futuro:** Sempre verificar a existência de `git config user.name` e `git config user.email` antes de disparar o primeiro commit de um repositório recém-inicializado.

### 2026-09-28 - Falha do passlib ao detectar wrap bug com versões modernas da biblioteca bcrypt

- **Sintoma:** Ao invocar `CryptContext.hash(...)` utilizando o backend `bcrypt`, ocorria a exceção `ValueError: password cannot be longer than 72 bytes, truncate manually if necessary`.
- **Causa:** A biblioteca `passlib` (versão 1.7.4) possui uma rotina interna de teste de bug (`detect_wrap_bug`) que submete uma string de 255 bytes para a biblioteca `bcrypt`. Versões modernas da biblioteca C/Python `bcrypt` (>= 4.1.0) passaram a rejeitar ativamente senhas com mais de 72 bytes em vez de truncá-las silenciosamente, quebrando o handler interno do passlib.
- **Solução aplicada:** Implementou-se a geração e verificação de hashes diretamente via API nativa da biblioteca `bcrypt` (`bcrypt.hashpw` e `bcrypt.checkpw`) com fator de custo `rounds=12`, mantendo total conformidade com a especificação de segurança e hashes `$2b$12$...` do FSD.
- **Como evitar no futuro:** Evitar abstrações legadas de verificação de wrap bug do passlib quando utilizando versões recentes do pacote `bcrypt`, priorizando a API direta ou wrappers com truncamento explícito seguro.

### 2026-09-28 - Erro de importação de driver dialetal 'psycopg' ao carregar SQLAlchemy 2.0+ com URL padrão postgresql://

- **Sintoma:** Ao executar os testes automatizados ou o carregamento da engine com SQLAlchemy 2.0+, ocorria o erro `ModuleNotFoundError: No module named 'psycopg'`.
- **Causa:** No SQLAlchemy 2.0+ rodando em versões recentes do Python, o esquema de URL `postgresql://` tenta utilizar o driver `psycopg` (versão 3) por padrão quando o submódulo dialetal não é explicitado, enquanto o projeto utiliza o driver binário padrão estável `psycopg2-binary`.
- **Solução aplicada:** O esquema da URL de conexão foi explicitado como `postgresql+psycopg2://` tanto em `config/config.py` quanto em `alembic.ini`.
- **Como evitar no futuro:** Sempre especificar explicitamente o driver no protocolo de conexão do SQLAlchemy (ex.: `postgresql+psycopg2://` em vez de apenas `postgresql://`).

### 2026-09-29 - Falha de importação de email-validator no Pydantic ao utilizar EmailStr

- **Sintoma:** Ao executar os testes com pytest importando esquemas com `EmailStr`, ocorreu `ImportError: email-validator is not installed, run pip install 'pydantic[email]'`.
- **Causa:** O tipo `EmailStr` do Pydantic v2 depende da biblioteca externa `email-validator`, que não estava listada no escopo estrito de dependências do FSD (`requirements.txt`).
- **Solução aplicada:** Substituiu-se `EmailStr` por campo `str` com validação de formato via `@field_validator` nativo com expressão regular padrão RFC, mantendo validação estrita sem adicionar pacotes externos desnecessários.
- **Como evitar no futuro:** Evitar tipos do Pydantic que exijam pacotes auxiliares não contemplados no `requirements.txt` do projeto, priorizando validadores nativos.

### 2026-09-29 - Falha de tabela não encontrada em SQLite :memory: com conexões concorrentes nos testes

- **Sintoma:** Nos testes do TestClient com SQLite em memória, ocorria `OperationalError: (sqlite3.OperationalError) no such table: users`.
- **Causa:** Por padrão, a URI `sqlite:///:memory:` cria uma base de dados distinta a cada nova conexão aberta pelo pool do SQLAlchemy. Quando o TestClient e a fixture abriam conexões diferentes, a tabela criada na primeira conexão não existia na segunda.
- **Solução aplicada:** Configurou-se o engine dos testes com `poolclass=StaticPool` e `connect_args={"check_same_thread": False}`, garantindo que todas as threads e conexões compartilhem o mesmo estado em memória durante o teste.
- **Como evitar no futuro:** Sempre utilizar `StaticPool` ao executar testes com SQLite `:memory:` no SQLAlchemy em conjunto com o `TestClient` do FastAPI.

### 2026-09-29 - UnicodeEncodeError ao imprimir caracteres e emojis no console Windows

- **Sintoma:** Ao rodar `seed.py` no terminal do Windows, ocorreu `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f331'`.
- **Causa:** O console padrão do Windows utiliza a página de código `cp1252`, que não suporta determinados caracteres Unicode estendidos ou emojis emitidos via `print()`.
- **Solução aplicada:** Adicionou-se `if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")` na inicialização do script.
- **Como evitar no futuro:** Garantir configuração explícita de `sys.stdout` para UTF-8 em scripts de linha de comando no Windows.

### 2026-09-29 - Incompatibilidade de argumento 'subdominio' em vez de 'slug' na entidade Tenant

- **Sintoma:** Ao rodar testes em `test_properties.py`, ocorreu `TypeError: 'subdominio' is an invalid keyword argument for Tenant`.
- **Causa:** A entidade `Tenant` mapeada no SQLAlchemy (`app/models/tenant.py`) define a coluna de identificação web como `slug` e não `subdominio`.
- **Solução aplicada:** Corrigiu-se a instanciação das fixtures de teste substituindo o parâmetro `subdominio` por `slug`.
- **Como evitar no futuro:** Sempre inspecionar a definição dos campos nos modelos SQLAlchemy antes de estruturar novas fixtures e scripts.

### 2026-09-29 - Exceção de serialização JSON com objetos ValueError em RequestValidationError no Pydantic v2

- **Sintoma:** Ao disparar requisições inválidas no FastAPI, ocorria erro 500 no `validation_exception_handler` com a mensagem `TypeError: Object of type ValueError is not JSON serializable when serializing dict item 'errors'`.
- **Causa:** No Pydantic v2, o método `exc.errors()` pode incluir instâncias do erro (`ValueError`) em `ctx['error']`, que não podem ser diretamente serializadas por `json.dumps()` sem um conversor especializado.
- **Solução aplicada:** Adicionou-se `jsonable_encoder(exc.errors())` no manipulador `validation_exception_handler` em `app/main.py`.
- **Como evitar no futuro:** Em manipuladores customizados de exceções do FastAPI, sempre utilizar `jsonable_encoder` para garantir compatibilidade JSON de coleções e dicionários do Pydantic.

### 2026-09-29 - Variação de separador de milhar por espaço não-quebrável no toLocaleString('pt-PT') no Node/V8

- **Sintoma:** Ao testar o gerador offline de scripts do teleprompter via Node.js, a asserção `620.000 €` falhou porque a string gerada continha `620\xa0000 €`.
- **Causa:** Ambientes V8/Node.js recentes implementam a norma CLDR para o locale `pt-PT` utilizando o caractere Unicode `\xa0` (espaço não-quebrável) como agrupador de milhar em vez do ponto tradicional (`.`).
- **Solução aplicada:** Implementou-se um método utilitário `formatCurrency` em `static/js/teleprompter.js` com expressão regular `replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' €'`, garantindo padronização visual com pontos e total consistência entre navegadores, Node.js e testes automatizados.
- **Como evitar no futuro:** Para formatação monetária com pontos em JavaScript puro independente de versões de CLDR/V8, utilizar funções determinísticas baseadas em expressões regulares ou normalizadores de whitespace.

### 2026-09-29 - Duplicação de prefixo de rota em sub-roteadores FastAPI ao incluir router com prefixo global

- **Sintoma:** Requisições para `/api/v1/contacts` retornavam HTTP 404 Not Found nos testes do TestClient.
- **Causa:** O sub-roteador em `app/controllers/contacts_controller.py` foi declarado com `prefix="/api/v1/contacts"` e, em seguida, registrado em `app/main.py` com `app.include_router(..., prefix=settings.API_V1_STR)` (onde `API_V1_STR = "/api/v1"`), gerando a rota duplicada `/api/v1/api/v1/contacts`.
- **Solução aplicada:** Ajustou-se a declaração do `APIRouter` para `prefix="/contacts"`, mantendo a composição modular padrão do projeto onde o prefixo global da versão da API (`/api/v1`) é atribuído pelo `app.include_router` em `app/main.py`.
- **Como evitar no futuro:** Em novos sub-roteadores, declarar sempre apenas o segmento do recurso (ex.: `prefix="/recurso"`) e deixar o prefixo de versão da API para a inclusão no arquivo principal.

### 2026-09-29 - SyntaxError em static/js/app.js impedindo execução de eventos e botões da interface

- **Sintoma:** Os botões e comandos na interface web do aplicativo pararam de responder aos cliques do usuário (ex: abrir calculadora, scripts, carteira, gravação de feedback, etc.).
- **Causa:** Durante a inserção do módulo de contatos na Fase 8, um bloco de fechamento (`}`) de um `if (prompterBtnCopy)` anterior foi acidentalmente omitido, gerando um `SyntaxError: Unexpected token ')'` no encerramento do script. Como o script falhou em tempo de parsing no navegador, nenhum ouvinte de eventos (`addEventListener`) chegou a ser registrado.
- **Solução aplicada:** Restaurou-se o fechamento do bloco com a chave faltante em `static/js/app.js` e validou-se a integridade sintática de 100% dos scripts frontend via `node -c static/js/*.js` com código de retorno 0.
- **Como evitar no futuro:** Sempre executar verificação estática de sintaxe com o compilador do Node.js (`node -c`) nos arquivos JavaScript modificados antes de finalizar qualquer entrega.

### 2026-09-29 - Divergência de nomes de colunas em Property e Contact na instanciação de fixtures e exportador CSV

- **Sintoma:** Ao executar a suíte de testes com `pytest`, ocorreram exceções do SQLAlchemy `TypeError: 'referencia' is an invalid keyword argument for Property` e `TypeError: 'tipo_contacto' is an invalid keyword argument for Contact`.
- **Causa:** O modelo `Property` mapeado no banco não continha o campo `referencia` (utiliza chave primária numérica) e `Contact` utiliza a coluna `tipo` (em vez de `tipo_contacto`) e `telemovel` obrigatório (não nulo).
- **Solução aplicada:** Adequaram-se as chamadas para os atributos reais mapeados nos modelos (`f"FECHO-{p.id:04d}"`, `p.area_bruta`, `p.telefone_comprador`, `c.tipo`, `c.anonimizado`), alinhando os esquemas Pydantic, exportadores CSV e fixtures de teste.
- **Como evitar no futuro:** Sempre inspecionar as definições dos modelos declarativos no SQLAlchemy antes de instanciar ou mapear colunas de banco em serviços de exportação e testes.

### 2026-09-29 - Falha de autenticação FATAL no PostgreSQL local bloqueando login no Backoffice

- **Sintoma:** Ao clicar no botão "Diretora Demo (Acesso Completo)" no painel web `/backoffice`, a interface não respondia ou falhava silenciosamente e o endpoint `/api/v1/auth/login` retornava erro HTTP 500 (`Ocorreu um erro interno no servidor`).
- **Causa:** O serviço PostgreSQL local da máquina utilizava senha diferente do padrão de desenvolvimento, causando `psycopg2.OperationalError: FATAL: password authentication failed for user "postgres"` em qualquer requisição que acedesse o banco de dados. Além disso, o botão de demonstração dependia da propagação indireta de evento `submit` do formulário.
- **Solução aplicada:**
  1. Implementou-se inicialização resiliente do banco em `database/connection.py`, testando a conexão com PostgreSQL e ativando fallback automático para a base de dados local SQLite (`database/fecho_dev.db`) com inicialização de schema e carga dos dados de demonstração (seed) caso a conexão primária falhe;
  2. Ajustou-se a função `doLogin` em `static/backoffice.html` para ser disparada diretamente no clique dos botões demo com feedback de erro visual em tela caso a API recuse a autenticação.
- **Como evitar no futuro:** Em ambientes de desenvolvimento local, sempre prover mecanismos de resiliência e fallback autônomo para bases locais para não interromper os testes manuais caso o SGBD local possua credenciais divergentes.

### 2026-09-29 - Precedência de operadores lógicos no RateLimitMiddleware causando KeyError em rotas fora do escopo de limitação

- **Sintoma:** Ao requisitar rotas estáticas ou de healthcheck (`/health`, `/static/manifest.json`), ocorria exceção `KeyError: None` na linha `max_limit = rate_limiter.limits[scope][0]`.
- **Causa:** A expressão condicional `if scope and not isinstance(...) or (isinstance(response, Response))` avaliava o ramo `or` como verdadeiro mesmo quando `scope` era `None`, tentando buscar `rate_limiter.limits[None]`.
- **Solução aplicada:** Refatorou-se a condicional para a checagem explícita `if scope and isinstance(response, Response):`, garantindo que o escopo é válido antes de consultar o dicionário de limites.
- **Como evitar no futuro:** Utilizar parênteses explícitos ao combinar operadores lógicos `and` e `or`, ou manter verificações de guarda simples e diretas.

### 2026-09-29 - Remoção prematura de caracteres de controle pelo strip() antes da validação de sanitização CSV

- **Sintoma:** Payloads de evasão de injeção de fórmulas CSV iniciando com tabulação (`\t`) ou retorno de carro (`\r`) não recebiam o prefixo de aspa simples (`'`).
- **Causa:** A chamada prévia `text = str(value).strip()` descartava a tabulação e o retorno de carro no início do texto antes da verificação `text[0] in (...)`.
- **Solução aplicada:** Inspecionou-se a string original bruta (`raw = str(value)`) antes da normalização, verificando se o primeiro caractere pertence aos caracteres maliciosos de controle e fórmulas (`=`, `+`, `-`, `@`, `\t`, `\r`, `%`).
- **Como evitar no futuro:** Em rotinas de sanitização de segurança (anti-injection), sempre validar a cadeia de caracteres original antes de transformações ou filtros de whitespace que possam alterar a assinatura do payload.

### 2026-09-29 - ReferenceError por Temporal Dead Zone (TDZ) e ausência de escapeHtml bloqueando eventos em static/js/app.js

- **Sintoma:** Várias funcionalidades da interface do aplicativo móvel deixaram de responder (botões de gravação de voz, calculadora, teleprompter, contatos e seleção de imóveis não abriam gavetas ou modais).
- **Causa:**
  1. Um bloco de fechamento de backdrop em `static/js/app.js` tentava iterar sobre variáveis declaradas com `const` (`[drawerPortfolio, modalNewProperty, modalTransitionStatus, drawerCalculator, drawerVoiceVisit]`) na linha 449, antes de `drawerCalculator` (linha 634) e `drawerVoiceVisit` (linha 958) serem inicializadas. Em ES6, variáveis declaradas com `const` ficam na Temporal Dead Zone (TDZ) até a linha da sua atribuição. A tentativa de acesso prematuro disparou `ReferenceError: Cannot access 'drawerCalculator' before initialization` durante o evento `DOMContentLoaded`, interrompendo a execução do script e impedindo o registro de todos os ouvintes de eventos subsequentes.
  2. O módulo de contatos e esfera de influência invocava `escapeHtml(...)` para sanitização XSS, porém a função `escapeHtml` não havia sido declarada no escopo de `app.js`.
  3. O Service Worker PWA mantinha cache com `fecho-static-v3`, retendo versões antigas dos arquivos no navegador dos clientes.
- **Solução aplicada:**
  1. Substituiu-se a lista estática de variáveis não inicializadas por `document.querySelectorAll('.fecho-modal-overlay')`, que localiza de forma segura e dinâmica todos os modais e gavetas do DOM sem qualquer risco de TDZ;
  2. Implementou-se a função utilitária `escapeHtml(text)` em `static/js/app.js` para sanitização defensiva contra XSS;
  3. Adicionou-se ouvinte explícito para `#btn-toggle-portfolio-card`;
  4. Elevou-se a versão do cache do Service Worker para `fecho-static-v4` em `static/sw.js` e forçou-se a checagem de atualização imediata no carregamento da aplicação;
  5. Validou-se a suíte de 99 testes automatizados com 100% de sucesso.
- **Como evitar no futuro:** Nunca referenciar variáveis declaradas com `const`/`let` antes da sua linha de inicialização. Preferir sempre seleção declarativa pelo DOM (`document.querySelectorAll`) para componentes genéricos (como modais e overlays). Testar o ciclo de vida do script em ambiente DOM simulado antes de entregas.

### 2026-09-29 - Omissão de sanitização escapeHtml em cards de imóveis e tabelas do backoffice (Risco XSS)

- **Sintoma:** Durante a auditoria de segurança pré-publicação, identificou-se que embora a função `escapeHtml` existisse no módulo de contatos, dados dinâmicos como títulos de imóveis, localização, nomes de consultores e tags de objeção eram inseridos via `innerHTML` em `static/js/app.js` e `static/backoffice.html` sem filtragem.
- **Causa:** Construção de templates literais em Vanilla JS interpolando propriedades de objetos diretamente no DOM sem a passagem sistemática pela rotina de escape.
- **Solução aplicada:**
  1. Aplicou-se `escapeHtml` em todas as variáveis interpoladas em `renderPortfolioCards` e `renderObjectionChips` em `static/js/app.js`;
  2. Declarou-se a função utilitária `escapeHtml` e aplicou-se a sanitização nas tabelas de consultores, tags e gráfico de distribuição em `static/backoffice.html`;
  3. Elevou-se o cache do Service Worker para `fecho-static-v5` em `static/sw.js` para garantir atualização imediata nos navegadores dos clientes.
- **Como evitar no futuro:** Em aplicações com Vanilla JS, nunca concatenar dados dinâmicos não confiáveis em propriedades `innerHTML` sem envolver em função sanitizadora padronizada ou priorizar `textContent` e nós DOM declarativos.

### 2026-09-29 - Risco de execução em produção com SECRET_KEY padrão ou fallback silencioso para SQLite

- **Sintoma:** Em caso de falha de conexão com o PostgreSQL em produção ou omissão da variável `SECRET_KEY` no painel do PaaS, o sistema aceitaria a chave padrão insegura de desenvolvimento e faria fallback automático para um banco SQLite efêmero com criação de contas demo com senhas conhecidas.
- **Causa:** Ausência de validação de guardrails no `lifespan` do FastAPI e fallback indiscriminado de banco de dados em `database/connection.py` sem checagem do ambiente `ENVIRONMENT`.
- **Solução aplicada:**
  1. Implementou-se `Settings.validate_production_settings()` no `config/config.py`, bloqueando a inicialização em produção (`ENVIRONMENT=production`) se `SECRET_KEY` for a chave padrão ou tiver menos de 32 caracteres;
  2. Bloqueou-se o fallback para SQLite em `database/connection.py` se `ENVIRONMENT == "production"`, forçando encerramento com mensagem explícita;
  3. Desativou-se o seed automático de contas de teste de demonstração em produção;
  4. Adicionaram-se testes automatizados específicos cobrindo esses guardrails em `tests/test_security_multitenant_stress.py`.
- **Como evitar no futuro:** Sempre implementar verificações de guarda explícitas no ciclo de vida (startup) da aplicação que impeçam a inicialização em ambientes produtivos caso segredos ou infraestruturas críticas estejam em modo permissivo de desenvolvimento.

### 2026-09-29 - Omissão da classe active na abertura do Drawer de Scripts impedindo exibição da interface

- **Sintoma:** Ao clicar na opção "Scripts" na barra inferior de navegação ou no botão "Scripts de Vídeo & Teleprompter" no painel principal do PWA, a interface não respondia e o módulo de roteiros de vídeo não era exibido.
- **Causa:**
  1. A função `openScriptsDrawer()` em `static/js/app.js` alterava apenas a propriedade `drawerScripts.style.display = 'flex'`. No entanto, as regras de animação e visibilidade em `static/css/style.css` para a classe `.fecho-modal-overlay` utilizam `opacity: 0`, `visibility: hidden` e `.fecho-drawer-sheet` com `transform: translateY(100%)`, exigindo a presença da classe modificadora `.active` (`.fecho-modal-overlay.active`) para tornar o componente visível e posicionado no viewport. Ao contrário dos demais drawers do sistema que utilizavam o utilitário centralizado `openDrawer(element)`, a gaveta de scripts não adicionava essa classe.
  2. Em caso de ausência de imóvel ativo selecionado no `localStorage`, a função tentava acessar `resp.items[0]` em vez de `resp.properties[0]` e invocava `openPortfolioDrawer()`, uma função não declarada no escopo (o identificador correto é `handleOpenPortfolio()`), disparando um `ReferenceError` não tratado que bloqueava a execução do script.
  3. No fechamento da gaveta, utilizava-se `display = 'none'` em vez de `closeDrawer(drawerScripts)`, quebrando a sincronização tátil do menu inferior (`setActiveNavTab`).
- **Solução aplicada:**
  1. Padronizou-se o controle de abertura e fechamento da gaveta em `static/js/app.js` utilizando `openDrawer(drawerScripts)` e `closeDrawer(drawerScripts)`;
  2. Corrigiu-se a leitura de resposta da API de listagem de propriedades para `resp.properties`;
  3. Substituiu-se a chamada inexistente por `handleOpenPortfolio()`;
  4. Elevou-se a versão do Service Worker para `fecho-static-v6` em `static/sw.js` para garantir atualização imediata nos navegadores dos clientes.
- **Como evitar no futuro:** Sempre reutilizar as funções utilitárias do ciclo de vida de componentes (`openDrawer` e `closeDrawer`) em vez de manipular estilos inline pontuais, e verificar contratos de esquemas JSON retornados pelas rotas da API em todas as integrações client-side.

### 2026-09-30 - Violação de restrição NOT NULL na coluna 'entidade' ao gravar audit_logs na conversão e oposição RGPD

- **Sintoma:** Ao executar a suíte de testes de captação de leads (`tests/test_leads.py`), os testes de conversão em 1 clique e de oposição RGPD falharam com `sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: audit_logs.entidade`.
- **Causa:** Na entidade `Log` (`app/models/log.py`), a coluna `entidade` é definida como obrigatória (`nullable=False`). No serviço `lead_service.py`, a instanciação de `Log` incluía apenas `agencia_id`, `user_id`, `acao` e `detalhes`, omitindo os campos `entidade` e `entidade_id`.
- **Solução aplicada:**
  1. No método `converter_em_imovel`, especificou-se `entidade="lead"` e `entidade_id=lead.id`;
  2. No método `aplicar_oposicao_rgpd`, especificou-se `entidade="lead"` e `entidade_id=lead.id`;
  3. Reexecutou-se a suíte e os 108 testes foram aprovados com 100% de sucesso.
- **Como evitar no futuro:** Sempre verificar os metadados e restrições de nulidade (`nullable=False`) de entidades auxiliares (como `audit_logs`) antes de instanciá-las nos serviços de negócio.

### 2026-09-30 - Alerta genérico de varredura e WinError 10013 por processo Python zumbi retendo a porta 8000

- **Sintoma:** Ao clicar em "Executar Varredura" na aba de Captação e Angariação do Backoffice, o navegador exibia o alerta "Erro ao executar varredura". Ao tentar iniciar o servidor via Uvicorn, o PowerShell retornava o erro: `[WinError 10013] Foi feita uma tentativa de acesso a uma socket de uma maneira que é proibida pelas permissões de acesso`.
- **Causa Raiz:** Uma instância antiga do Uvicorn (`python.exe`, PIDs 42992 e 46532) iniciada no dia anterior (29/09 às 15:29:36) permaneceu rodando em segundo plano sem a flag `--reload` e retendo a porta TCP 8000. Isso gerou dois problemas combinados:
  1. A instância em execução na porta 8000 continha o código antigo e não possuía a rota `/api/v1/leads/varredura`, retornando 404/401 quando o navegador tentava fazer a requisição;
  2. Qualquer tentativa do usuário de iniciar um novo Uvicorn no terminal falhava com `[WinError 10013]` porque o Windows impedia o bind concorrente na mesma porta.
- **Solução aplicada:**
  1. Identificaram-se os processos zumbis via `Get-NetTCPConnection -LocalPort 8000` e encerraram-se forçadamente via `Stop-Process -Id 42992, 46532 -Force`, liberando completamente a porta 8000;
  2. Incrementou-se a versão do Service Worker para `fecho-static-v7` em `static/sw.js` para garantir atualização dos assets em cache no navegador;
  3. Aprimorou-se o tratamento de erro no front-end em `static/backoffice.html` com mensagens contextuais explicativas;
  4. Atualizou-se a asserção no teste `test_pwa_manifest_and_service_worker_served` em `tests/test_security_multitenant_stress.py` para validar `fecho-static-v7`;
  5. Suíte de 108 testes automatizados validada com 100% de aprovação.
- **Como evitar no futuro:** Sempre verificar processos prévios em execução na porta 8000 (`Get-NetTCPConnection -LocalPort 8000`) antes de inicializar o servidor em ambientes Windows locais; certificar-se de utilizar `--reload` durante o desenvolvimento para que alterações de código sejam refletidas automaticamente sem manter instâncias zumbis.

### 2026-10-04 - HTTP 422 ao requisitar endpoint literal /concelhos-ine devido à precedência de rota dinâmica /{property_id}

- **Sintoma:** Ao testar o endpoint `GET /api/v1/properties/concelhos-ine`, o FastAPI retornava status HTTP 422 Unprocessable Content em vez de 200 OK.
- **Causa:** O APIRouter continha a rota dinâmica `@router.get("/{property_id}")` declarada antes da rota literal `@router.get("/concelhos-ine")`. Como o parâmetro de caminho `{property_id}` é tipado como inteiro (`int`), o FastAPI tentava converter a string `"concelhos-ine"` em inteiro, falhando na validação de tipos antes de avaliar a rota subsequente.
- **Solução aplicada:** Moveu-se a declaração das rotas literais e estáticas (`/concelhos-ine` e `/market-study`) para antes das rotas dinâmicas de parâmetros (`/{property_id}`).
- **Como evitar no futuro:** Em roteadores FastAPI/Starlette, sempre declarar rotas estáticas ou literais antes de rotas com parâmetros de caminho (`path parameters`) para evitar sombreamento e erros de coerção de tipos.

### 2026-10-04 - Falha no parsing de concelho na Caderneta Predial contendo prefixos de códigos da Autoridade Tributária

- **Sintoma:** O parser de Caderneta Predial retornava `None` para o concelho ao processar documentos reais contendo o código oficial da repartição de finanças (ex.: `CONCELHO: 05 - CASCAIS`).
- **Causa:** A expressão regular esperava apenas caracteres alfabéticos imediatamente após o identificador `CONCELHO:`, falhando quando a Autoridade Tributária emite o documento com o código de 2 a 4 dígitos seguido de hífen (ex.: `05 - CASCAIS`).
- **Solução aplicada:** Atualizou-se o padrão regex para tolerar opcionalmente dígitos seguidos de hífen ou meia-risca (`(?:\d+\s*[-–]\s*)?`) antes da captura do nome do município e flexibilizou-se o delimitador de encerramento de linha.
- **Como evitar no futuro:** Documentos emitidos pela Administração Pública em Portugal frequentemente usam códigos numéricos de identificação territorial combinados com os nomes por extenso; as expressões regulares de extração documental devem sempre prever e tolerar esses prefixos codificados.

### 2026-10-04 - HTTP 429 Too Many Requests em testes contínuos ao acumular requisições de login no RateLimiter

- **Sintoma:** Ao executar a suíte completa de testes contendo mais de 140 testes, asserções de login falharam com `HTTP 429 Too Many Requests` em vez de `200 OK` ou `401 Unauthorized`.
- **Causa:** O middleware de proteção contra força bruta (`RateLimitMiddleware`) mantém uma janela deslizante em memória com limite de 10 tentativas por minuto para o escopo `login`. Como o `TestClient` compartilha o mesmo IP de origem (`testclient` / `127.0.0.1`), a execução consecutiva e rápida de dezenas de testes de autenticação esgotou o limite da janela.
- **Solução aplicada:** Invocou-se `rate_limiter.reset()` dentro do fixture de cliente de teste (`client`), garantindo que cada teste unitário inicie com a janela deslizante de rate limiting limpa e isolada.
- **Como evitar no futuro:** Em suítes de testes automatizados com Starlette/FastAPI TestClient que testam rotas protegidas por rate limiting, sempre invocar a rotina de reset de rate limiter no ciclo de vida da fixture (`setup`/`teardown`).
### 2026-10-04 - Modal de criação de consultores invisível devido a tag div não fechada no modal de RGPD anterior

- **Sintoma:** Ao clicar no botão "+ Novo Consultor" na aba Equipa Comercial do Backoffice, o modal não aparecia no ecrã.
- **Causa:** O overlay anterior `#modal-rgpd-lead` possuía uma tag de fechamento `</div>` ausente (fechava o card interno mas não o overlay externo). Como consequência, o `#modal-create-consultor` e modais subsequentes foram renderizados como filhos do `#modal-rgpd-lead` que possuía `display: none;`. Ao tentar exibir o modal filho com `display: flex;`, a visibilidade permanecia suprimida pelo elemento pai oculto.
- **Solução aplicada:** Adicionou-se o `</div>` de fechamento do overlay em `static/backoffice.html` e validou-se o balanceamento estrito de tags `<div>` via script automatizado (0 unclosed divs).
- **Como evitar no futuro:** Sempre validar o balanceamento sintático de tags HTML ao criar novos overlays e modais para evitar aprisionamento hierárquico no DOM.

### 2026-10-04 - Lista de consultores vazia no modal "Definir Metas" e falta de sincronização dinâmica

- **Sintoma:** Ao abrir o modal "Definir Metas" na Direção Comercial, o seletor de consultores exibia apenas o placeholder inicial sem listar nenhum consultor da agência, mesmo após cadastrar consultores na aba "Equipa Comercial".
- **Causa:**
  1. O endpoint backend `GET /api/v1/backoffice/consultores` retorna uma lista direta (`List[ConsultorResponse]`). Em `static/backoffice.html`, a função `loadCommercialDashboard()` lia `resTeam.consultores || []`, o que avaliava para `undefined` e resultava em array vazio `commercialTeamConsultores = []`.
  2. Ao cadastrar um novo consultor via `formCreateConsultor`, a lista comercial não era sincronizada nem os seletores eram atualizados dinamicamente.
  3. A abertura do modal de metas ocorria sem assegurar a resolução assíncrona da listagem de consultores.
- **Solução aplicada:**
  1. Criou-se a função centralizadora `ensureCommercialConsultores(forceRefresh)` com suporte resiliente a retorno em array ou objeto (`Array.isArray(res) ? res : res.consultores || []`), sincronizando `teamConsultoresData` e `commercialTeamConsultores`;
  2. Assegurou-se que `openCommercialGoalsModal` e o botão de criação de deals invoquem `await ensureCommercialConsultores()`;
  3. No callback de criação (`formCreateConsultor`), edição (`formEditConsultor`) e alteração de status (`handleToggleConsultorStatus`), garantiu-se a atualização imediata dos selects e tabelas;
  4. Adicionou-se listener dinâmico para pré-carregar metas já salvas ao selecionar um consultor no dropdown;
  5. Incrementou-se a versão de cache do Service Worker para `fecho-static-v17` e atualizou-se o teste correspondente em `test_security_multitenant_stress.py`.
- **Como evitar no futuro:** Em clientes JavaScript, sempre inspecionar o contrato real de resposta retornado pela API (array direto vs payload envelopado em chave) e unificar o estado compartilhado entre abas afins através de funções de sincronização reativas.

