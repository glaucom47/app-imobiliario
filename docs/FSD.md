# DOCUMENTO DE ESPECIFICAÇÃO FUNCIONAL (FSD)

## 1. Visão Geral

* **Nome do Sistema:** Fecho (`fecho.pt`)
* **Objetivo Principal:** Capacitar consultores imobiliários em atividade externa e diretores de agências em Portugal com um assistente móvel focado exclusivamente em compra, venda e angariação imobiliária, eliminando formulários densos de secretária através de notas de voz de 30 segundos, simulações fiscais e financeiras instantâneas em visita (IMT e Selo) e teleprompter de roteiros curtos de marketing, fornecendo à direção inteligência estatística de mercado sobre objeções acumuladas para fundamentar a renegociação de preços de venda com proprietários.
* **Resumo do Funcionamento:** O sistema atua em cinco áreas funcionais essenciais:
  1. *Visitas & Feedback por Voz:* Seleção obrigatória do imóvel ativo, gravação de áudio de até 30 segundos, transcrição e estruturação automática com extração de nível de interesse e tags de objeção, ecrã de revisão (*Human-in-the-Loop*) e disparo ao WhatsApp do proprietário via ligação direta (*Deep Link*);
  2. *Conteúdo & Scripts de Vídeo Curto:* Geração de roteiros de marketing em 3 blocos (Gancho, 2 Destaques e CTA) orientados pelo objetivo comercial (*Angariação*, *Baixa de Preço*, *Open House*), acoplados a um leitor de teleprompter para ensaio com rolagem temporizada e botão de cópia de texto;
  3. *Gestão da Esfera de Influência & Pós-Venda:* Recolha ágil de 3 campos ao transitar o imóvel para "Vendido" (*Nome do Comprador*, *Telemóvel* e *Data da Escritura*), notificação no telemóvel às 09:00 no dia de aniversário da celebração da escritura e envio de mensagens dinâmicas de relacionamento em 1 toque via WhatsApp;
  4. *Calculadora Visual de Viabilidade Financeira em Visita:* Motor matemático executado 100% no telemóvel (*client-side* / offline) para cálculo exato de IMT (regimes HPP e Secundária no Continente e Ilhas, contemplando isenção de IMT Jovem), 0,8% de Imposto do Selo e estimativa de prestação bancária (Sistema Price), com partilha estruturada no WhatsApp;
  5. *Gestão da Agência & Backoffice Web:* Painel administrativo web com KPIs de adesão e assiduidade dos consultores, gráfico consolidado de objeções por imóvel, catálogo corporativo padronizado de tags, parametrização remota de taxas financeiras e exportação em formato aberto CSV.
* **Público Usuário:** Consultores imobiliários em trabalho de campo e Diretores Comerciais / Brokers de agências imobiliárias em Portugal.
* **Contexto de Uso:** Operação em telemóveis pelos consultores durante visitas, deslocações de campo e contacto com clientes; e operação em computadores ou tablets pela direção no escritório da agência.
* **Observações Relevantes para Implementação:** O Fecho adota isolamento lógico multi-tenant rigoroso por agência (`agencia_id`). Módulos de arrendamento habitacional, upload ou guarda de arquivos pesados, disparo automático por WhatsApp Business API e integrações bidirecionais externas com CRMs legados estão formalmente fora de escopo.

---

## 2. Documentos do Projeto para Implementação

A IA codificadora deverá utilizar unicamente os seguintes documentos para a implementação integral do sistema:

- `docs/FSD.md` (este documento, que consolida de forma autossuficiente todas as regras de negócio, especificações funcionais e diretrizes arquiteturais);
- `docs/DESIGN.md` (guia estético *Editorial PropTech Luxury*, definindo a paleta de cores monocromática com toques minerais, contraste para luz solar intensa, tipografia Plus Jakarta Sans com números tabulares e ergonomia tátil para mobilidade).

Todas as decisões técnicas e funcionais necessárias para implementação estão consolidadas diretamente nas seções deste documento.

---

## 3. Stack Definida

* **Linguagem Backend:** Python (versão 3.11 ou superior) com validação de tipagem estática e esquemas via Pydantic.
* **Framework Web:** FastAPI com servidor ASGI Uvicorn, garantindo alta performance assíncrona e geração de contratos Swagger/OpenAPI.
* **Banco de Dados:** PostgreSQL (versão 15 ou superior), provendo consistência transacional relacional e suporte a dados semiestruturados (JSONB).
* **Tecnologias de Interface:** HTML5 semântico, CSS3 baseado nos tokens do `docs/DESIGN.md`, JavaScript puro moderno (Vanilla ES6+) e Bootstrap local (v5.3+), estruturados como Progressive Web App (PWA) instalável no ecrã inicial[cite: 3, 4].
* **Dependências Centrais do Backend:**
  - `fastapi` e `uvicorn[standard]` (servidor web e roteamento assíncrono);
  - `pydantic` (validação e tipagem de contratos de dados de entrada/saída);
  - `sqlalchemy` (ORM e mapeamento objeto-relacional);
  - `alembic` (gerenciamento e controle de migrações estruturais do banco de dados);
  - `passlib[bcrypt]` (geração e verificação de hashes de senhas corporativas);
  - `python-jose[cryptography]` (criação e assinatura de tokens JWT);
  - `psycopg2-binary` ou `asyncpg` (driver de comunicação com PostgreSQL).
* **Padrão Arquitetural:** Separação estruturada em camadas inspirada no padrão MVC para aplicações web orientadas a APIs REST assíncronas.
* **Restrições Técnicas:** 
  - Proibido o uso de arquivos de ambiente `.env` para credenciais da aplicação; as configurações devem residir em arquivos de código protegidos (`config/config.py`) carregados apenas internamente;
  - Ausência de bibliotecas de renderização pesada em PDF;
  - Todos os cálculos fiscais (IMT e Selo) devem ser processados no cliente via JavaScript puro.

---

## 4. Ambientes do Projeto

* **Ambiente de Desenvolvimento Local:** Execução nativa no ambiente do desenvolvedor com interpretador Python 3 isolado em ambiente virtual (`venv`), Uvicorn escutando em `http://localhost:8000` e banco de dados PostgreSQL rodando localmente na porta padrão `5432`.
* **Ambiente de Testes ou Homologação:** Não haverá ambiente formal dedicado na nuvem na primeira versão; todas as validações de rotas e testes funcionais serão realizados integralmente no ambiente local antes da publicação.
* **Ambiente de Produção:** Plataforma PaaS gerenciada em nuvem (**Render** ou **Railway**) conectada ao repositório de código, provendo processo contínuo ASGI para a API FastAPI, banco PostgreSQL gerenciado com backups automatizados e terminação de segurança SSL/HTTPS para o domínio próprio (`fecho.pt`).
* **Observações sobre Deploy:** Em produção, chaves secretas de JWT, credenciais de banco e parâmetros de APIs externas são fornecidos exclusivamente pelo painel do PaaS, sem versionamento de dados sensíveis no repositório de código.

---

## 5. Arquitetura do Sistema

A referência principal da raiz do projeto nos ambientes de desenvolvimento e hospedagem é:

`[Diretório do Projeto - Repositório]`

Este diretório representa a pasta raiz versionada no repositório. Tanto no ambiente de desenvolvimento local quanto nos servidores de deploy (PaaS como Render ou Railway), toda a execução da aplicação parte deste diretório raiz.

### Organização de Camadas (Padrão MVC para API REST / PWA)

1. **Camada de Visão (View / PWA):**
   - Arquivos estáticos contidos na pasta pública (`static/`), compostos por HTML5, CSS3 e JavaScript puro;
   - Contém o manifesto PWA (`manifest.json`) e o Service Worker (`sw.js`) para cache estático e funcionamento offline dos motores de cálculo e teleprompter;
   - Implementa a interface gráfica tátil alinhada ao `docs/DESIGN.md`.
2. **Camada de Controle (Controller / Routers):**
   - Endpoints HTTP implementados com FastAPI que recebem requisições, validam parâmetros contra esquemas Pydantic, injetam a sessão do usuário autenticado e filtram o contexto multi-tenant (`agencia_id`).
3. **Camada de Negócio e Serviços (Service Layer):**
   - Centraliza a lógica de aplicação: transição restrita dos estados de imóveis (*Ativo* → *Reservado* → *Vendido*), orquestração de transcrição de áudio, geração de scripts de vídeo em 3 blocos, cálculo de KPIs de assiduidade e rotina de anonimização RGPD ("Cliente Anonimizado").
4. **Camada de Modelo de Dados e Persistência (Model / Data Access):**
   - Entidades mapeadas no PostgreSQL via SQLAlchemy, gerenciando transações, chaves primárias, chaves estrangeiras, índices e integridade referencial.

### Sugestão de Estrutura de Diretórios

```text
[Diretório do Projeto - Repositório]/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Ponto de entrada da aplicação ASGI
│   ├── controllers/                # Routers HTTP / Endpoints da API REST
│   │   ├── __init__.py
│   │   ├── auth_controller.py
│   │   ├── properties_controller.py
│   │   ├── visits_controller.py
│   │   ├── scripts_controller.py
│   │   ├── contacts_controller.py
│   │   └── backoffice_controller.py
│   ├── services/                   # Lógica de negócio, regras e integrações
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── property_service.py
│   │   ├── visit_service.py
│   │   ├── script_service.py
│   │   ├── contact_service.py
│   │   ├── speech_service.py
│   │   └── export_service.py
│   ├── models/                     # Definição das tabelas SQLAlchemy
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
│   └── config.py                   # Parâmetros estruturais, SMTP, chaves de hash
├── database/                       # Migrações e inicialização
│   ├── migrations/                 # Scripts versionados de migrações (Alembic)
│   │   ├── env.py
│   │   └── versions/
│   └── connection.py               # Sessões do PostgreSQL
├── logs/                           # Logs em arquivo para contingência
│   └── .gitkeep
├── static/                         # Assets do Frontend / PWA
│   ├── index.html                  # Shell da aplicação móvel
│   ├── backoffice.html             # Shell do painel da direção
│   ├── manifest.json               # Configuração PWA
│   ├── sw.js                       # Service Worker para cache e modo offline
│   ├── css/
│   │   ├── design-tokens.css       # Tokens extraídos do DESIGN.md
│   │   └── style.css
│   └── js/
│       ├── app.js                  # Inicialização e roteamento client-side
│       ├── calculator.js           # Motor matemático 100% offline (IMT, Selo, Price)
│       ├── teleprompter.js         # Controle tátil de rolagem e contagem 3-2-1
│       ├── audio_recorder.js       # Captura de 30s e controle de fila offline
│       └── api.js                  # Cliente HTTP para a API REST
├── alembic.ini                     # Configuração do Alembic
└── requirements.txt                # Dependências do projeto