# MANUAL OPERACIONAL DE DEPLOY CONTÍNUO (PAAS) - FECHO (fecho.pt)

Este manual estabelece as instruções definitivas para publicação, configuração e manutenção contínua da aplicação **Fecho** (`fecho.pt`) em plataformas gerenciadas em nuvem (**Render** ou **Railway**), conforme especificado em `docs/FSD.md` (Seção 4 e 5) e `AGENTS.md`.

---

## 1. Visão Geral da Arquitetura em Produção

* **Ponto de Entrada:** Servidor ASGI Uvicorn escutando na porta dinâmica `$PORT` fornecida pelo PaaS.
* **Backend:** FastAPI (Python 3.11+) com validação tipada via Pydantic e middlewares defensivos de segurança (CSP, HSTS, X-Frame-Options, Rate Limiting, Payload Limiter).
* **Banco de Dados:** PostgreSQL 15+ gerenciado, com backups automatizados diários, SSL obrigatório e pool de conexões.
* **Frontend / PWA:** Shell estático HTML5/CSS3/Vanilla JS servido pelo FastAPI e gerido por Service Worker (`static/sw.js`) para funcionamento 100% offline da calculadora fiscal e teleprompter.
* **Domínio Oficial:** `https://fecho.pt` e `https://www.fecho.pt` com terminação SSL/TLS (HTTPS) e renovação automática de certificados Let's Encrypt.
* **Localização dos Dados:** Região Europa / Frankfurt (Alemanha), assegurando conformidade com o Regulamento Geral sobre a Proteção de Dados (RGPD).
* **Política de Segredos:** **Proibição estrita de arquivos `.env`**. Todas as credenciais de banco, segredos JWT e parametrizações de ambiente são fornecidas exclusivamente através das variáveis de ambiente configuradas no painel da plataforma PaaS.

---

## 2. Parâmetros e Variáveis de Ambiente de Produção

As seguintes variáveis devem ser configuradas no painel de controle do PaaS (Render ou Railway):

| Variável | Valor Recomendado / Descrição | Obrigatória? |
|---|---|:---:|
| `ENVIRONMENT` | `production` | Sim |
| `DEBUG` | `false` | Sim |
| `DATABASE_URL` | String de conexão segura fornecida pelo banco gerenciado (`postgresql+psycopg2://usuario:senha@host:5432/fecho_db`) | Sim |
| `SECRET_KEY` | String aleatória de alta entropia com pelo menos 64 caracteres (ex: `openssl rand -hex 32`) | Sim |
| `ALGORITHM` | `HS256` | Não (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 horas de jornada de trabalho do consultor) | Não (default `480`) |
| `CORS_ORIGINS` | `https://fecho.pt,https://www.fecho.pt` | Sim |
| `RATE_LIMIT_ENABLED` | `true` | Sim |

---

## 3. Opção A: Publicação no Render (Recomendada)

O Render suporta infraestrutura como código (Blueprint) através do arquivo `render.yaml` já versionado na raiz do projeto.

### 3.1. Deploy Automatizado via Render Blueprint

1. Acesse o painel do [Render](https://dashboard.render.com/);
2. Clique em **New +** e selecione **Blueprint**;
3. Conecte sua conta do GitHub e selecione o repositório `glaucom47/app-imobiliario`;
4. O Render detectará automaticamente o arquivo `render.yaml`;
5. Defina a região como **Frankfurt (EU Central)**;
6. Clique em **Apply**. O Render provisionará:
   - Uma base de dados gerenciada **PostgreSQL 15** (`fecho-db`);
   - Um Web Service contínuo **Python 3** (`fecho-app`);
   - Gerará a variável `SECRET_KEY` aleatória e ligará automaticamente a `DATABASE_URL`.

### 3.2. Deploy Manual no Render (Passo a Passo)

Caso prefira configurar serviço a serviço:

#### Passo 1: Criar o Banco PostgreSQL Gerenciado
1. No painel do Render, clique em **New +** → **PostgreSQL**;
2. **Name:** `fecho-db`;
3. **Database:** `fecho_db`;
4. **User:** `fecho_user`;
5. **Region:** `Frankfurt (EU Central)`;
6. **PostgreSQL Version:** `15`;
7. Selecione o plano adequado e clique em **Create Database**;
8. Após a criação, copie o valor do campo **Internal Database URL**.

#### Passo 2: Criar o Web Service FastAPI
1. Clique em **New +** → **Web Service**;
2. Conecte o repositório `glaucom47/app-imobiliario` (branch `main`);
3. **Name:** `fecho-app`;
4. **Region:** `Frankfurt (EU Central)`;
5. **Environment:** `Python 3`;
6. **Build Command:**
   ```bash
   pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head
   ```
7. **Start Command:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
   ```
8. **Health Check Path:** `/health`;
9. Em **Advanced** → **Environment Variables**, cadastre as variáveis listadas na Seção 2:
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `false`
   - `DATABASE_URL`: cole a URL interna do banco (garantindo o prefixo `postgresql+psycopg2://`)
   - `SECRET_KEY`: insira chave criptográfica gerada
   - `CORS_ORIGINS`: `https://fecho.pt,https://www.fecho.pt`
   - `RATE_LIMIT_ENABLED`: `true`
10. Clique em **Create Web Service**.

#### Passo 3: Executar a Carga Inicial de Dados (Seed)
Após o primeiro deploy ser concluído com sucesso:
1. Abra a aba **Shell** do serviço no Render;
2. Execute o comando de seed:
   ```bash
   python database/seed.py
   ```
3. A agência padrão, usuários demo (Diretora e Consultor) e o catálogo de objeções serão persistidos no PostgreSQL de produção.

---

## 4. Opção B: Publicação no Railway

O Railway oferece provisionamento rápido baseado no arquivo `railway.json` ou `Procfile` do repositório.

### 4.1. Passo a Passo no Railway

1. Acesse o painel do [Railway](https://railway.app/);
2. Clique em **New Project** → **Deploy from GitHub repo**;
3. Selecione o repositório `glaucom47/app-imobiliario`;
4. No painel do projeto, clique em **+ New** → **Database** → **Add PostgreSQL**;
5. Clique no serviço da aplicação (Web Service):
   - Em **Settings** → **Build Command**, utilize:
     ```bash
     pip install -r requirements.txt
     ```
   - Em **Settings** → **Deploy**, certifique-se de que o comando de inicialização é:
     ```bash
     alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
     ```
   - Em **Variables**, configure:
     - `DATABASE_URL`: `${{Postgres.DATABASE_URL}}`
     - `ENVIRONMENT`: `production`
     - `DEBUG`: `false`
     - `SECRET_KEY`: `<chave-secreta-64-caracteres>`
     - `CORS_ORIGINS`: `https://fecho.pt,https://www.fecho.pt`
     - `RATE_LIMIT_ENABLED`: `true`
6. Após a conclusão do deploy, acesse o terminal do serviço via Railway CLI ou aba de terminal e execute:
   ```bash
   python database/seed.py
   ```

---

## 5. Configuração do Domínio Próprio (`fecho.pt`) e SSL

Para associar o domínio próprio `fecho.pt` na plataforma PaaS:

### 5.1. No Painel do Render / Railway
1. Vá na aba **Settings** → **Custom Domains**;
2. Adicione `fecho.pt` e `www.fecho.pt`;
3. A plataforma fornecerá os registros DNS de apontamento.

### 5.2. No Provedor de DNS (DNS.pt / Cloudflare / GoDaddy)
Configure os seguintes registros na zona DNS do domínio:

| Tipo | Nome (Host) | Valor (Destino) | TTL |
|---|---|---|:---:|
| **A / ALIAS / ANAME** | `@` (ou raiz) | IP fornecido pelo Render/Railway (ex: `216.24.57.1`) | Automático / 3600 |
| **CNAME** | `www` | `fecho-app.onrender.com` (ou alias Railway) | Automático / 3600 |

Após a propagação do DNS (geralmente entre 15 minutos e 2 horas), o certificado SSL/TLS será emitido e renovado automaticamente sem necessidade de intervenção manual.

---

## 6. Procedimento de Atualização Contínua (CI/CD)

1. Qualquer alteração ou nova funcionalidade desenvolvida localmente deve ter todos os testes automatizados validados antes do envio:
   ```powershell
   .\venv\Scripts\python -m pytest -v
   ```
2. Após aprovação de 100% dos testes, faça o commit e envie para a branch principal:
   ```bash
   git add .
   git commit -m "feat/fix: descricao da entrega"
   git push origin main
   ```
3. A plataforma PaaS (Render ou Railway) detectará o push via Webhook do GitHub, disparará a compilação, executará as migrações estruturais do Alembic (`alembic upgrade head`) e reiniciará os processos sem tempo de inatividade (*Zero-Downtime Rolling Update*).

---

## 7. Monitoramento, Saúde e Recuperação de Desastres

* **Sonda de Liveness e Readiness:** O endpoint `GET /health` responde `200 OK` com payload JSON contendo o status, nome do sistema, versão e ambiente.
* **Políticas de Backup:** Os bancos PostgreSQL gerenciados no Render/Railway efetuam cópias de segurança automáticas a cada 24 horas, retidas por 7 dias.
* **Backup Manual sob Demanda:**
  ```bash
  pg_dump -d "$DATABASE_URL" -Fc -f "fecho_backup_$(date +%Y%m%d_%H%M%S).dump"
  ```
* **Rollback de Emergência:** Caso um deploy introduza comportamento inesperado em produção:
  1. No painel do Render/Railway, acesse a aba **Deploys**;
  2. Localize o deploy anterior estável e clique em **Rollback to this deploy**;
  3. A plataforma reverterá a imagem do container imediatamente.
