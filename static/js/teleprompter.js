/**
 * Leitor e Controlador do Teleprompter - Fecho (fecho.pt)
 * Responsável pela rolagem temporizada, contagem 3-2-1 e ensaio de roteiros de marketing.
 * A implementação completa será realizada na Fase 7.
 */

const Teleprompter = {
  speed: 2,
  isPlaying: false,

  startCountdown(callback) {
    // Contagem regressiva 3-2-1 para início da gravação
    console.log("Iniciando contagem regressiva...");
    if (typeof callback === 'function') callback();
  },

  togglePlay() {
    this.isPlaying = !this.isPlaying;
  },

  copyScriptToClipboard(text) {
    if (navigator.clipboard) {
      return navigator.clipboard.writeText(text);
    }
  }
};
