# AGENTS.md - Contexto Operacional para Inteligência Artificial

Este arquivo orienta a atuação de qualquer assistente de inteligência artificial neste repositório. Ele resume o contexto técnico, arquitetural, os protocolos de trabalho e as regras de segurança aplicáveis ao projeto **Fecho** (`fecho.pt`).

---

## 1. Idioma e Comunicação

* Responda sempre em **português do Brasil**.
* Adote tom profissional, técnico, conciso e cuidadoso, atuando como arquiteto(a) e engenheiro(a) de software de excelência.

---

## 2. Protocolo dos Arquivos Vivos

Todo agente de IA que atuar neste repositório deve seguir obrigatoriamente o seguinte protocolo:

```text
Antes de iniciar qualquer trabalho:
1. Ler `docs/FSD.md`.
2. Ler `docs/DESIGN.md`.
3. Ler `docs/INSUMOS.md`.
4. Ler `docs/PLANO.md`.
5. Ler `docs/STATUS.md`.
6. Ler `docs/ERROS.md`.

Use sempre caminhos relativos à raiz do projeto.
Não transformar estes caminhos em links absolutos.
Não usar links `file:///`.
Não registrar caminhos locais da máquina atual dentro do `AGENTS.md`.

Ao terminar qualquer trabalho:
1. Atualizar `docs/STATUS.md`.
2. Registrar erros e soluções em `docs/ERROS.md`, se houver.
3. Informar ao usuário o que foi feito.
4. Informar como testar ou validar a entrega.
```

---

## 3. Base Técnica do Projeto

Baseada estritamente nas definições de `docs/FSD.md`:

* **Nome do Sistema:** Fecho (`fecho.pt`)
* **Linguagem Backend:** Python (versão 3.11 ou superior) com validação de tipagem estática e esquemas via Pydantic.
* **Framework Web:** FastAPI com servidor ASGI Uvicorn.
* **Banco de Dados:** PostgreSQL (versão 15 ou superior), com suporte a integridade relacional e JSONB.
* **ORM e Migrações:** SQLAlchemy para mapeamento objeto-relacional e Alembic para versionamento de migrações estruturais.
* **Autenticação e Criptografia:** `passlib[bcrypt]` para hashes de senhas e `python-jose[cryptography]` para emissão e validação de tokens JWT.
* **Frontend e Interface:** HTML5 semântico, CSS3 baseado nos tokens do `docs/DESIGN.md` (*Editorial PropTech Luxury*), JavaScript puro moderno (Vanilla ES6+) e Bootstrap v5.3+ local, estruturados como Progressive Web App (PWA) instalável.
* **Arquitetura:** Padrão em camadas inspirado no MVC adaptado para APIs REST assíncronas e PWA:
  - *Visão (View / PWA):* `static/` (HTML5, CSS3, JS Vanilla, `manifest.json`, `sw.js`);
  - *Controle (Controllers):* `app/controllers/` (Routers FastAPI com injeção de dependências e isolamento de tenant);
  - *Serviços (Service Layer):* `app/services/` (Lógica de negócio, orquestração e transições de estado);
  - *Persistência (Models & Schemas):* `app/models/` (SQLAlchemy) e `app/schemas/` (Pydantic).

---

## 4. Ambientes de Execução

* **Desenvolvimento Local:**
  - Interpretador Python 3 isolado em ambiente virtual (`venv`).
  - Servidor Uvicorn escutando em `http://localhost:8000`.
  - Banco de dados PostgreSQL rodando localmente na porta padrão `5432`.
* **Ambiente de Testes / Homologação:**
  - Execução local de suíte automatizada com `pytest` e TestClient antes de qualquer publicação.
* **Ambiente de Produção:**
  - Plataforma PaaS em nuvem (Render ou Railway), com processo contínuo ASGI, PostgreSQL gerenciado com backups automatizados e certificado SSL/HTTPS para o domínio `fecho.pt`.
  - Credenciais e segredos fornecidos exclusivamente via variáveis do painel da plataforma PaaS, sem versionamento de segredos no código.

---

## 5. Restrições Técnicas Cruciais

1. **Proibição de arquivos `.env`:** As configurações da aplicação residem em código protegido em `config/config.py`, carregadas internamente. Não utilize arquivos `.env` para credenciais da aplicação.
2. **Sem bibliotecas de renderização pesada em PDF:** Relatórios e exportações devem ser em formato aberto e leve (CSV).
3. **Cálculos fiscais 100% no cliente:** Os cálculos de IMT (Continente e Ilhas), Imposto do Selo (0,8%) e prestação bancária devem ser processados no cliente via JavaScript puro (`static/js/calculator.js`), garantindo funcionamento instantâneo e offline.
4. **Isolamento Multi-tenant Rigoroso:** Todas as tabelas de negócio e consultas devem conter e filtrar obrigatoriamente por `agencia_id`.
5. **Máquina de Estados de Imóveis:** O ciclo de vida do imóvel é estritamente: *Ativo* → *Reservado* → *Vendido*. A transição para *Vendido* exige os 3 campos: *Nome do Comprador*, *Telemóvel* e *Data da Escritura*.
6. **Escopo Delimitado:** Módulos de arrendamento habitacional, upload ou guarda de arquivos pesados, disparos diretos via WhatsApp Business API oficial e integrações bidirecionais externas com CRMs legados estão formalmente **fora de escopo**.

---

## 6. Estrutura de Pastas do Projeto

A organização de diretórios e arquivos portável é:

```text
├── app/
│   ├── __init__.py
│   ├── main.py                     # Ponto de entrada da aplicação ASGI FastAPI
│   ├── controllers/                # Routers HTTP / Endpoints da API REST
│   │   ├── __init__.py
│   │   ├── auth_controller.py
│   │   ├── properties_controller.py
│   │   ├── visits_controller.py
│   │   ├── scripts_controller.py
│   │   ├── contacts_controller.py
│   │   └── backoffice_controller.py
│   ├── services/                   # Regras de negócio, cálculos e integrações
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── property_service.py
│   │   ├── visit_service.py
│   │   ├── script_service.py
│   │   ├── contact_service.py
│   │   ├── speech_service.py
│   │   └── export_service.py
│   ├── models/                     # Entidades relacionais SQLAlchemy
│   │   ├── __init__.py
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── property.py
│   │   ├── visit.py
│   │   ├── objection.py
│   │   ├── contact.py
│   │   ├── settings.py
│   │   └── log.py
│   └── schemas/                    # Contratos de dados Pydantic (Request/Response)
│       ├── __init__.py
│       ├── auth_schema.py
│       ├── property_schema.py
│       ├── visit_schema.py
│       └── report_schema.py
├── config/                         # Configuração técnica em código (sem .env)
│   ├── __init__.py
│   └── config.py                   # Parâmetros estruturais, chaves de hash, tokens
├── database/                       # Persistência e migrações
│   ├── __init__.py
│   ├── connection.py               # Engine e sessões do PostgreSQL
│   └── migrations/                 # Controle de migrações estruturais (Alembic)
│       ├── env.py
│       └── versions/
├── logs/                           # Armazenamento de logs locais estruturados
│   └── .gitkeep
├── static/                         # Frontend / Shell PWA da aplicação
│   ├── index.html                  # Shell da aplicação móvel (PWA)
│   ├── backoffice.html             # Shell do painel da direção / agência
│   ├── manifest.json               # Manifesto PWA instalável
│   ├── sw.js                       # Service Worker para cache e modo offline
│   ├── css/
│   │   ├── design-tokens.css       # Tokens de design extraídos do DESIGN.md
│   │   └── style.css               # Estilos base da aplicação
│   ├── js/
│   │   ├── app.js                  # Inicialização e roteamento client-side
│   │   ├── calculator.js           # Motor matemático 100% offline (IMT, Selo, Price)
│   │   ├── teleprompter.js         # Controle tátil de rolagem e contagem 3-2-1
│   │   ├── audio_recorder.js       # Captura de 30s e controle de fila offline
│   │   └── api.js                  # Cliente HTTP para a API REST
│   └── img/
│       ├── screen.png              # Logotipo oficial (símbolo preto, ponto ouro, fecho.pt)
│       └── logo.png
├── tests/                          # Suíte de testes automatizados com pytest
│   └── __init__.py
├── alembic.ini                     # Arquivo de configuração do Alembic
├── requirements.txt                # Lista de dependências do Python
└── .gitignore                      # Proteção de arquivos sensíveis e cache
```

---

## 7. Comandos Principais do Projeto

* **Criar ambiente virtual:**
  ```bash
  python -m venv venv
  ```

* **Ativar ambiente virtual:**
  - No Windows (PowerShell):
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
  - No Linux / macOS:
    ```bash
    source venv/bin/activate
    ```

* **Instalar dependências:**
  ```bash
  pip install -r requirements.txt
  ```

* **Executar servidor de desenvolvimento:**
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

* **Gerar nova migração no banco de dados:**
  ```bash
  alembic revision --autogenerate -m "descricao_da_migracao"
  ```

* **Aplicar migrações ao banco de dados:**
  ```bash
  alembic upgrade head
  ```

* **Executar suíte de testes:**
  ```bash
  pytest -v
  ```

---

## 8. Diretrizes de Segurança

Para garantir a integridade dos dados das agências e dos clientes:

1. **Prevenção de SQL Injection:** Utilizar exclusivamente o ORM SQLAlchemy ou consultas expressas parametrizadas. Nunca concatenar strings em consultas SQL.
2. **Prevenção de XSS:** Higienização de dados na renderização do DOM em Vanilla JS, priorizando `textContent` e templates seguros em vez de `innerHTML` com entradas não tratadas.
3. **Proteção contra CSRF / CORS:** Configurar o middleware `CORSMiddleware` do FastAPI permitindo origens controladas e cabeçalhos autorizados.
4. **Armazenamento de Senhas:** Senhas devem ser salvas exclusivamente como hashes Bcrypt irreversíveis (`passlib[bcrypt]`), com fator de custo adequado.
5. **Autenticação e Sessão (JWT):** Tokens gerados via `python-jose` assinados com algoritmo HMAC-SHA256 (`HS256`), tempo de expiração curto e presença obrigatória de `sub` (ID do usuário) e `agencia_id`.
6. **Controle de Acesso Baseado em Perfis (RBAC):** Dependências do FastAPI (`require_diretor`, `require_consultor`) para validação de privilégios. Consultores não podem acessar rotas de auditoria, KPIs corporativos e parametrizações da agência.
7. **Isolamento Lógico Multi-tenant:** Toda query no banco de dados deve filtrar obrigatoriamente por `agencia_id`. Nunca expor ou aceitar `agencia_id` alterável pelo cliente via payload aberto; obter sempre do token JWT validado.
8. **Proteção de Dados Pessoais (RGPD):** Suporte à anonimização ("Cliente Anonimizado") para expurgo de dados pessoais de compradores sem quebra de integridade referencial de vendas e estatísticas da agência.
9. **Proteção de Segredos e Configurações:** Proibição de arquivos `.env`. As configurações residem em `config/config.py` e em variáveis de ambiente fornecidas pelo PaaS em produção. Nenhum segredo ou chave privada deve ser commitado no repositório.
10. **Logs Seguros:** Proibido registrar senhas, tokens JWT, dados bancários ou dados pessoais sensíveis nos logs da aplicação.

---

## 9. Padrões de Código e Boas Práticas

* **Clareza e Simplicidade:** Código legível, modular e coeso. Funções pequenas e com responsabilidade única.
* **Tipagem Estática:** Uso rigoroso de Type Hints do Python e esquemas Pydantic para validação na entrada e saída de dados.
* **Comentários:** Comentários úteis e objetivos em português do Brasil quando elucidarem regras de negócio complexas (como fórmulas de IMT).
* **Fidelidade ao Design:** Seguir estritamente `docs/DESIGN.md` em cores, tipografia (Plus Jakarta Sans com números tabulares `tnum`), espaçamentos e elevação. Não adicionar estilos divergentes do guia *Editorial PropTech Luxury*.
* **Sem Escopo Fantasma:** Não implementar funcionalidades não descritas em `docs/FSD.md`.
