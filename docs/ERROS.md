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

