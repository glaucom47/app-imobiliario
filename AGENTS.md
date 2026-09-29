# AGENTS.md - Contexto Operacional para Inteligência Artificial (Modo Manutenção)

Este arquivo orienta a atuação de qualquer assistente de inteligência artificial ou desenvolvedor(a) neste repositório. O projeto **Fecho** (`fecho.pt`) encontra-se com todas as suas fases funcionais concluídas, auditadas e em **modo de manutenção e evolução contínua**.

---

## 1. Idioma e Comunicação

* Responda sempre em **português do Brasil**.
* Adote tom profissional, técnico, conciso e cuidadoso, atuando como arquiteto(a) e engenheiro(a) de software de excelência.

---

## 2. Protocolo Obrigatório para Mudanças Futuras

Todo agente de IA que atuar neste repositório DEVE seguir rigorosamente o seguinte protocolo:

```text
Antes de qualquer alteração:
1. Ler docs/MANUTENCAO.md.
2. Ler docs/FSD.md.
3. Ler docs/DESIGN.md, se a alteração envolver interface.
4. Ler docs/STATUS.md.
5. Ler docs/ERROS.md.
6. Entender o pedido do usuário.
7. Explicar o plano antes de alterar arquivos.

Depois de qualquer alteração:
1. Testar o que foi alterado (executar a suíte automatizada 'pytest -v').
2. Atualizar docs/STATUS.md.
3. Registrar erro e solução em docs/ERROS.md, se houver.
4. Fazer commit ou entregar os comandos para o usuário.
5. Explicar ao usuário como validar a entrega.
```

> **Aviso de integridade:**
> - Use sempre caminhos relativos à raiz do projeto.
> - Não transforme caminhos de documentação em links absolutos ou links `file:///`.
> - Não registre caminhos locais de máquinas específicas dentro deste arquivo.

---

## 3. Base Técnica e Arquitetura do Sistema

* **Nome do Sistema:** Fecho (`fecho.pt`)
* **Linguagem Backend:** Python (versão 3.11 ou superior) com tipagem estática e esquemas via Pydantic v2.
* **Framework Web:** FastAPI com servidor ASGI Uvicorn.
* **Banco de Dados:** PostgreSQL (versão 15 ou superior) como banco primário.
* **ORM e Migrações:** SQLAlchemy 2.0+ e Alembic.
* **Autenticação:** Bcrypt nativo (`rounds=12`) e JWT (`python-jose`) assinado com `HS256`.
* **Frontend:** HTML5 semântico, CSS3 com tokens do `docs/DESIGN.md` (*Editorial PropTech Luxury*), JavaScript puro moderno (Vanilla ES6+) e Bootstrap v5.3+ local, estruturados como Progressive Web App (PWA) instalável e com Service Worker offline (`static/sw.js`).
* **Arquitetura em Camadas (MVC / REST API / PWA):**
  - *Visão (View / PWA):* `static/` (HTML5, CSS3, JS Vanilla, `manifest.json`, `sw.js`);
  - *Controle (Controllers):* `app/controllers/` (Routers FastAPI com injeção de dependências e isolamento de tenant);
  - *Serviços (Service Layer):* `app/services/` (Lógica de negócio pura, orquestração e transições de estado);
  - *Persistência (Models & Schemas):* `app/models/` (SQLAlchemy) e `app/schemas/` (Pydantic);
  - *Middlewares Defensivos:* `app/middleware/security.py` (Headers de segurança, Rate Limiting em memória e Limitador de Payload).

---

## 4. Ambientes de Execução

* **Ambiente de Desenvolvimento Local:**
  - Python 3 em ambiente virtual (`venv`).
  - Servidor Uvicorn escutando em `http://localhost:8000`.
  - PostgreSQL na porta `5432` ou fallback resiliente para SQLite local (`database/fecho_dev.db`) com seed automático exclusivo para testes locais.
* **Ambiente de Testes:**
  - Suíte com mais de 100 testes automatizados via `pytest` e TestClient do FastAPI.
* **Ambiente de Produção:**
  - PaaS em nuvem (Render ou Railway) conectada ao GitHub, processo ASGI contínuo (`Procfile`), PostgreSQL gerenciado com SSL e certificado HTTPS para `fecho.pt`.
  - Guardrails ativos: sistema recusa inicialização se `SECRET_KEY` for insegura/padrão ou se houver tentativa de fallback para SQLite.

---

## 5. Resumo da Estrutura de Pastas

```text
├── app/
│   ├── main.py                     # Ponto de entrada ASGI FastAPI e montagem de rotas
│   ├── dependencies.py             # Injeção de dependências (auth, tenant, RBAC)
│   ├── controllers/                # Endpoints REST (auth, properties, visits, scripts, contacts, backoffice)
│   ├── services/                   # Lógica de negócio (auth, property, visit, script, contact, speech, export)
│   ├── models/                     # Entidades SQLAlchemy (tenant, user, property, visit, objection, contact, settings, log)
│   ├── schemas/                    # Contratos Pydantic de entrada e saída
│   └── middleware/                 # Segurança, rate limit e proteção contra DoS
├── config/                         # Configuração técnica em código (sem .env)
├── database/                       # Conexão, script de seed e migrações Alembic
├── logs/                           # Armazenamento de logs estruturados locais
├── static/                         # Shell PWA, assets, CSS e scripts frontend
│   ├── css/design-tokens.css       # Tokens visuais (Editorial PropTech Luxury)
│   ├── js/calculator.js            # Motor fiscal e de crédito 100% offline
│   ├── js/teleprompter.js          # Roteiros e teleprompter
│   ├── js/audio_recorder.js        # Gravação de voz de 30s
│   └── js/api.js                   # Cliente HTTP REST
├── tests/                          # Suíte de testes automatizados com pytest (101 testes)
├── alembic.ini                     # Configuração do Alembic
├── Procfile                        # Comando de inicialização PaaS
└── requirements.txt                # Dependências do Python
```

---

## 6. Comandos Principais

* **Ativar ambiente virtual:**
  - Windows: `.\venv\Scripts\Activate.ps1`
  - Linux/macOS: `source venv/bin/activate`
* **Instalar dependências:** `pip install -r requirements.txt`
* **Executar servidor de desenvolvimento:** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
* **Executar suíte de testes:** `pytest -v`
* **Gerar nova migração:** `alembic revision --autogenerate -m "descricao_da_migracao"`
* **Aplicar migrações:** `alembic upgrade head`
* **Verificar sintaxe JS:** `node -c static/js/*.js`

---

## 7. Diretrizes e Cuidados de Segurança Inegociáveis

1. **Isolamento Multi-tenant Obrigatório:** Todas as consultas, inserções e filtros devem aplicar obrigatoriamente `agencia_id`. O ID da agência deve vir unicamente do token JWT validado (`current_user.agencia_id`), nunca de parâmetros abertos de requisição.
2. **Prevenção Universal contra XSS:** No Vanilla JS, jamais interpole dados dinâmicos em `innerHTML` sem utilizar `escapeHtml(...)`.
3. **Prevenção contra SQL Injection:** Uso exclusivo da API expressa do SQLAlchemy ORM. É expressamente proibida a concatenação manual de strings em comandos SQL.
4. **Prevenção contra CSV Formula Injection:** Todas as exportações de relatórios em `export_service.py` devem prefixar com apóstrofo (`'`) células que iniciem com caracteres perigosos (`=`, `+`, `-`, `@`, `\t`, `\r`, `%`).
5. **Máquina de Estados de Imóveis:** O ciclo de vida do imóvel é estritamente: *Ativo* → *Reservado* → *Vendido*. A transição para *Vendido* exige imperativamente os 3 campos: *Nome do Comprador*, *Telemóvel* e *Data da Escritura*, bloqueando reversão posterior.
6. **Cálculos Fiscais 100% no Cliente:** As regras e tabelas de IMT (Continente/Ilhas, HPP/Secundária, IMT Jovem), Imposto do Selo e prestação bancária devem ser processadas no cliente via `static/js/calculator.js`, garantindo funcionamento offline.
7. **Proibição de Arquivos `.env`:** As configurações da aplicação residem em código protegido em `config/config.py` e variáveis seguras do painel PaaS. Nunca versione arquivos `.env` ou segredos no repositório.
8. **Proteção de Senhas:** Hashes Bcrypt irreversíveis (`rounds=12`). Proibido registrar senhas, tokens ou dados pessoais sensíveis nos logs.
9. **Controle de Acesso Baseado em Perfis (RBAC):** Consultores não podem acessar rotas de diretoria, auditoria, parametrizações da agência ou painel de backoffice (`require_diretor`).
10. **Conformidade com RGPD:** Suporte à rotina de anonimização ("Cliente Anonimizado") para expurgo de dados de compradores a pedido, preservando os registros de fechamento e auditoria da agência.

---

## 8. Cuidados para Não Quebrar o Sistema

* **Antes de alterar:** Consulte o manual `docs/MANUTENCAO.md` e o guia `docs/COMO-PEDIR-MUDANCAS.md`.
* **Não descaracterize a stack:** Não adicione frameworks pesados de frontend (React, Vue, Tailwind) ou bibliotecas de renderização pesada de PDF.
* **Teste sempre:** Nunca finalize uma tarefa sem executar `pytest -v` e garantir 100% de aprovação de todos os testes automatizados.
* **Atualize os arquivos vivos:** Toda alteração exige atualização em `docs/STATUS.md` e, caso ocorra algum imprevisto técnico, registro detalhado em `docs/ERROS.md`.
* **Versionamento limpo:** Verifique `git status` antes de commitar, garantindo que nenhum arquivo sensível ou temporário seja incluído.
