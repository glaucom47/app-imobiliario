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
