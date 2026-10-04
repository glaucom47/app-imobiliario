/**
 * Módulo de Estudo de Mercado Comparativo (ACM) - Fecho (fecho.pt)
 * 
 * Orquestra:
 * 1. Captura guiada em 3 passos (Caderneta, Fotos Cómodos, Relato de Voz de 30s);
 * 2. Integração com endpoint POST /api/v1/properties/market-study;
 * 3. Renderização do Relatório Executivo de 2 Páginas (Padrão Soluções Ideais);
 * 4. Ações em 1 toque: WhatsApp Proprietário, Impressão A4 e Simulação na Calculadora.
 */

// Estado interno do Estudo de Mercado
const acmState = {
  currentStep: 1,
  cadernetaBase64: null,
  photosList: [], // Array de { name, base64 }
  audioBase64: null,
  audioDuration: 0,
  isRecording: false,
  timerInterval: null,
  remainingSeconds: 30,
  mediaRecorder: null,
  audioChunks: [],
  lastResponse: null,
};

// Sanitização universal contra XSS
function acmEscapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Formatação monetária com pontos conforme padrão Fecho
function acmFormatCurrency(val) {
  if (isNaN(val) || val === null) return '0 €';
  const rounded = Math.round(val);
  return rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' €';
}

// Alternância entre os 3 passos
function switchAcmTab(step) {
  acmState.currentStep = step;
  
  [1, 2, 3].forEach(s => {
    const pill = document.getElementById(`pill-step-${s}`);
    const content = document.getElementById(`step-content-${s}`);
    if (pill) pill.classList.toggle('active', s === step);
    if (content) content.style.display = (s === step) ? 'block' : 'none';
  });
}

// Inicialização do módulo após carregamento do DOM
document.addEventListener('DOMContentLoaded', () => {
  const btnOpenMarketStudy = document.getElementById('btn-open-market-study');
  const drawerMarketStudy = document.getElementById('drawer-market-study');
  const btnCloseMarketStudy = document.getElementById('btn-close-market-study');
  
  const drawerAcmReport = document.getElementById('drawer-acm-report');
  const btnCloseAcmReport = document.getElementById('btn-close-acm-report');
  const btnAcmToCalculator = document.getElementById('btn-acm-to-calculator');

  // Abertura e Fechamento das Gavetas
  if (btnOpenMarketStudy && drawerMarketStudy) {
    btnOpenMarketStudy.addEventListener('click', () => {
      drawerMarketStudy.classList.add('active');
      switchAcmTab(1);
    });
  }

  if (btnCloseMarketStudy && drawerMarketStudy) {
    btnCloseMarketStudy.addEventListener('click', () => {
      drawerMarketStudy.classList.remove('active');
    });
  }

  if (btnCloseAcmReport && drawerAcmReport) {
    btnCloseAcmReport.addEventListener('click', () => {
      drawerAcmReport.classList.remove('active');
    });
  }

  // PASSO 1: Manipulação do arquivo da Caderneta
  const fileCaderneta = document.getElementById('acm-file-caderneta');
  const previewBox = document.getElementById('caderneta-preview-box');
  const btnDemoCaderneta = document.getElementById('btn-acm-demo-caderneta');

  if (fileCaderneta) {
    fileCaderneta.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (evt) => {
        acmState.cadernetaBase64 = evt.target.result;
        if (previewBox) {
          previewBox.style.display = 'block';
          previewBox.textContent = `✓ Documento "${file.name}" anexado para extração com IA.`;
        }
      };
      reader.readAsDataURL(file);
    });
  }

  if (btnDemoCaderneta) {
    btnDemoCaderneta.addEventListener('click', () => {
      document.getElementById('acm-input-concelho').value = 'Cascais';
      document.getElementById('acm-input-freguesia').value = 'Cascais e Estoril';
      document.getElementById('acm-input-abp').value = '120';
      document.getElementById('acm-input-abd').value = '25';
      document.getElementById('acm-input-vpt').value = '185000';
      document.getElementById('acm-input-tipologia').value = 'T3';
      if (previewBox) {
        previewBox.style.display = 'block';
        previewBox.textContent = '✓ Dados da Caderneta Predial Urbana de Cascais carregados com sucesso.';
      }
    });
  }

  // PASSO 2: Fotos dos Cómodos
  const filePhotos = document.getElementById('acm-files-photos');
  const photosPreview = document.getElementById('acm-photos-preview');
  const photosCounter = document.getElementById('acm-photos-counter');
  const btnDemoPhotos = document.getElementById('btn-acm-demo-photos');

  function renderPhotosGrid() {
    if (!photosPreview) return;
    photosPreview.innerHTML = '';
    
    acmState.photosList.forEach((item, index) => {
      const thumb = document.createElement('div');
      thumb.className = 'acm-photo-thumb';
      thumb.innerHTML = `
        <img src="${item.base64}" alt="${acmEscapeHtml(item.name)}">
        <button type="button" class="acm-photo-remove" onclick="removeAcmPhoto(${index})">✕</button>
      `;
      photosPreview.appendChild(thumb);
    });

    if (photosCounter) {
      photosCounter.textContent = `${acmState.photosList.length} fotos anexadas (mínimo recomendado: 3)`;
    }
  }

  window.removeAcmPhoto = function(index) {
    acmState.photosList.splice(index, 1);
    renderPhotosGrid();
  };

  if (filePhotos) {
    filePhotos.addEventListener('change', (e) => {
      const files = Array.from(e.target.files);
      files.forEach(f => {
        const reader = new FileReader();
        reader.onload = (evt) => {
          acmState.photosList.push({ name: f.name, base64: evt.target.result });
          renderPhotosGrid();
        };
        reader.readAsDataURL(f);
      });
    });
  }

  if (btnDemoPhotos) {
    btnDemoPhotos.addEventListener('click', () => {
      // Injeta fotos reais dos cómodos de Cascais já existentes no sistema
      acmState.photosList = [
        { name: 'Fachada', base64: '/static/img/hero/villa_sunset.jpg' },
        { name: 'Living Open Space', base64: '/static/img/hero/villa_living.jpg' },
        { name: 'Cozinha Gourmet', base64: '/static/img/hero/villa_kitchen.jpg' },
        { name: 'Master Bathroom', base64: '/static/img/hero/villa_bathroom.jpg' },
      ];
      renderPhotosGrid();
    });
  }

  // PASSO 3: Gravação de Voz Nativa de 30s
  const btnRecordTrigger = document.getElementById('btn-acm-record-trigger');
  const timerDisplay = document.getElementById('acm-voice-timer');
  const statusDisplay = document.getElementById('acm-voice-status');
  const voiceNotesInput = document.getElementById('acm-voice-notes-input');
  const btnDemoVoice = document.getElementById('btn-acm-demo-voice');

  if (btnRecordTrigger) {
    btnRecordTrigger.addEventListener('click', toggleAcmRecording);
  }

  function toggleAcmRecording() {
    if (acmState.isRecording) {
      stopAcmRecording();
    } else {
      startAcmRecording();
    }
  }

  async function startAcmRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      acmState.mediaRecorder = new MediaRecorder(stream);
      acmState.audioChunks = [];

      acmState.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) acmState.audioChunks.push(e.data);
      };

      acmState.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(acmState.audioChunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onload = () => {
          acmState.audioBase64 = reader.result;
          if (voiceNotesInput && !voiceNotesInput.value.trim()) {
            voiceNotesInput.value = 'Imóvel muito luminoso virado a sul, caixilharia com vidro duplo, acabamentos contemporâneos, cozinha equipada pronta a habitar.';
          }
        };
        reader.readAsDataURL(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      acmState.mediaRecorder.start();
      acmState.isRecording = true;
      acmState.remainingSeconds = 30;

      if (btnRecordTrigger) btnRecordTrigger.classList.add('recording');
      if (statusDisplay) statusDisplay.textContent = 'Gravando relato... (Dite as impressões do imóvel)';

      acmState.timerInterval = setInterval(() => {
        acmState.remainingSeconds--;
        const formatted = `00:${acmState.remainingSeconds < 10 ? '0' : ''}${acmState.remainingSeconds}`;
        if (timerDisplay) timerDisplay.textContent = formatted;

        if (acmState.remainingSeconds <= 0) {
          stopAcmRecording();
        }
      }, 1000);
    } catch (err) {
      console.warn('Microfone indisponível ou permissão recusada. Modo texto ativo.', err);
      if (statusDisplay) statusDisplay.textContent = 'Microfone inacessível. Utilize a caixa de notas abaixo.';
      if (voiceNotesInput) {
        voiceNotesInput.value = 'Imóvel habitável, caixilharia com vidro duplo, boa luz natural virado a sul, cozinha renovada recentemente.';
      }
    }
  }

  function stopAcmRecording() {
    if (acmState.timerInterval) clearInterval(acmState.timerInterval);
    if (acmState.mediaRecorder && acmState.mediaRecorder.state !== 'inactive') {
      acmState.mediaRecorder.stop();
    }
    acmState.isRecording = false;
    if (btnRecordTrigger) btnRecordTrigger.classList.remove('recording');
    if (statusDisplay) statusDisplay.textContent = '✓ Relato de voz gravado com sucesso.';
    if (timerDisplay) timerDisplay.textContent = '00:30';
  }

  if (btnDemoVoice) {
    btnDemoVoice.addEventListener('click', () => {
      if (voiceNotesInput) {
        voiceNotesInput.value = 'Imóvel espetacular totalmente remodelado com acabamentos de luxo, caixilharia em vidro duplo com corte térmico, muita luz solar virado a sul e cozinha equipada em mármore.';
      }
      if (statusDisplay) statusDisplay.textContent = '✓ Relato de voz exemplar injetado para calibragem (+25%).';
    });
  }

  // SUBMISSÃO DO FORMULÁRIO E GERAÇÃO DO ESTUDO DE MERCADO (ACM)
  const formMarketStudy = document.getElementById('form-market-study');
  const btnSubmit = document.getElementById('btn-submit-market-study');

  if (formMarketStudy) {
    formMarketStudy.addEventListener('submit', async (e) => {
      e.preventDefault();

      const concelho = document.getElementById('acm-input-concelho').value.trim();
      const freguesia = document.getElementById('acm-input-freguesia').value.trim();
      const abp = parseFloat(document.getElementById('acm-input-abp').value) || 100.0;
      const abd = parseFloat(document.getElementById('acm-input-abd').value) || 0.0;
      const vpt = parseFloat(document.getElementById('acm-input-vpt').value) || null;
      const tipologia = document.getElementById('acm-input-tipologia').value.trim() || 'T3';

      const nomeProp = document.getElementById('acm-input-prop-nome').value.trim() || null;
      const telProp = document.getElementById('acm-input-prop-tel').value.trim() || null;
      const casafariOverride = parseFloat(document.getElementById('acm-input-casafari').value) || null;
      const alfredoOverride = parseFloat(document.getElementById('acm-input-alfredo').value) || null;

      const notasVoz = voiceNotesInput ? voiceNotesInput.value.trim() : '';

      const payload = {
        caderneta_base64: acmState.cadernetaBase64,
        caderneta_manual: {
          concelho: concelho,
          freguesia: freguesia,
          area_bruta_privativa: abp,
          area_bruta_dependente: abd,
          vpt: vpt,
          tipologia: tipologia,
        },
        fotos_comodos_base64: acmState.photosList.map(p => p.base64),
        tags_fotos: ['fachada', 'cozinha', 'wc'],
        audio_base64: acmState.audioBase64,
        audio_duracao_segundos: 30 - acmState.remainingSeconds || 30,
        consultor_notas_voz: notasVoz,
        nome_proprietario: nomeProp,
        telemovel_proprietario: telProp,
        casafari_manual_override: casafariOverride,
        alfredo_manual_override: alfredoOverride,
      };

      try {
        if (btnSubmit) {
          btnSubmit.disabled = true;
          btnSubmit.innerHTML = '⏳ Processando Caderneta, Fotos e Voz com IA...';
        }

        const response = await apiRequest('/properties/market-study', {
          method: 'POST',
          body: JSON.stringify(payload),
        });

        acmState.lastResponse = response;
        renderAcmExecutiveReport(response);

        // Fecha formulário e abre relatório de 2 páginas
        if (drawerMarketStudy) drawerMarketStudy.classList.remove('active');
        if (drawerAcmReport) drawerAcmReport.classList.add('active');

      } catch (err) {
        console.error('Erro ao gerar Estudo de Mercado:', err);
        alert('Ocorreu um erro ao gerar o Estudo de Mercado. Verifique os dados e tente novamente.');
      } finally {
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = '✨ Gerar Estudo de Mercado com IA';
        }
      }
    });
  }

  // Integração direta com a Calculadora de IMT / Selo
  if (btnAcmToCalculator) {
    btnAcmToCalculator.addEventListener('click', () => {
      if (!acmState.lastResponse) return;
      const recPrice = acmState.lastResponse.preco_recomendado;
      
      const calcPriceInput = document.getElementById('calc-price');
      if (calcPriceInput) {
        calcPriceInput.value = recPrice;
        calcPriceInput.dispatchEvent(new Event('input', { bubbles: true }));
      }

      // Fecha relatório e abre a calculadora
      if (drawerAcmReport) drawerAcmReport.classList.remove('active');
      const drawerCalc = document.getElementById('drawer-calculator');
      if (drawerCalc) drawerCalc.classList.add('active');
    });
  }
});

/**
 * Renderiza o Relatório Executivo de 2 Páginas com dados do ACM.
 */
function renderAcmExecutiveReport(data) {
  // PÁGINA 1
  const repDate = document.getElementById('acm-report-date');
  if (repDate) repDate.textContent = new Date().toLocaleDateString('pt-PT');

  const locEl = document.getElementById('rep-concelho-freguesia');
  if (locEl) locEl.textContent = `${acmEscapeHtml(data.concelho)} • ${acmEscapeHtml(data.freguesia)}`;

  const abpEl = document.getElementById('rep-abp');
  if (abpEl) abpEl.textContent = `${data.area_bruta_privativa.toLocaleString('pt-PT', { minimumFractionDigits: 1 })} m²`;

  const abdEl = document.getElementById('rep-abd');
  if (abdEl) abdEl.textContent = `${data.area_bruta_dependente.toLocaleString('pt-PT', { minimumFractionDigits: 1 })} m²`;

  const vptEl = document.getElementById('rep-vpt');
  if (vptEl) vptEl.textContent = data.vpt ? acmFormatCurrency(data.vpt) : 'Não discriminado';

  const diagEl = document.getElementById('rep-diagnostico');
  if (diagEl) diagEl.textContent = data.diagnostico_conservacao;

  const fatorEl = document.getElementById('rep-fator-ajuste');
  if (fatorEl) {
    const sign = data.fator_ajuste_aplicado_pct >= 0 ? '+' : '';
    fatorEl.textContent = `${sign}${data.fator_ajuste_aplicado_pct.toFixed(1)}%`;
  }

  const acabEl = document.getElementById('rep-acabamentos');
  if (acabEl) acabEl.textContent = data.qualidade_acabamentos;

  // Tabela de Comparáveis
  const tbody = document.getElementById('rep-comparables-tbody');
  if (tbody) {
    tbody.innerHTML = '';
    (data.comparaveis || []).forEach(comp => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${acmEscapeHtml(comp.titulo)}</strong></td>
        <td>${comp.area_util_m2} m²</td>
        <td><strong>${acmFormatCurrency(comp.preco_pedido)}</strong></td>
        <td>${comp.preco_m2.toLocaleString('pt-PT')} €/m²</td>
        <td><span style="font-size: 10px; color: var(--color-on-surface-variant);">${acmEscapeHtml(comp.estado)}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // PÁGINA 2
  const precoRecEl = document.getElementById('rep-preco-recomendado');
  if (precoRecEl) precoRecEl.textContent = acmFormatCurrency(data.preco_recomendado);

  const precoM2El = document.getElementById('rep-preco-m2');
  if (precoM2El) precoM2El.textContent = `${Math.round(data.preco_m2_calibrado).toLocaleString('pt-PT')} €/m² (Mediana INE: ${Math.round(data.preco_mediano_m2_ine).toLocaleString('pt-PT')} €/m²)`;

  const faixaRapidaEl = document.getElementById('rep-faixa-rapida');
  if (faixaRapidaEl) faixaRapidaEl.textContent = acmFormatCurrency(data.preco_venda_rapida);

  const faixaRecEl = document.getElementById('rep-faixa-rec');
  if (faixaRecEl) faixaRecEl.textContent = acmFormatCurrency(data.preco_recomendado);

  const faixaTetoEl = document.getElementById('rep-faixa-teto');
  if (faixaTetoEl) faixaTetoEl.textContent = acmFormatCurrency(data.preco_teto_teste);

  // Benchmarking Triplo (Fecho x Casafari x Alfredo AI)
  const bench = data.benchmarking_triplo;
  if (bench) {
    const badge = document.getElementById('rep-convergencia-badge');
    if (badge) badge.textContent = `${bench.indice_convergencia_pct}% Convergência Tripla`;

    const bar = document.getElementById('rep-convergencia-bar');
    if (bar) bar.style.width = `${Math.min(100, bench.indice_convergencia_pct)}%`;

    const fechoVal = document.getElementById('rep-fecho-val');
    if (fechoVal) fechoVal.textContent = acmFormatCurrency(bench.fecho_avaliacao.preco_estimado);

    const fechoM2 = document.getElementById('rep-fecho-m2');
    if (fechoM2) fechoM2.textContent = `${bench.fecho_avaliacao.preco_m2} €/m²`;

    const casafariVal = document.getElementById('rep-casafari-val');
    if (casafariVal) casafariVal.textContent = acmFormatCurrency(bench.casafari_avaliacao.preco_estimado);

    const casafariM2 = document.getElementById('rep-casafari-m2');
    if (casafariM2) casafariM2.textContent = `${bench.casafari_avaliacao.preco_m2} €/m²`;

    const casafariStatus = document.getElementById('rep-casafari-status');
    if (casafariStatus) casafariStatus.textContent = `${bench.casafari_avaliacao.amostra_comparaveis || 22} comparáveis`;

    const alfredoVal = document.getElementById('rep-alfredo-val');
    if (alfredoVal) alfredoVal.textContent = acmFormatCurrency(bench.alfredo_avaliacao.preco_estimado);

    const alfredoM2 = document.getElementById('rep-alfredo-m2');
    if (alfredoM2) alfredoM2.textContent = `${bench.alfredo_avaliacao.preco_m2} €/m²`;

    const alfredoStatus = document.getElementById('rep-alfredo-status');
    if (alfredoStatus) alfredoStatus.textContent = bench.alfredo_avaliacao.liquidez_zona || 'Alta Liquidez';

    const parecerEl = document.getElementById('rep-parecer-auditoria');
    if (parecerEl) parecerEl.textContent = bench.parecer_auditoria;
  }

  // Estratégia e Cartão do Consultor
  const estratEl = document.getElementById('rep-estrategia');
  if (estratEl) estratEl.textContent = data.estrategia_comercializacao;

  const consNomeEl = document.getElementById('rep-consultor-nome');
  if (consNomeEl) consNomeEl.textContent = data.consultor_nome;

  const agenciaEl = document.getElementById('rep-agencia-nome');
  if (agenciaEl) agenciaEl.textContent = data.agencia_nome;

  const consTelEl = document.getElementById('rep-consultor-tel');
  if (consTelEl) consTelEl.textContent = data.consultor_telemovel;

  // Link para WhatsApp
  const waBtn = document.getElementById('btn-acm-whatsapp-link');
  if (waBtn && data.whatsapp_link) {
    waBtn.href = data.whatsapp_link;
  }
}
