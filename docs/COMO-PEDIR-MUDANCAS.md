# GUIA PRÁTICO: COMO PEDIR MUDANÇAS PARA UMA IA - FECHO (fecho.pt)

Este guia foi elaborado para que qualquer pessoa (mesmo sem conhecimentos técnicos de programação) consiga solicitar melhorias, correções e novas funcionalidades para uma Inteligência Artificial de forma segura, evitando que o sistema seja quebrado.

---

## 1. Como Pedir Mudanças sem Medo

Para que a Inteligência Artificial trabalhe com precisão e segurança no projeto **Fecho**, siga estas 4 regras de ouro em qualquer conversa futura:

1. **Peça uma coisa de cada vez:** Evite pedir para a IA alterar o banco de dados, o visual e as regras de cálculo ao mesmo tempo. Divida pedidos grandes em passos menores.
2. **Exija que a IA leia a documentação antes de começar:** Isso impede que a IA invente bibliotecas ou tente recriar o sistema do zero com outra tecnologia.
3. **Peça para a IA explicar o plano antes de editar qualquer arquivo:** Você poderá conferir se ela entendeu exatamente o que você quer antes de aplicar alterações.
4. **Exija a execução dos testes automatizados (`pytest -v`) antes de concluir:** O sistema possui mais de 100 testes automatizados que garantem que nenhuma parte existente deixou de funcionar.

---

## 2. A Regra Obrigatória para Iniciar Qualquer Chat Futuro

Sempre que você abrir uma nova conversa com uma IA neste projeto, cole a seguinte instrução no início do seu pedido:

```text
Antes de começar qualquer alteração, leia obrigatoriamente nesta ordem:
1. docs/MANUTENCAO.md
2. docs/FSD.md
3. docs/DESIGN.md (se envolver interface visual)
4. docs/STATUS.md
5. docs/ERROS.md

Responda em português do Brasil, explique o seu plano detalhado e só depois edite os arquivos. Ao terminar, execute a suíte de testes com 'pytest -v' e atualize docs/STATUS.md.
```

---

## 3. Modelos de Prompts Prontos (Copie e Cole)

Abaixo estão 8 modelos de comandos específicos para as principais situações no sistema Fecho:

### Exemplo 1: Adicionar um Campo em um Cadastro
> **Cenário:** Você quer que o cadastro de imóveis passe a registrar a tipologia detalhada (ex: T1, T2, T3) ou a Certificação Energética (A+, A, B, C).
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Antes de iniciar, leia `docs/MANUTENCAO.md`, `docs/FSD.md`, `docs/STATUS.md` e `docs/ERROS.md`.
>
> Preciso adicionar o campo "Certificação Energética" (opções: A+, A, B, B-, C, D, E, F) no cadastro de Imóveis (`Property`).
>
> Siga este roteiro:
> 1. Atualize o modelo de dados em `app/models/property.py`.
> 2. Atualize os esquemas Pydantic em `app/schemas/property_schema.py`.
> 3. Gere uma migração com Alembic e aplique-a ao banco.
> 4. Adicione o campo no formulário de criação de imóveis no mobile (`static/index.html`).
> 5. Atualize o código em `static/js/app.js` para enviar o valor e exibi-lo nos cards de carteira com proteção contra XSS (`escapeHtml`).
> 6. Atualize a exportação CSV em `app/services/export_service.py`.
> 7. Adicione testes em `tests/test_properties.py` e garanta que `pytest -v` passe com 100% de sucesso.
> 8. Atualize `docs/STATUS.md`.
>
> Explique o plano antes de iniciar a alteração dos arquivos.
> ```

---

### Exemplo 2: Criar uma Nova Tela
> **Cenário:** Você quer criar uma tela de histórico de fechamentos e comissões da agência dentro do Backoffice da diretoria.
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Leia `docs/MANUTENCAO.md`, `docs/FSD.md`, `docs/DESIGN.md` e `docs/STATUS.md`.
>
> Preciso criar uma nova tela no Backoffice (`static/backoffice.html`) chamada "Histórico de Fechamentos".
>
> Requisitos:
> 1. Acesso restrito a usuários com perfil 'diretor' (use `require_diretor` no backend).
> 2. Exibir a listagem dos imóveis transitados para o estado "Vendido", com valor de venda, comprador, telemóvel e data da escritura.
> 3. Seguir estritamente o guia visual `docs/DESIGN.md`: cartões brancos com bordas finas, tipografia Plus Jakarta Sans e valores em euros alinhados à direita com números tabulares (`tnum`).
> 4. Toda renderização de texto no frontend deve usar a função `escapeHtml(...)`.
> 5. Crie testes automatizados em `tests/test_backoffice.py` e execute `pytest -v`.
> 6. Atualize `docs/STATUS.md`.
>
> Apresente o plano detalhado antes de modificar o código.
> ```

---

### Exemplo 3: Corrigir um Erro (Bug)
> **Cenário:** Um botão parou de responder ou uma mensagem de erro inesperada apareceu na tela.
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Leia `docs/MANUTENCAO.md`, `docs/STATUS.md` e `docs/ERROS.md`.
>
> Ocorreu o seguinte erro no sistema:
> [Cole aqui a mensagem de erro exata que apareceu no console do navegador ou no terminal]
>
> O erro aconteceu quando eu executei a seguinte ação:
> [Explique o que você clicou ou preencheu antes do erro acontecer]
>
> Sua missão:
> 1. Investigue a causa raiz do problema no código sem desativar proteções de segurança.
> 2. Se for um arquivo JavaScript, verifique a sintaxe com `node -c static/js/*.js` para garantir ausência de erros como TDZ ou variáveis não declaradas.
> 3. Execute `pytest -v` para certificar-se de que nada foi quebrado.
> 4. Registre o erro e a solução aplicada em `docs/ERROS.md` seguindo o modelo padrão.
> 5. Atualize `docs/STATUS.md`.
> ```

---

### Exemplo 4: Alterar uma Regra de Negócio
> **Cenário:** A legislação portuguesa mudou ou a agência quer alterar o horário padrão de envio das notificações de aniversário de escritura.
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Leia `docs/MANUTENCAO.md`, `docs/FSD.md` e `docs/STATUS.md`.
>
> Preciso alterar a regra de notificação de aniversários de escritura no módulo de pós-venda (`app/services/contact_service.py`):
> [Explique a nova regra de negócio de forma simples e clara]
>
> Cuidados:
> 1. Não altere o isolamento por agência (`agencia_id`).
> 2. Não quebre a máquina de estados que exige os 3 campos para imóveis "Vendidos".
> 3. Atualize os testes automatizados em `tests/test_contacts.py`.
> 4. Execute `pytest -v` e confirme que todos os testes foram aprovados.
> 5. Atualize `docs/STATUS.md`.
>
> Explique os impactos da alteração antes de editar.
> ```

---

### Exemplo 5: Ajustar Visual Conforme o `docs/DESIGN.md`
> **Cenário:** Um botão, cartão ou texto ficou com visual desalinhado em relação ao estilo *Editorial PropTech Luxury*.
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Leia `docs/DESIGN.md` e `docs/MANUTENCAO.md`.
>
> Preciso ajustar o visual do componente [Nome do componente ou tela, ex: Card de Imóvel em Foco].
>
> Diretrizes obrigatórias:
> 1. Use unicamente as cores do design system: fundo Warm Alabaster (`#FBFBFB`), cartões brancos puros (`#FFFFFF`), bordas ultra-finas de 1px (`#EAEAEA`) e texto Deep Onyx (`#111111`).
> 2. Aplique fonte Plus Jakarta Sans com números tabulares (`tnum`) em todos os valores monetários em euros (€).
> 3. Mantenha suporte ao modo de alto contraste para luz solar intensa (`.sunlight-mode`).
> 4. Não instale frameworks externos pesados de CSS; utilize as variáveis declaradas em `static/css/design-tokens.css`.
> 5. Não altere a lógica de funcionamento ou os identificadores (IDs) dos elementos.
> ```

---

### Exemplo 6: Criar um Relatório ou Filtro
> **Cenário:** A agência deseja filtrar a carteira de imóveis por faixa de preço ou exportar um relatório de visitas em formato CSV.
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Leia `docs/MANUTENCAO.md`, `docs/FSD.md` e `docs/STATUS.md`.
>
> Preciso criar um novo filtro na tela de carteira de imóveis do mobile para filtrar por faixa de preço (ex: até 250k€, 250k€ a 500k€, acima de 500k€).
>
> Regras:
> 1. A filtragem deve respeitar o isolamento multi-tenant da agência autenticada.
> 2. O filtro deve responder de forma rápida no telemóvel.
> 3. Toda renderização no DOM deve continuar protegida com `escapeHtml`.
> 4. Crie testes para esse filtro em `tests/test_properties.py`.
> 5. Execute `pytest -v` e garanta que 100% dos testes passam.
> 6. Atualize `docs/STATUS.md`.
> ```

---

### Exemplo 7: Revisar Segurança Depois de uma Mudança
> **Cenário:** Você fez várias modificações no sistema e quer ter certeza de que nenhuma vulnerabilidade ou vazamento de dados foi introduzido.
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Leia `docs/MANUTENCAO.md`, `docs/STATUS.md` e a seção de segurança de `docs/FSD.md`.
>
> Faça uma auditoria defensiva de segurança nas alterações recentes do repositório.
>
> Verifique obrigatoriamente:
> 1. Se todas as consultas no banco de dados continuam filtrando por `agencia_id`.
> 2. Se há qualquer uso de `innerHTML` sem envolver variáveis em `escapeHtml(...)`.
> 3. Se as exportações CSV continuam sanitizando células contra Formula Injection.
> 4. Se não foi criado acidentalmente nenhum arquivo `.env` ou chaves privadas no código.
> 5. Execute a suíte de testes de estresse com `pytest -v tests/test_security_multitenant_stress.py`.
> 6. Apresente um resumo dos itens verificados e confirme se o sistema permanece blindado.
> ```

---

### Exemplo 8: Preparar uma Alteração para Commit
> **Cenário:** A alteração foi concluída, testada e você quer salvar o progresso no controle de versão Git.
>
> **Prompt para copiar:**
> ```text
> Responda em português do Brasil.
>
> Todas as alterações foram finalizadas e testadas.
>
> Por favor:
> 1. Verifique o status dos arquivos com `git status`.
> 2. Confirme que nenhum segredo, arquivo `.env` ou arquivo temporário será versionado.
> 3. Atualize `docs/STATUS.md` com o resumo do que foi entregue.
> 4. Crie o commit com uma mensagem clara e em português do Brasil (ex: 'Adiciona filtro por faixa de preço na carteira de imóveis').
> 5. Forneça o comando para eu executar `git push` no terminal.
> ```

---

## 4. Checklist Antes de Aceitar Qualquer Alteração

Antes de dar uma tarefa por concluída, faça este teste rápido de 5 minutos:

- [ ] **A IA executou os testes automatizados?** A resposta deve conter o resultado de `pytest -v` com 100% dos testes aprovados (`PASSED`).
- [ ] **A IA atualizou o `docs/STATUS.md`?** O arquivo deve conter a data e a descrição do que foi alterado.
- [ ] **Se houve erro durante o processo, foi registrado em `docs/ERROS.md`?**
- [ ] **O sistema abre sem erros no navegador?** Abra `http://localhost:8000/` e o console do navegador (F12) para checar se há erros em vermelho.
- [ ] **O design foi respeitado?** Os cartões, fontes e botões continuam elegantes e sem quebra de alinhamento.
- [ ] **Nenhum arquivo com senhas ou `.env` foi criado?**
