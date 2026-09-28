/**
 * Motor e Controlador do Teleprompter - Fecho (fecho.pt)
 * Conforme FSD e DESIGN (Editorial PropTech Luxury):
 * - Superfície escura de alto contraste (#111111) para legibilidade em luz solar direta.
 * - Rolagem suave temporizada com requestAnimationFrame (60 FPS).
 * - Contagem regressiva 3-2-1 para início da gravação de vídeo curto.
 * - Controle tátil de velocidade, tamanho de fonte e pausa instantânea.
 * - Cópia rápida para clipboard do texto integral formatado.
 * - Gerador offline de contingência em 3 blocos (Gancho, 2 Destaques e CTA).
 */

const Teleprompter = {
  // Estado interno
  speed: 2, // 1 (lento) a 5 (rápido)
  fontSize: 24, // Tamanho em pixels (18px a 38px)
  isPlaying: false,
  isCountingDown: false,
  countdownTimer: null,
  animationFrameId: null,
  lastTimestamp: null,

  // Referências DOM
  elements: {
    overlay: null,
    scrollContainer: null,
    textContent: null,
    countdownOverlay: null,
    countdownNumber: null,
    speedLabel: null,
    btnPlayPause: null,
    propertyTitle: null,
    objectiveBadge: null,
    wordsCounter: null,
    timeCounter: null,
  },

  // Dados do roteiro atual
  currentScript: null,

  /**
   * Mapeamento de velocidade para pixels por segundo
   * Níveis 1 a 5:
   * 1 = ~24 px/s (leitura relaxada)
   * 2 = ~42 px/s (leitura natural de 130-140 WPM)
   * 3 = ~64 px/s (ritmo dinâmico de 150-165 WPM)
   * 4 = ~90 px/s (ritmo acelerado)
   * 5 = ~125 px/s (leitura rápida)
   */
  speedToPixelsPerSecond: {
    1: 26,
    2: 44,
    3: 68,
    4: 95,
    5: 130,
  },

  /**
   * Inicializa o teleprompter associando elementos da interface.
   */
  init(customElements = {}) {
    this.elements = {
      overlay: document.getElementById('teleprompter-modal'),
      scrollContainer: document.getElementById('teleprompter-scroll-container'),
      textContent: document.getElementById('teleprompter-text-content'),
      countdownOverlay: document.getElementById('teleprompter-countdown-overlay'),
      countdownNumber: document.getElementById('teleprompter-countdown-number'),
      speedLabel: document.getElementById('teleprompter-speed-label'),
      btnPlayPause: document.getElementById('teleprompter-btn-play-pause'),
      propertyTitle: document.getElementById('teleprompter-prop-title'),
      objectiveBadge: document.getElementById('teleprompter-obj-badge'),
      wordsCounter: document.getElementById('teleprompter-words-count'),
      timeCounter: document.getElementById('teleprompter-time-count'),
      ...customElements,
    };

    this.bindKeyboardShortcuts();
    this.updateControlsUI();
  },

  /**
   * Carrega um roteiro estruturado ou string de texto no leitor do teleprompter.
   */
  loadScript(scriptData) {
    this.currentScript = scriptData;

    let textFormatted = '';
    let titleText = 'Roteiro de Vídeo';
    let objectiveText = 'Vídeo Curto';
    let totalWords = 0;
    let estimatedSeconds = 35;

    if (typeof scriptData === 'string') {
      textFormatted = scriptData;
      totalWords = scriptData.split(/\s+/).filter(Boolean).length;
      estimatedSeconds = Math.max(Math.ceil((totalWords / 140) * 60), 5);
    } else if (scriptData && typeof scriptData === 'object') {
      titleText = scriptData.property_titulo || 'Imóvel Selecionado';
      objectiveText = scriptData.objetivo_label || 'Vídeo de Marketing';
      totalWords = scriptData.total_palavras || (scriptData.texto_completo ? scriptData.texto_completo.split(/\s+/).filter(Boolean).length : 0);
      estimatedSeconds = scriptData.tempo_estimado_segundos || 35;

      if (scriptData.blocos && Array.isArray(scriptData.blocos)) {
        textFormatted = scriptData.blocos
          .map((b) => `<div class="prompter-block"><span class="prompter-block-title">${this.escapeHtml(b.titulo)}</span><p class="prompter-block-content">${this.escapeHtml(b.conteudo).replace(/\n/g, '<br>')}</p></div>`)
          .join('');
      } else if (scriptData.texto_completo) {
        textFormatted = `<div class="prompter-block"><p class="prompter-block-content">${this.escapeHtml(scriptData.texto_completo).replace(/\n/g, '<br>')}</p></div>`;
      }
    }

    if (this.elements.textContent) {
      this.elements.textContent.innerHTML = textFormatted;
      this.elements.textContent.style.fontSize = `${this.fontSize}px`;
    }

    if (this.elements.propertyTitle) {
      this.elements.propertyTitle.textContent = titleText;
    }

    if (this.elements.objectiveBadge) {
      this.elements.objectiveBadge.textContent = objectiveText;
    }

    if (this.elements.wordsCounter) {
      this.elements.wordsCounter.textContent = `${totalWords} palavras`;
    }

    if (this.elements.timeCounter) {
      this.elements.timeCounter.textContent = `~${estimatedSeconds}s`;
    }

    this.reset();
  },

  /**
   * Abre o ecrã imersivo escuro (#111111) do Teleprompter.
   */
  open() {
    if (!this.elements.overlay) this.init();
    if (this.elements.overlay) {
      this.elements.overlay.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      this.reset();
    }
  },

  /**
   * Fecha o ecrã do teleprompter e restaura a rolagem padrão da página.
   */
  close() {
    this.pause();
    this.cancelCountdown();
    if (this.elements.overlay) {
      this.elements.overlay.style.display = 'none';
      document.body.style.overflow = '';
    }
  },

  /**
   * Inicia a contagem regressiva 3-2-1 com efeitos táteis e visuais.
   */
  startCountdown(onFinished) {
    if (this.isCountingDown) return;
    this.pause();
    this.isCountingDown = true;

    if (!this.elements.countdownOverlay || !this.elements.countdownNumber) {
      this.isCountingDown = false;
      if (typeof onFinished === 'function') onFinished();
      this.play();
      return;
    }

    let count = 3;
    this.elements.countdownOverlay.style.display = 'flex';
    this.elements.countdownNumber.textContent = count;
    this.elements.countdownNumber.classList.remove('pulse-anim');
    void this.elements.countdownNumber.offsetWidth; // Força reflow
    this.elements.countdownNumber.classList.add('pulse-anim');

    // Vibração tátil sutil em telemóveis compatíveis
    if (navigator.vibrate) {
      navigator.vibrate(80);
    }

    this.countdownTimer = setInterval(() => {
      count -= 1;
      if (count > 0) {
        this.elements.countdownNumber.textContent = count;
        this.elements.countdownNumber.classList.remove('pulse-anim');
        void this.elements.countdownNumber.offsetWidth;
        this.elements.countdownNumber.classList.add('pulse-anim');
        if (navigator.vibrate) navigator.vibrate(80);
      } else {
        clearInterval(this.countdownTimer);
        this.countdownTimer = null;
        this.elements.countdownNumber.textContent = 'GRAVAR!';
        if (navigator.vibrate) navigator.vibrate([120, 60, 120]);

        setTimeout(() => {
          this.elements.countdownOverlay.style.display = 'none';
          this.isCountingDown = false;
          if (typeof onFinished === 'function') onFinished();
          this.play();
        }, 500);
      }
    }, 1000);
  },

  /**
   * Cancela a contagem regressiva em andamento.
   */
  cancelCountdown() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
    this.isCountingDown = false;
    if (this.elements.countdownOverlay) {
      this.elements.countdownOverlay.style.display = 'none';
    }
  },

  /**
   * Alterna entre iniciar rolagem ou pausar.
   */
  togglePlay() {
    if (this.isCountingDown) {
      this.cancelCountdown();
      return;
    }
    if (this.isPlaying) {
      this.pause();
    } else {
      // Se estiver no topo, inicia com a contagem 3-2-1
      const isAtTop = !this.elements.scrollContainer || this.elements.scrollContainer.scrollTop < 10;
      if (isAtTop) {
        this.startCountdown(() => {});
      } else {
        this.play();
      }
    }
  },

  /**
   * Inicia o laço de animação contínua e suave de rolagem (requestAnimationFrame).
   */
  play() {
    if (this.isPlaying) return;
    this.isPlaying = true;
    this.lastTimestamp = null;
    this.updateControlsUI();

    const scrollLoop = (timestamp) => {
      if (!this.isPlaying) return;

      if (!this.lastTimestamp) {
        this.lastTimestamp = timestamp;
      }
      const deltaSeconds = (timestamp - this.lastTimestamp) / 1000;
      this.lastTimestamp = timestamp;

      if (this.elements.scrollContainer) {
        const pxPerSecond = this.speedToPixelsPerSecond[this.speed] || 44;
        const deltaPx = pxPerSecond * deltaSeconds;
        this.elements.scrollContainer.scrollTop += deltaPx;

        // Verifica se chegou ao fim
        const maxScroll = this.elements.scrollContainer.scrollHeight - this.elements.scrollContainer.clientHeight;
        if (this.elements.scrollContainer.scrollTop >= maxScroll - 2) {
          this.pause();
          return;
        }
      }

      this.animationFrameId = requestAnimationFrame(scrollLoop);
    };

    this.animationFrameId = requestAnimationFrame(scrollLoop);
  },

  /**
   * Pausa a rolagem do texto.
   */
  pause() {
    this.isPlaying = false;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    this.updateControlsUI();
  },

  /**
   * Reinicia a rolagem para o início do texto.
   */
  reset() {
    this.pause();
    this.cancelCountdown();
    if (this.elements.scrollContainer) {
      this.elements.scrollContainer.scrollTo({ top: 0, behavior: 'smooth' });
    }
    this.updateControlsUI();
  },

  /**
   * Ajusta a velocidade de rolagem (1 a 5).
   */
  setSpeed(newSpeed) {
    const clamped = Math.max(1, Math.min(5, parseInt(newSpeed, 10) || 2));
    this.speed = clamped;
    this.updateControlsUI();
  },

  /**
   * Aumenta a velocidade de rolagem.
   */
  increaseSpeed() {
    this.setSpeed(this.speed + 1);
  },

  /**
   * Diminui a velocidade de rolagem.
   */
  decreaseSpeed() {
    this.setSpeed(this.speed - 1);
  },

  /**
   * Ajusta o tamanho da fonte do texto (18px a 38px).
   */
  setFontSize(newSize) {
    const clamped = Math.max(18, Math.min(38, parseInt(newSize, 10) || 24));
    this.fontSize = clamped;
    if (this.elements.textContent) {
      this.elements.textContent.style.fontSize = `${this.fontSize}px`;
    }
  },

  /**
   * Aumenta o tamanho da fonte.
   */
  increaseFontSize() {
    this.setFontSize(this.fontSize + 2);
  },

  /**
   * Reduz o tamanho da fonte.
   */
  decreaseFontSize() {
    this.setFontSize(this.fontSize - 2);
  },

  /**
   * Atualiza a interface gráfica dos botões de controle.
   */
  updateControlsUI() {
    if (this.elements.speedLabel) {
      this.elements.speedLabel.textContent = `${this.speed}x`;
    }

    if (this.elements.btnPlayPause) {
      if (this.isPlaying) {
        this.elements.btnPlayPause.innerHTML = '⏸ Pausar';
        this.elements.btnPlayPause.classList.add('is-playing');
      } else {
        this.elements.btnPlayPause.innerHTML = '▶ Iniciar';
        this.elements.btnPlayPause.classList.remove('is-playing');
      }
    }
  },

  /**
   * Copia o roteiro integral para a área de transferência com feedback tátil.
   */
  async copyScriptToClipboard(customText = null) {
    let textToCopy = customText;

    if (!textToCopy) {
      if (this.currentScript) {
        if (typeof this.currentScript === 'string') {
          textToCopy = this.currentScript;
        } else if (this.currentScript.texto_completo) {
          textToCopy = this.currentScript.texto_completo;
        } else if (this.currentScript.gancho) {
          textToCopy = `[1. GANCHO]\n${this.currentScript.gancho}\n\n[2. DESTAQUES]\n${this.currentScript.destaque_1}\n\n${this.currentScript.destaque_2}\n\n[3. CTA]\n${this.currentScript.cta}`;
        }
      } else if (this.elements.textContent) {
        textToCopy = this.elements.textContent.innerText;
      }
    }

    if (!textToCopy) {
      throw new Error('Nenhum texto disponível para cópia.');
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(textToCopy);
    } else {
      // Fallback para navegadores legados
      const textarea = document.createElement('textarea');
      textarea.value = textToCopy;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }

    if (navigator.vibrate) {
      navigator.vibrate(50);
    }

    return true;
  },

  /**
   * Registra atalhos de teclado ergonômicos (Barra de Espaço, Setas e Esc).
   */
  bindKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      // Apenas atua se o overlay do teleprompter estiver visível
      if (!this.elements.overlay || this.elements.overlay.style.display !== 'flex') {
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        this.togglePlay();
      } else if (e.code === 'ArrowUp') {
        e.preventDefault();
        this.increaseSpeed();
      } else if (e.code === 'ArrowDown') {
        e.preventDefault();
        this.decreaseSpeed();
      } else if (e.code === 'Escape') {
        e.preventDefault();
        this.close();
      }
    });
  },

  /**
   * Gerador offline de contingência em 3 blocos.
   * Permite ao consultor gerar roteiros e ensaiar em campo sem nenhuma conexão com o servidor.
   */
  generateOfflineScript(property, objective = 'angariacao') {
    const titulo = property?.titulo || 'Imóvel Exclusivo';
    const tipologia = property?.tipologia || 'Apartamento';
    const preco = this.formatCurrency(property?.preco);
    const local = property?.concelho || property?.morada || 'excelente localização';
    const area = property?.area_bruta ? ` com ${property.area_bruta} m²` : '';

    let gancho = '';
    let destaque1 = '';
    let destaque2 = '';
    let cta = '';
    let objNome = 'Angariação';

    if (objective === 'baixa_preco') {
      objNome = 'Baixa de Preço';
      gancho = `Atenção: nova oportunidade em ${local}! Este magnífico ${tipologia} acabou de sofrer um ajuste direto para ${preco}.`;
      destaque1 = `Primeiro destaque: valor altamente competitivo e abaixo da média para a zona de ${local}.${area}`;
      destaque2 = `Segundo destaque: imóvel impecável, pronto a habitar e com condições favoráveis para celebração rápida de escritura.`;
      cta = `Envie-me mensagem agora mesmo no WhatsApp para agendar a sua visita antes que seja reservado.`;
    } else if (objective === 'open_house') {
      objNome = 'Open House';
      gancho = `Está convidado para uma visita exclusiva: neste fim de semana abrimos as portas deste ${tipologia} em ${local}!`;
      destaque1 = `Venha comprovar ao vivo a luminosidade, as áreas generosas${area} e a tranquilidade incomparável deste endereço.`;
      destaque2 = `A nossa equipa estará presente com simulações completas de financiamento bancário e cálculos de IMT e Selo para o valor de ${preco}.`;
      cta = `As vagas para o evento são limitadas. Confirme já a sua presença pelo link da bio ou mensagem privada.`;
    } else {
      // angariacao
      objNome = 'Angariação';
      gancho = `Se procura um ${tipologia} de sonho em ${local}, acaba de entrar no mercado uma oportunidade exclusiva que não pode perder.`;
      destaque1 = `Primeiro: localização de prestígio${area} aliada a divisões amplas com excelente exposição solar.`;
      destaque2 = `Segundo: uma relação preço-qualidade excecional por ${preco}, ideal tanto para habitação própria como para investimento sólido.`;
      cta = `Contacte-me hoje mesmo por WhatsApp ou mensagem direta para receber o dossier completo e agendar a sua visita privada.`;
    }

    const textoCompleto = (
      `--- [1. GANCHO] ---\n${gancho}\n\n` +
      `--- [2. DESTAQUES] ---\n${destaque1}\n\n${destaque2}\n\n` +
      `--- [3. CHAMADA PARA AÇÃO] ---\n${cta}`
    );

    const totalPalavras = (gancho + ' ' + destaque1 + ' ' + destaque2 + ' ' + cta).split(/\s+/).filter(Boolean).length;
    const tempoEstimado = Math.max(Math.ceil((totalPalavras / 140) * 60), 5);

    return {
      property_id: property?.id || 0,
      property_titulo: titulo,
      tipologia: tipologia,
      preco_formatado: preco,
      localizacao: local,
      objetivo: objective,
      objetivo_label: objNome,
      gancho: gancho,
      destaque_1: destaque1,
      destaque_2: destaque2,
      cta: cta,
      blocos: [
        { ordem: 1, chave: 'gancho', titulo: '1. Gancho Magnético (0 a 5s)', tempo_estimado_segundos: 6, conteudo: gancho },
        { ordem: 2, chave: 'destaques', titulo: '2. Dois Destaques (5 a 25s)', tempo_estimado_segundos: 20, conteudo: `${destaque1}\n\n${destaque2}` },
        { ordem: 3, chave: 'cta', titulo: '3. Chamada para Ação (25 a 35s)', tempo_estimado_segundos: 9, conteudo: cta },
      ],
      texto_completo: textoCompleto,
      total_palavras: totalPalavras,
      tempo_estimado_segundos: tempoEstimado,
    };
  },

  /**
   * Formata valores numéricos para o padrão monetário com separador de milhar por ponto.
   */
  formatCurrency(value) {
    if (value === null || value === undefined || value === '') return 'sob consulta';
    const valInt = Math.round(Number(value) || 0);
    return valInt.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' €';
  },

  /**
   * Função utilitária para higienizar saídas HTML (prevenção contra XSS).
   */
  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};

// Exportação compatível com ambientes Node/Jest/ESM e Vanilla Browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Teleprompter;
}
