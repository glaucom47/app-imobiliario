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
- **Solução aplicada:** Identificação da necessidade de configuração de autor e solicitação ao usuário ou definição de credencial para o repositório.
- **Como evitar no futuro:** Sempre verificar a existência de `git config user.name` e `git config user.email` antes de disparar o primeiro commit de um repositório recém-inicializado.
