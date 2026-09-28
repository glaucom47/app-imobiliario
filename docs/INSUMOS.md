# Inventário de Insumos do Projeto

Este documento cataloga todos os arquivos presentes na pasta `docs/` do projeto **Fecho**, identificando a sua natureza, se serão consumidos em tempo de execução pela aplicação e o local provável de utilização.

> **Nota:** A pasta `docs/` é estritamente uma pasta de documentação e apoio. Arquivos que precisem ser servidos pela aplicação em execução (como imagens, logos e ícones) deverão ser copiados posteriormente para a pasta pública de assets (`static/`) definida pela arquitetura no momento da construção do frontend.

---

## Inventário de insumos do projeto

| Arquivo | O que é | Usado pelo sistema em execução? | Onde será usado | Observações |
|---|---|---|---|---|
| `docs/FSD.md` | Documento de Especificação Funcional e Técnica da aplicação | Não | Documentação | Define escopo, arquitetura, stack (Python/FastAPI/PostgreSQL), entidades e regras de negócio. |
| `docs/DESIGN.md` | Guia de Design System (*Editorial PropTech Luxury*) | Não | Documentação / Referência visual | Define tokens CSS (cores, tipografia Plus Jakarta Sans, espaçamentos, elevação e componentes). |
| `docs/screen.png` | Logotipo oficial do produto com ícone "F." e marca "fecho.pt" | Sim (a ser copiado para `static/img/` na construção) | Cabeçalho, tela de login, manifesto PWA e ecrã de carregamento (Splash Screen) | Arquivo de imagem PNG transparente (234x56 px aprox.), contendo o símbolo preto com ponto dourado (*Champagne Ore*) e o texto "fecho.pt". |
| `docs/INSUMOS.md` | Inventário e catalogação dos arquivos de documentação e insumos | Não | Documentação | Este próprio catálogo de apoio técnico. |
