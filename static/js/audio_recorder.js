/**
 * Módulo de Captura de Áudio em Visitas (Até 30 segundos) - Fecho (fecho.pt)
 * 
 * Funcionalidades:
 * 1. Gravação de áudio de alta fidelidade com MediaRecorder (limite estrito de 30s);
 * 2. Reconhecimento de voz em tempo real via Web Speech API (pt-PT / pt-BR);
 * 3. Temporizador tátil com eventos de progresso por segundo;
 * 4. Suporte a enfileiramento e sincronização offline (localStorage);
 * 5. Gerador client-side de mensagem formatada para WhatsApp do proprietário.
 */

const AudioRecorder = {
  maxDurationSeconds: 30,
  mediaRecorder: null,
  speechRecognition: null,
  audioChunks: [],
  audioBlob: null,
  audioBase64: null,
  liveTranscript: '',
  timerInterval: null,
  durationSeconds: 0,
  isRecording: false,
  offlineQueueKey: 'fecho_offline_visits_queue',

  // Callbacks para atualização da interface
  onTick: null,      // (currentSeconds, remainingSeconds, percent) => void
  onStop: null,      // (result) => void
  onError: null,     // (error) => void
  onTranscript: null,// (transcriptText) => void

  /**
   * Verifica se o navegador tem suporte a gravação de áudio.
   */
  isSupported() {
    return Boolean(
      navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia &&
      window.MediaRecorder
    );
  },

  /**
   * Inicia a gravação de voz (máximo 30 segundos).
   */
  async startRecording() {
    if (this.isRecording) return;

    this.audioChunks = [];
    this.audioBlob = null;
    this.audioBase64 = null;
    this.liveTranscript = '';
    this.durationSeconds = 0;

    // Inicializa Web Speech API se disponível no dispositivo
    this._initSpeechRecognition();

    try {
      if (this.isSupported()) {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          }
        });

        // Seleciona mimeType suportado
        let mimeType = 'audio/webm;codecs=opus';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = MediaRecorder.isTypeSupported('audio/mp4')
            ? 'audio/mp4'
            : '';
        }

        this.mediaRecorder = mimeType
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream);

        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };

        this.mediaRecorder.onstop = async () => {
          // Para todas as faixas do microfone
          stream.getTracks().forEach((track) => track.stop());
          this._finalizeRecording();
        };

        this.mediaRecorder.start(250); // Coleta a cada 250ms
      } else {
        console.warn('[AudioRecorder] MediaRecorder não suportado neste navegador. Utilizando modo simulado/reconhecimento direto.');
      }

      this.isRecording = true;

      if (this.speechRecognition) {
        try {
          this.speechRecognition.start();
        } catch (e) {
          console.warn('[AudioRecorder] Não foi possível iniciar Web Speech API:', e);
        }
      }

      // Inicia temporizador com limite estrito de 30 segundos
      this._startTimer();

    } catch (err) {
      this.isRecording = false;
      console.error('[AudioRecorder] Erro ao acessar microfone:', err);
      if (this.onError) {
        this.onError(err);
      }
      throw err;
    }
  },

  /**
   * Para a gravação manualmente antes dos 30 segundos.
   */
  stopRecording() {
    if (!this.isRecording) return;
    this.isRecording = false;
    this._clearTimer();

    if (this.speechRecognition) {
      try {
        this.speechRecognition.stop();
      } catch {}
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    } else {
      this._finalizeRecording();
    }
  },

  /**
   * Cancela a gravação sem emitir resultado.
   */
  cancelRecording() {
    this.isRecording = false;
    this._clearTimer();

    if (this.speechRecognition) {
      try {
        this.speechRecognition.abort();
      } catch {}
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        this.mediaRecorder.stream.getTracks().forEach((t) => t.stop());
        this.mediaRecorder.stop();
      } catch {}
    }

    this.audioChunks = [];
    this.audioBlob = null;
    this.liveTranscript = '';
    this.durationSeconds = 0;
  },

  /**
   * Inicializa o reconhecimento de voz nativo do navegador para Português.
   */
  _initSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) return;

    try {
      this.speechRecognition = new SpeechRec();
      this.speechRecognition.continuous = true;
      this.speechRecognition.interimResults = true;
      this.speechRecognition.lang = 'pt-PT'; // Português de Portugal

      this.speechRecognition.onresult = (event) => {
        let finalTrans = '';
        for (let i = 0; i < event.results.length; ++i) {
          finalTrans += event.results[i][0].transcript + ' ';
        }
        this.liveTranscript = finalTrans.trim();
        if (this.onTranscript) {
          this.onTranscript(this.liveTranscript);
        }
      };

      this.speechRecognition.onerror = (err) => {
        console.warn('[AudioRecorder] Aviso no reconhecimento de voz:', err);
      };
    } catch (e) {
      console.warn('[AudioRecorder] Falha ao instanciar SpeechRecognition:', e);
      this.speechRecognition = null;
    }
  },

  /**
   * Dispara o temporizador tátil de até 30 segundos.
   */
  _startTimer() {
    this._clearTimer();
    const startTime = Date.now();

    this.timerInterval = setInterval(() => {
      const elapsedSeconds = Math.min(
        this.maxDurationSeconds,
        Math.floor((Date.now() - startTime) / 1000)
      );
      this.durationSeconds = elapsedSeconds;

      const remaining = Math.max(0, this.maxDurationSeconds - elapsedSeconds);
      const percent = Math.min(100, (elapsedSeconds / this.maxDurationSeconds) * 100);

      if (this.onTick) {
        this.onTick(elapsedSeconds, remaining, percent);
      }

      // Encerra automaticamente aos 30 segundos
      if (elapsedSeconds >= this.maxDurationSeconds) {
        this.stopRecording();
      }
    }, 250);
  },

  _clearTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  },

  /**
   * Converte os chunks gravados em Blob e Base64 e aciona callback onStop.
   */
  async _finalizeRecording() {
    if (this.audioChunks.length > 0) {
      this.audioBlob = new Blob(this.audioChunks, {
        type: this.mediaRecorder ? this.mediaRecorder.mimeType : 'audio/webm'
      });

      // Conversão segura para Base64 para envio via JSON
      try {
        this.audioBase64 = await this._blobToBase64(this.audioBlob);
      } catch (e) {
        console.warn('[AudioRecorder] Falha ao converter áudio em base64:', e);
      }
    }

    const result = {
      durationSeconds: Math.max(1, this.durationSeconds),
      transcript: this.liveTranscript,
      audioBlob: this.audioBlob,
      audioBase64: this.audioBase64,
    };

    if (this.onStop) {
      this.onStop(result);
    }
  },

  _blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64data = reader.result ? reader.result.toString().split(',')[1] : null;
        resolve(base64data);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  },

  /**
   * Gera a mensagem formatada para WhatsApp do proprietário (Client-side / Offline).
   */
  generateWhatsAppFeedback({
    propriedade,
    consultorNome,
    nivelInteresse,
    notasEstruturadas,
    objectionNames,
  }) {
    const nomeProprietario = (propriedade && propriedade.nome_proprietario) || 'Proprietário(a)';
    const tituloImovel = propriedade ? `${propriedade.tipologia} • ${propriedade.titulo}` : 'Imóvel em Carteira';
    const consultor = consultorNome || 'Consultor Imobiliário';

    const interesseMap = {
      5: ['★ ★ ★ ★ ★', 'Proposta Iminente / Entusiasmo Total'],
      4: ['★ ★ ★ ★ ☆', 'Interesse Elevado / Forte Potencial'],
      3: ['★ ★ ★ ☆ ☆', 'Interesse Médio / Em Avaliação Comparativa'],
      2: ['★ ★ ☆ ☆ ☆', 'Interesse Baixo / Com Reservas'],
      1: ['★ ☆ ☆ ☆ ☆', 'Sem Interesse / Não Enquadrado no Perfil'],
    };

    const [stars, label] = interesseMap[nivelInteresse || 3] || ['★ ★ ★ ☆ ☆', 'Em Avaliação'];
    const notas = (notasEstruturadas && notasEstruturadas.trim()) || 'Visita presencial acompanhada e apresentação dos detalhes do imóvel.';

    let pontosAtencaoBloco = '';
    if (objectionNames && objectionNames.length > 0) {
      const itens = objectionNames.map((n) => `  - ${n}`).join('\n');
      pontosAtencaoBloco = `\n• Pontos de Atenção Levantados:\n${itens}\n`;
    }

    return (
      `Estimado(a) ${nomeProprietario},\n\n` +
      `Partilho o resumo da visita realizada hoje ao seu imóvel (${tituloImovel}):\n\n` +
      `• Nível de Interesse: ${stars} (${label})\n\n` +
      `• Resumo da Visita:\n${notas}\n` +
      `${pontosAtencaoBloco}\n` +
      `Seguimos a acompanhar este cliente com o devido rigor e manter-lhe-ei informado(a) sobre qualquer evolução ou proposta formal.\n\n` +
      `Com os melhores cumprimentos,\n` +
      `${consultor}\n` +
      `Fecho (fecho.pt)`
    );
  },

  /**
   * Constrói a URL Deep Link do WhatsApp.
   */
  getWhatsAppDeepLink(phone, messageText) {
    let cleanPhone = (phone || '').replace(/[^\d+]/g, '');
    if (cleanPhone.startsWith('+')) cleanPhone = cleanPhone.slice(1);
    const encoded = encodeURIComponent(messageText);
    return cleanPhone
      ? `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${encoded}`
      : `https://api.whatsapp.com/send?text=${encoded}`;
  },

  // =========================================================================
  // GESTÃO DA FILA OFFLINE (PWA Resilience)
  // =========================================================================

  getOfflineQueue() {
    try {
      const data = localStorage.getItem(this.offlineQueueKey);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  enqueueOfflineVisit(visitData) {
    const queue = this.getOfflineQueue();
    queue.push({
      id: 'local_' + Date.now(),
      queuedAt: new Date().toISOString(),
      payload: visitData,
    });
    localStorage.setItem(this.offlineQueueKey, JSON.stringify(queue));
    console.log(`[Offline Queue] Visita enfileirada. Total na fila: ${queue.length}`);
    window.dispatchEvent(new CustomEvent('fecho:offline_queue_changed', { detail: { count: queue.length } }));
  },

  async syncOfflineQueue(apiClient) {
    const queue = this.getOfflineQueue();
    if (!queue.length) return 0;

    console.log(`[Offline Sync] Sincronizando ${queue.length} visitas offline...`);
    const remaining = [];
    let syncedCount = 0;

    for (const item of queue) {
      try {
        await apiClient.createVisit(item.payload);
        syncedCount++;
        console.log(`[Offline Sync] Visita sincronizada com sucesso: ${item.id}`);
      } catch (err) {
        console.warn(`[Offline Sync] Falha ao sincronizar visita ${item.id}:`, err);
        remaining.push(item);
      }
    }

    localStorage.setItem(this.offlineQueueKey, JSON.stringify(remaining));
    window.dispatchEvent(new CustomEvent('fecho:offline_queue_changed', { detail: { count: remaining.length } }));
    return syncedCount;
  }
};

// Sincronização automática quando a conexão for restabelecida
window.addEventListener('online', () => {
  console.log('[PWA] Conexão restabelecida. Verificando fila offline...');
  if (typeof Api !== 'undefined' && Api.isAuthenticated()) {
    AudioRecorder.syncOfflineQueue(Api).then((count) => {
      if (count > 0) {
        console.log(`[PWA] ${count} visitas sincronizadas automaticamente.`);
      }
    });
  }
});
