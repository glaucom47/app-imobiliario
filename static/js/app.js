/**
 * Inicialização e Bootstrap Client-side - Fecho (fecho.pt)
 * Gestão de sessão, PWA offline, carteira de imóveis e máquina de estados.
 */

document.addEventListener('DOMContentLoaded', async () => {
  console.log('[Fecho] Inicializando aplicação móvel PWA...');

  // 1. Registro de Service Worker para suporte offline
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/sw.js')
        .then((registration) => {
          console.log('[PWA] Service Worker registrado:', registration.scope);
        })
        .catch((error) => {
          console.warn('[PWA] Falha ao registrar Service Worker:', error);
        });
    });
  }

  // 1.1 Controle de Modo Luz Solar Intensa e Estado de Rede (PWA / Offline)
  const btnSunlightToggle = document.getElementById('btn-sunlight-toggle');
  const sunlightLabel = document.getElementById('sunlight-label');
  const offlineStatusBanner = document.getElementById('offline-status-banner');

  function setSunlightMode(enabled) {
    if (enabled) {
      document.body.classList.add('sunlight-mode');
      if (sunlightLabel) sunlightLabel.textContent = 'Luz Solar: ON';
      if (btnSunlightToggle) {
        btnSunlightToggle.style.background = '#000000';
        btnSunlightToggle.style.color = '#ffffff';
      }
      localStorage.setItem('fecho_sunlight_mode', 'true');
    } else {
      document.body.classList.remove('sunlight-mode');
      if (sunlightLabel) sunlightLabel.textContent = 'Luz Solar';
      if (btnSunlightToggle) {
        btnSunlightToggle.style.background = '#ffffff';
        btnSunlightToggle.style.color = 'inherit';
      }
      localStorage.removeItem('fecho_sunlight_mode');
    }
  }

  if (localStorage.getItem('fecho_sunlight_mode') === 'true') {
    setSunlightMode(true);
  }

  if (btnSunlightToggle) {
    btnSunlightToggle.addEventListener('click', () => {
      const isCurrently = document.body.classList.contains('sunlight-mode');
      setSunlightMode(!isCurrently);
    });
  }

  function updateNetworkStatus(isOnline) {
    if (offlineStatusBanner) {
      offlineStatusBanner.style.display = isOnline ? 'none' : 'block';
    }
    console.log(`[PWA] Conectividade de rede: ${isOnline ? 'Online' : 'Offline'}`);
  }

  window.addEventListener('online', () => updateNetworkStatus(true));
  window.addEventListener('offline', () => updateNetworkStatus(false));
  if (typeof navigator.onLine === 'boolean') {
    updateNetworkStatus(navigator.onLine);
  }

  // 2. Elementos de Autenticação e Cabeçalho
  const authModal = document.getElementById('auth-modal');
  const loginForm = document.getElementById('login-form');
  const loginEmailInput = document.getElementById('login-email');
  const loginPasswordInput = document.getElementById('login-password');
  const loginError = document.getElementById('login-error');
  const btnSubmitLogin = document.getElementById('btn-submit-login');
  const userBadge = document.getElementById('user-badge');
  const btnLogout = document.getElementById('btn-logout');
  const btnDemoConsultor = document.getElementById('btn-demo-consultor');
  const btnDemoDiretor = document.getElementById('btn-demo-diretor');

  // Elementos do Imóvel em Foco
  const propertySelectorCard = document.getElementById('property-selector-card');
  const focusPropTitle = document.getElementById('focus-prop-title');
  const focusPropSubtitle = document.getElementById('focus-prop-subtitle');
  const btnOpenPortfolio = document.getElementById('btn-open-portfolio');
  const navCarteira = document.getElementById('nav-carteira');

  // Elementos da Gaveta de Carteira
  const drawerPortfolio = document.getElementById('drawer-portfolio');
  const btnClosePortfolio = document.getElementById('btn-close-portfolio');
  const portfolioListContainer = document.getElementById('portfolio-list-container');
  const portfolioCountLabel = document.getElementById('portfolio-count-label');
  const propertySearchInput = document.getElementById('property-search-input');
  const portfolioFilterBar = document.getElementById('portfolio-filter-bar');
  const btnOpenNewProperty = document.getElementById('btn-open-new-property');

  // Elementos do Modal Novo Imóvel
  const modalNewProperty = document.getElementById('modal-new-property');
  const btnCloseNewProperty = document.getElementById('btn-close-new-property');
  const formNewProperty = document.getElementById('form-new-property');
  const newPropError = document.getElementById('new-prop-error');
  const btnSubmitNewProperty = document.getElementById('btn-submit-new-property');

  // Elementos do Modal de Transição de Estado
  const modalTransitionStatus = document.getElementById('modal-transition-status');
  const btnCloseTransition = document.getElementById('btn-close-transition');
  const formTransitionStatus = document.getElementById('form-transition-status');
  const transitionPropertyId = document.getElementById('transition-property-id');
  const transitionPropTitleLabel = document.getElementById('transition-prop-title-label');
  const selectTransitionTarget = document.getElementById('select-transition-target');
  const soldClosingInputs = document.getElementById('sold-closing-inputs');
  const soldBuyerName = document.getElementById('sold-buyer-name');
  const soldBuyerPhone = document.getElementById('sold-buyer-phone');
  const soldBuyerDate = document.getElementById('sold-buyer-date');
  const transitionError = document.getElementById('transition-error');
  const btnSubmitTransition = document.getElementById('btn-submit-transition');

  // Estado Local da Carteira
  let currentFilterStatus = '';
  let searchDebounceTimeout = null;
  let cachedProperties = [];

  // Formatador de Moeda (€)
  const currencyFormatter = new Intl.NumberFormat('pt-PT', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  });

  // 3. Atualização da Interface do Imóvel em Foco
  function renderFocusProperty(property) {
    if (!focusPropTitle || !focusPropSubtitle) return;

    if (property) {
      const priceFormatted = currencyFormatter.format(property.preco);
      focusPropTitle.textContent = `${property.tipologia} • ${property.titulo}`;
      focusPropSubtitle.textContent = `${priceFormatted} • ${property.concelho || property.distrito || 'Portugal'}`;
    } else {
      focusPropTitle.textContent = 'Nenhum imóvel em foco';
      focusPropSubtitle.textContent = 'Toque aqui para selecionar da carteira';
    }
  }

  // 4. Gestão da Sessão e Cabeçalho
  function updateAuthUI(user) {
    if (user) {
      if (userBadge) {
        userBadge.textContent = `${user.nome} • ${user.role.toUpperCase()}`;
        userBadge.className = user.role === 'diretor'
          ? 'status-pill status-pill-notarized'
          : 'status-pill status-pill-secondary';
      }
      if (btnLogout) btnLogout.style.display = 'inline-flex';
      if (authModal) authModal.style.display = 'none';

      // Carrega o imóvel em foco ou inicializa carteira
      initPortfolioContext();
      checkMorningAnniversaries();
    } else {
      if (userBadge) {
        userBadge.textContent = 'Não autenticado';
        userBadge.className = 'status-pill status-pill-error';
      }
      if (btnLogout) btnLogout.style.display = 'none';
      if (authModal) authModal.style.display = 'flex';
      renderFocusProperty(null);
    }
  }

  // 5. Inicialização do Contexto da Carteira após Autenticação
  async function initPortfolioContext() {
    const savedProp = Api.getSelectedProperty();
    if (savedProp) {
      renderFocusProperty(savedProp);
    } else {
      // Busca imóveis ativos para definir o primeiro como padrão se houver
      try {
        const res = await Api.getProperties({ status: 'Ativo', limit: 1 });
        if (res.properties && res.properties.length > 0) {
          Api.setSelectedProperty(res.properties[0]);
          renderFocusProperty(res.properties[0]);
        } else {
          renderFocusProperty(null);
        }
      } catch (e) {
        console.warn('[Portfolio] Não foi possível carregar o imóvel padrão:', e);
      }
    }
  }

  // 6. Carregamento e Renderização da Carteira
  async function loadPortfolioList() {
    if (!portfolioListContainer) return;
    portfolioListContainer.innerHTML = '<p style="text-align: center; color: var(--color-outline); font-size: 13px; padding: 24px 0;">A carregar imóveis...</p>';

    try {
      const params = {};
      if (currentFilterStatus) params.status = currentFilterStatus;
      const searchTerm = propertySearchInput ? propertySearchInput.value.trim() : '';
      if (searchTerm) params.busca = searchTerm;

      const response = await Api.getProperties(params);
      cachedProperties = response.properties || [];

      if (portfolioCountLabel) {
        portfolioCountLabel.textContent = `${response.total} ${response.total === 1 ? 'imóvel cadastrado' : 'imóveis cadastrados'}`;
      }

      renderPortfolioCards(cachedProperties);
    } catch (err) {
      portfolioListContainer.innerHTML = `<p style="text-align: center; color: var(--color-error); font-size: 13px; padding: 24px 0;">Erro ao carregar carteira: ${err.message}</p>`;
    }
  }

  function getStatusBadgeHtml(status) {
    if (status === 'Ativo') {
      return '<span class="status-pill status-pill-notarized" style="font-size: 11px;">Ativo</span>';
    } else if (status === 'Reservado') {
      return '<span class="status-pill status-pill-secondary" style="font-size: 11px;">Reservado</span>';
    } else if (status === 'Vendido') {
      return '<span class="status-pill" style="background: var(--color-surface-container-high); color: var(--color-primary); font-size: 11px;">Vendido</span>';
    }
    return `<span class="status-pill" style="font-size: 11px;">${status}</span>`;
  }

  function renderPortfolioCards(properties) {
    if (!portfolioListContainer) return;

    if (!properties || properties.length === 0) {
      portfolioListContainer.innerHTML = `
        <div style="text-align: center; padding: 32px 16px; color: var(--color-outline);">
          <p style="font-size: 14px; font-weight: 500;">Nenhum imóvel encontrado.</p>
          <p style="font-size: 12px; margin-top: 4px;">Ajuste os filtros ou cadastre um novo imóvel na carteira.</p>
        </div>
      `;
      return;
    }

    const selectedProp = Api.getSelectedProperty();
    const selectedId = selectedProp ? selectedProp.id : null;

    portfolioListContainer.innerHTML = properties.map((p) => {
      const isSelected = p.id === selectedId;
      const priceFmt = currencyFormatter.format(p.preco);
      const locationText = [p.concelho, p.distrito].filter(Boolean).join(' • ') || 'Localização não especificada';

      return `
        <div class="property-card ${isSelected ? 'is-selected' : ''}" data-property-id="${p.id}">
          <div class="property-card-header">
            <div style="flex: 1; padding-right: 8px;">
              <span class="label-caps" style="color: var(--color-secondary);">${p.tipologia}${p.area_bruta ? ` • ${p.area_bruta} m²` : ''}</span>
              <h4 class="property-title">${p.titulo}</h4>
              <p class="property-location">${locationText}</p>
            </div>
            <div>
              ${getStatusBadgeHtml(p.status)}
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 6px;">
            <span class="property-price">${priceFmt}</span>
            <span style="font-size: 11px; color: var(--color-outline);">Consultor: ${p.consultor_nome || 'Agência'}</span>
          </div>

          <div class="property-actions-row">
            <button type="button" class="btn-card-action ${isSelected ? 'btn-card-primary' : ''} btn-select-focus" data-property-id="${p.id}">
              ${isSelected ? '✓ Em Foco' : 'Focar Imóvel'}
            </button>
            <button type="button" class="btn-card-action btn-change-status" data-property-id="${p.id}">
              Mudar Estado
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Eventos nos botões dos cartões
    portfolioListContainer.querySelectorAll('.btn-select-focus').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const pId = parseInt(btn.getAttribute('data-property-id'), 10);
        const prop = properties.find((item) => item.id === pId);
        if (prop) {
          Api.setSelectedProperty(prop);
          renderFocusProperty(prop);
          closeDrawer(drawerPortfolio);
        }
      });
    });

    portfolioListContainer.querySelectorAll('.btn-change-status').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const pId = parseInt(btn.getAttribute('data-property-id'), 10);
        const prop = properties.find((item) => item.id === pId);
        if (prop) {
          openTransitionModal(prop);
        }
      });
    });

    // Clique direto no card também seleciona o imóvel
    portfolioListContainer.querySelectorAll('.property-card').forEach((card) => {
      card.addEventListener('click', () => {
        const pId = parseInt(card.getAttribute('data-property-id'), 10);
        const prop = properties.find((item) => item.id === pId);
        if (prop) {
          Api.setSelectedProperty(prop);
          renderFocusProperty(prop);
          closeDrawer(drawerPortfolio);
        }
      });
    });
  }

  // 7. Abertura e Fechamento de Drawers e Modais
  function openDrawer(drawerElement) {
    if (drawerElement) {
      drawerElement.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeDrawer(drawerElement) {
    if (drawerElement) {
      drawerElement.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  // Abrir carteira
  function handleOpenPortfolio() {
    openDrawer(drawerPortfolio);
    loadPortfolioList();
  }

  if (propertySelectorCard) propertySelectorCard.addEventListener('click', handleOpenPortfolio);
  if (btnOpenPortfolio) btnOpenPortfolio.addEventListener('click', handleOpenPortfolio);
  if (navCarteira) navCarteira.addEventListener('click', handleOpenPortfolio);
  if (btnClosePortfolio) btnClosePortfolio.addEventListener('click', () => closeDrawer(drawerPortfolio));

  // Fechar ao clicar no backdrop
  [drawerPortfolio, modalNewProperty, modalTransitionStatus, drawerCalculator, drawerVoiceVisit].forEach((overlay) => {
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          closeDrawer(overlay);
        }
      });
    }
  });

  // Filtros de status da carteira
  if (portfolioFilterBar) {
    portfolioFilterBar.querySelectorAll('.filter-chip-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        portfolioFilterBar.querySelectorAll('.filter-chip-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilterStatus = btn.getAttribute('data-status') || '';
        loadPortfolioList();
      });
    });
  }

  // Pesquisa de imóveis com debounce
  if (propertySearchInput) {
    propertySearchInput.addEventListener('input', () => {
      clearTimeout(searchDebounceTimeout);
      searchDebounceTimeout = setTimeout(() => {
        loadPortfolioList();
      }, 300);
    });
  }

  // 8. Modal de Novo Imóvel
  if (btnOpenNewProperty) {
    btnOpenNewProperty.addEventListener('click', () => {
      if (formNewProperty) formNewProperty.reset();
      if (newPropError) newPropError.style.display = 'none';
      openDrawer(modalNewProperty);
    });
  }

  if (btnCloseNewProperty) {
    btnCloseNewProperty.addEventListener('click', () => closeDrawer(modalNewProperty));
  }

  if (formNewProperty) {
    formNewProperty.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (newPropError) newPropError.style.display = 'none';
      btnSubmitNewProperty.disabled = true;
      btnSubmitNewProperty.textContent = 'A registar...';

      try {
        const payload = {
          titulo: document.getElementById('new-prop-title').value.trim(),
          tipologia: document.getElementById('new-prop-type').value,
          preco: parseFloat(document.getElementById('new-prop-price').value),
          regiao_fiscal: document.getElementById('new-prop-region').value,
          area_bruta: document.getElementById('new-prop-area').value ? parseFloat(document.getElementById('new-prop-area').value) : null,
          concelho: document.getElementById('new-prop-concelho').value.trim() || null,
          morada: document.getElementById('new-prop-address').value.trim() || null,
          descricao: document.getElementById('new-prop-desc').value.trim() || null,
          nome_proprietario: document.getElementById('new-prop-owner-name').value.trim(),
          telefone_proprietario: document.getElementById('new-prop-owner-phone').value.trim(),
        };

        const created = await Api.createProperty(payload);
        closeDrawer(modalNewProperty);
        Api.setSelectedProperty(created);
        renderFocusProperty(created);
        loadPortfolioList();
      } catch (err) {
        if (newPropError) {
          newPropError.textContent = err.message || 'Erro ao criar imóvel.';
          newPropError.style.display = 'block';
        }
      } finally {
        btnSubmitNewProperty.disabled = false;
        btnSubmitNewProperty.textContent = 'Criar Imóvel';
      }
    });
  }

  // 9. Modal de Transição de Estado da Máquina de Estados
  function openTransitionModal(property) {
    if (!modalTransitionStatus || !transitionPropertyId) return;

    transitionPropertyId.value = property.id;
    if (transitionPropTitleLabel) {
      transitionPropTitleLabel.textContent = `${property.titulo} (Estado atual: ${property.status})`;
    }

    if (selectTransitionTarget) {
      selectTransitionTarget.value = property.status;
      toggleSoldClosingInputs(property.status === 'Vendido');
    }

    if (soldBuyerName) soldBuyerName.value = property.nome_comprador || '';
    if (soldBuyerPhone) soldBuyerPhone.value = property.telefone_comprador || '';
    if (soldBuyerDate) soldBuyerDate.value = property.data_escritura || '';
    if (transitionError) transitionError.style.display = 'none';

    openDrawer(modalTransitionStatus);
  }

  function toggleSoldClosingInputs(isSold) {
    if (!soldClosingInputs) return;
    if (isSold) {
      soldClosingInputs.classList.add('visible');
      if (soldBuyerName) soldBuyerName.required = true;
      if (soldBuyerPhone) soldBuyerPhone.required = true;
      if (soldBuyerDate) soldBuyerDate.required = true;
    } else {
      soldClosingInputs.classList.remove('visible');
      if (soldBuyerName) soldBuyerName.required = false;
      if (soldBuyerPhone) soldBuyerPhone.required = false;
      if (soldBuyerDate) soldBuyerDate.required = false;
    }
  }

  if (selectTransitionTarget) {
    selectTransitionTarget.addEventListener('change', (e) => {
      toggleSoldClosingInputs(e.target.value === 'Vendido');
    });
  }

  if (btnCloseTransition) {
    btnCloseTransition.addEventListener('click', () => closeDrawer(modalTransitionStatus));
  }

  if (formTransitionStatus) {
    formTransitionStatus.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (transitionError) transitionError.style.display = 'none';
      btnSubmitTransition.disabled = true;
      btnSubmitTransition.textContent = 'A processar...';

      try {
        const propId = parseInt(transitionPropertyId.value, 10);
        const novoStatus = selectTransitionTarget.value;

        const payload = {
          novo_status: novoStatus,
        };

        if (novoStatus === 'Vendido') {
          payload.nome_comprador = soldBuyerName ? soldBuyerName.value.trim() : '';
          payload.telefone_comprador = soldBuyerPhone ? soldBuyerPhone.value.trim() : '';
          payload.data_escritura = soldBuyerDate ? soldBuyerDate.value : null;
        }

        const updated = await Api.transitionPropertyStatus(propId, payload);
        closeDrawer(modalTransitionStatus);

        // Se o imóvel alterado for o que está em foco, atualiza a visualização
        const currentFocused = Api.getSelectedProperty();
        if (currentFocused && currentFocused.id === updated.id) {
          Api.setSelectedProperty(updated);
          renderFocusProperty(updated);
        }

        loadPortfolioList();
        if (typeof loadContactsList === 'function') {
          loadContactsList();
        }
        if (typeof checkMorningAnniversaries === 'function') {
          checkMorningAnniversaries();
        }
      } catch (err) {
        if (transitionError) {
          transitionError.textContent = err.message || 'Erro ao alterar estado do imóvel.';
          transitionError.style.display = 'block';
        }
      } finally {
        btnSubmitTransition.disabled = false;
        btnSubmitTransition.textContent = 'Confirmar Alteração';
      }
    });
  }

  // ==========================================================================
  // 10. Módulo da Calculadora Visual de Viabilidade Financeira (Fase 5)
  // ==========================================================================
  const btnOpenCalculator = document.getElementById('btn-open-calculator');
  const navCalculadora = document.getElementById('nav-calculadora');
  const drawerCalculator = document.getElementById('drawer-calculator');
  const btnCloseCalculator = document.getElementById('btn-close-calculator');

  // Contexto do Imóvel na Calculadora
  const calcContextBar = document.getElementById('calc-context-bar');
  const calcFocusTitle = document.getElementById('calc-focus-title');
  const btnApplyFocusProp = document.getElementById('btn-apply-focus-prop');

  // Entradas da Calculadora
  const calcTipoBtns = document.querySelectorAll('#calc-tipo-control .segmented-btn');
  const calcRegiaoBtns = document.querySelectorAll('#calc-regiao-control .segmented-btn');
  const calcToggleJovem = document.getElementById('calc-toggle-jovem');
  const calcJovemBox = document.getElementById('calc-jovem-box');
  const calcValorImovel = document.getElementById('calc-valor-imovel');
  const calcValorFormatted = document.getElementById('calc-valor-formatted');
  const calcShortcutChips = document.querySelectorAll('.calc-shortcut-chip');
  const calcRangeEntrada = document.getElementById('calc-range-entrada');
  const calcPercentualLabel = document.getElementById('calc-percentual-label');
  const calcEntradaValorLabel = document.getElementById('calc-entrada-valor-label');
  const calcMontanteFinanciadoLabel = document.getElementById('calc-montante-financiado-label');
  const calcPrazo = document.getElementById('calc-prazo');
  const calcTaxa = document.getElementById('calc-taxa');

  // Saídas e Resultados
  const calcResultPmt = document.getElementById('calc-result-pmt');
  const calcPmtDetails = document.getElementById('calc-pmt-details');
  const calcPoupancaBadge = document.getElementById('calc-poupanca-badge');
  const calcPoupancaValor = document.getElementById('calc-poupanca-valor');
  const calcResultImt = document.getElementById('calc-result-imt');
  const calcImtTag = document.getElementById('calc-imt-tag');
  const calcResultSeloCompra = document.getElementById('calc-result-selo-compra');
  const calcRowSeloFinanciamento = document.getElementById('calc-row-selo-financiamento');
  const calcResultSeloFinanciamento = document.getElementById('calc-result-selo-financiamento');
  const calcResultTotalImpostos = document.getElementById('calc-result-total-impostos');
  const calcResultCapitalInicial = document.getElementById('calc-result-capital-inicial');
  const btnCalcWhatsapp = document.getElementById('btn-calc-whatsapp');
  const btnCalcCopy = document.getElementById('btn-calc-copy');
  const btnCalcCopyText = document.getElementById('btn-calc-copy-text');

  // Estado Local da Calculadora
  const calcState = {
    tipo: 'hpp',
    regiao: 'continente',
    isJovem: false,
    valorImovel: 350000,
    percentualEntrada: 20,
    prazoAnos: 30,
    taxaJuroAnual: 3.5,
    lastSimulation: null
  };

  function updateCalculatorView() {
    if (!calcValorImovel) return;

    // Atualiza o estado a partir dos inputs
    const valor = parseFloat(calcValorImovel.value) || 0;
    calcState.valorImovel = valor;
    calcState.percentualEntrada = parseInt(calcRangeEntrada ? calcRangeEntrada.value : 20, 10) || 20;
    calcState.prazoAnos = parseInt(calcPrazo ? calcPrazo.value : 30, 10) || 30;
    calcState.taxaJuroAnual = parseFloat(calcTaxa ? calcTaxa.value : 3.5) || 0;
    calcState.isJovem = Boolean(calcToggleJovem && calcToggleJovem.checked);

    if (calcValorFormatted) {
      calcValorFormatted.textContent = Calculator.formatCurrency(valor);
    }

    if (calcPercentualLabel) {
      calcPercentualLabel.textContent = `${calcState.percentualEntrada}%`;
    }

    // Executa a simulação matemática e fiscal completa
    const sim = Calculator.simulate({
      valorImovel: calcState.valorImovel,
      tipo: calcState.tipo,
      regiao: calcState.regiao,
      isJovem: calcState.isJovem,
      percentualEntrada: calcState.percentualEntrada,
      prazoAnos: calcState.prazoAnos,
      taxaJuroAnual: calcState.taxaJuroAnual
    });
    calcState.lastSimulation = sim;

    // Atualiza labels de financiamento
    if (calcEntradaValorLabel) {
      calcEntradaValorLabel.textContent = Calculator.formatCurrency(sim.valorEntrada);
    }
    if (calcMontanteFinanciadoLabel) {
      calcMontanteFinanciadoLabel.textContent = Calculator.formatCurrency(sim.montanteFinanciado);
    }

    // Prestação bancária (Price)
    if (calcResultPmt) {
      calcResultPmt.innerHTML = `${Calculator.formatCurrency(sim.financiamento.prestacaoMensal)} <span style="font-size: 14px; font-weight: 400; color: var(--color-outline);">/ mês</span>`;
    }
    if (calcPmtDetails) {
      calcPmtDetails.textContent = `${sim.prazoAnos} anos (${sim.financiamento.numeroPrestacoes} prestações) • TAN ${sim.taxaJuroAnual.toFixed(2)}%`;
    }

    // IMT e Tags de Isenção
    if (calcResultImt) {
      calcResultImt.textContent = Calculator.formatCurrency(sim.imt.valorIMT);
    }
    if (calcImtTag) {
      if (sim.imt.isencaoTotal) {
        calcImtTag.textContent = sim.isJovem ? 'Isenção Jovem' : 'Isento';
        calcImtTag.style.display = 'inline-block';
      } else if (sim.imt.isencaoParcial) {
        calcImtTag.textContent = 'Parcial Jovem';
        calcImtTag.style.display = 'inline-block';
      } else {
        calcImtTag.style.display = 'none';
      }
    }

    // Imposto do Selo
    if (calcResultSeloCompra) {
      calcResultSeloCompra.textContent = Calculator.formatCurrency(sim.seloCompra.valorSelo);
    }
    if (calcResultSeloFinanciamento) {
      calcResultSeloFinanciamento.textContent = Calculator.formatCurrency(sim.seloFinanciamento);
    }
    if (calcRowSeloFinanciamento) {
      calcRowSeloFinanciamento.style.display = sim.montanteFinanciado > 0 ? 'flex' : 'none';
    }

    // Totais Fiscais e Capital Próprio Inicial
    if (calcResultTotalImpostos) {
      calcResultTotalImpostos.textContent = Calculator.formatCurrency(sim.totais.totalImpostos);
    }
    if (calcResultCapitalInicial) {
      calcResultCapitalInicial.textContent = Calculator.formatCurrency(sim.totais.capitalInicialNecessario);
    }

    // Badge de Poupança IMT Jovem
    if (calcPoupancaBadge && calcPoupancaValor) {
      if (sim.totais.totalPoupancaJovem > 0) {
        calcPoupancaValor.textContent = Calculator.formatCurrency(sim.totais.totalPoupancaJovem);
        calcPoupancaBadge.style.display = 'flex';
      } else {
        calcPoupancaBadge.style.display = 'none';
      }
    }
  }

  function syncCalculatorWithFocusedProperty() {
    const focused = Api.getSelectedProperty();
    if (focused && calcContextBar && calcFocusTitle) {
      calcFocusTitle.textContent = `${focused.tipologia} • ${focused.titulo} (${currencyFormatter.format(focused.preco)})`;
      calcContextBar.style.display = 'flex';
    } else if (calcContextBar) {
      calcContextBar.style.display = 'none';
    }
  }

  function applyFocusedPropertyToCalculator() {
    const focused = Api.getSelectedProperty();
    if (!focused) return;

    if (calcValorImovel && focused.preco) {
      calcValorImovel.value = focused.preco;
    }

    // Ajusta região fiscal se disponível
    if (focused.regiao_fiscal) {
      const reg = focused.regiao_fiscal.toLowerCase();
      calcRegiaoBtns.forEach((btn) => {
        if (btn.getAttribute('data-regiao') === reg) {
          btn.click();
        }
      });
    }

    updateCalculatorView();
  }

  // Ouvintes de Seleção Segmentada (Tipo de Imóvel e Região)
  calcTipoBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      calcTipoBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      calcState.tipo = btn.getAttribute('data-tipo');

      // Se for habitação secundária, desabilita visualmente o benefício IMT Jovem
      if (calcJovemBox) {
        if (calcState.tipo === 'secundaria') {
          calcJovemBox.style.opacity = '0.5';
          calcJovemBox.style.pointerEvents = 'none';
          if (calcToggleJovem) calcToggleJovem.checked = false;
        } else {
          calcJovemBox.style.opacity = '1';
          calcJovemBox.style.pointerEvents = 'auto';
        }
      }

      updateCalculatorView();
    });
  });

  calcRegiaoBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      calcRegiaoBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      calcState.regiao = btn.getAttribute('data-regiao');
      updateCalculatorView();
    });
  });

  // Toggle IMT Jovem
  if (calcToggleJovem) {
    calcToggleJovem.addEventListener('change', () => {
      if (calcJovemBox) {
        calcJovemBox.classList.toggle('is-active', calcToggleJovem.checked);
      }
      updateCalculatorView();
    });
  }

  // Inputs e Sliders Reativos Instantâneos
  if (calcValorImovel) {
    calcValorImovel.addEventListener('input', updateCalculatorView);
  }

  calcShortcutChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const val = chip.getAttribute('data-val');
      if (calcValorImovel && val) {
        calcValorImovel.value = val;
        updateCalculatorView();
      }
    });
  });

  if (calcRangeEntrada) {
    calcRangeEntrada.addEventListener('input', updateCalculatorView);
  }

  if (calcPrazo) {
    calcPrazo.addEventListener('change', updateCalculatorView);
  }

  if (calcTaxa) {
    calcTaxa.addEventListener('input', updateCalculatorView);
  }

  if (btnApplyFocusProp) {
    btnApplyFocusProp.addEventListener('click', applyFocusedPropertyToCalculator);
  }

  // Abertura e Fecho do Drawer da Calculadora
  function openCalculator() {
    syncCalculatorWithFocusedProperty();
    updateCalculatorView();
    openDrawer(drawerCalculator);
  }

  if (btnOpenCalculator) {
    btnOpenCalculator.addEventListener('click', openCalculator);
  }

  if (navCalculadora) {
    navCalculadora.addEventListener('click', openCalculator);
  }

  if (btnCloseCalculator) {
    btnCloseCalculator.addEventListener('click', () => closeDrawer(drawerCalculator));
  }

  // Partilha no WhatsApp
  if (btnCalcWhatsapp) {
    btnCalcWhatsapp.addEventListener('click', () => {
      if (!calcState.lastSimulation) updateCalculatorView();
      const focused = Api.getSelectedProperty();
      const propTitle = focused ? `${focused.tipologia} • ${focused.titulo}` : '';
      const text = Calculator.generateWhatsAppText(calcState.lastSimulation, propTitle);
      const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
      window.open(url, '_blank');
    });
  }

  // Cópia para Clipboard
  if (btnCalcCopy) {
    btnCalcCopy.addEventListener('click', async () => {
      if (!calcState.lastSimulation) updateCalculatorView();
      const focused = Api.getSelectedProperty();
      const propTitle = focused ? `${focused.tipologia} • ${focused.titulo}` : '';
      const text = Calculator.generateWhatsAppText(calcState.lastSimulation, propTitle);

      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          // Fallback para textarea temporário
          const ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }

        if (btnCalcCopyText) {
          const original = btnCalcCopyText.textContent;
          btnCalcCopyText.textContent = '✓ Simulação Copiada!';
          btnCalcCopy.style.borderColor = 'var(--color-notarized)';
          btnCalcCopy.style.color = 'var(--color-notarized)';
          setTimeout(() => {
            btnCalcCopyText.textContent = original;
            btnCalcCopy.style.borderColor = '';
            btnCalcCopy.style.color = '';
          }, 2000);
        }
      } catch (err) {
        console.warn('[Calculadora] Falha ao copiar texto:', err);
      }
    });
  }

  // ==========================================================================
  // 11. Módulo de Feedback de Visita por Voz (30s) e Human-in-the-Loop (Fase 6)
  // ==========================================================================
  const btnOpenVoice = document.getElementById('btn-open-voice');
  const navVisitas = document.getElementById('nav-visitas');
  const drawerVoiceVisit = document.getElementById('drawer-voice-visit');
  const btnCloseVoiceVisit = document.getElementById('btn-close-voice-visit');

  const voicePropertyBanner = document.getElementById('voice-property-banner');
  const voicePropTitle = document.getElementById('voice-prop-title');
  const voicePropOwner = document.getElementById('voice-prop-owner');
  const btnChangeVoiceProp = document.getElementById('btn-change-voice-prop');
  const voiceNoPropAlert = document.getElementById('voice-no-prop-alert');
  const btnSelectPropForVoice = document.getElementById('btn-select-prop-for-voice');

  const voiceStageRecording = document.getElementById('voice-stage-recording');
  const voiceStageReview = document.getElementById('voice-stage-review');
  const btnModeMic = document.getElementById('btn-mode-mic');
  const btnModeText = document.getElementById('btn-mode-text');
  const voicePanelMic = document.getElementById('voice-panel-mic');
  const voicePanelText = document.getElementById('voice-panel-text');

  const voiceTimerLabel = document.getElementById('voice-timer-label');
  const voiceProgressBar = document.getElementById('voice-progress-bar');
  const btnAudioTrigger = document.getElementById('btn-audio-trigger');
  const voiceStatusText = document.getElementById('voice-status-text');
  const voiceLiveTranscriptBox = document.getElementById('voice-live-transcript-box');
  const voiceLiveTranscriptText = document.getElementById('voice-live-transcript-text');
  const btnStopAndReview = document.getElementById('btn-stop-and-review');
  const btnCancelVoice = document.getElementById('btn-cancel-voice');
  const btnDemoVoiceSim = document.getElementById('btn-demo-voice-sim');
  const voiceManualText = document.getElementById('voice-manual-text');
  const btnProcessManualText = document.getElementById('btn-process-manual-text');

  // Elementos do Ecrã de Revisão (HITL)
  const hitlDurationLabel = document.getElementById('hitl-duration-label');
  const formHitlReview = document.getElementById('form-hitl-review');
  const hitlNotesInput = document.getElementById('hitl-notes-input');
  const hitlInterestLabel = document.getElementById('hitl-interest-label');
  const hitlStarBtns = document.querySelectorAll('.hitl-star-btn');
  const hitlObjectionChipsGrid = document.getElementById('hitl-objection-chips-grid');
  const hitlObjectionsCount = document.getElementById('hitl-objections-count');
  const hitlClientName = document.getElementById('hitl-client-name');
  const hitlClientPhone = document.getElementById('hitl-client-phone');
  const hitlPreviewPhone = document.getElementById('hitl-preview-phone');
  const hitlPreviewText = document.getElementById('hitl-preview-text');
  const hitlError = document.getElementById('hitl-error');
  const btnHitlSaveAndWhatsapp = document.getElementById('btn-hitl-save-and-whatsapp');
  const btnHitlSaveOnly = document.getElementById('btn-hitl-save-only');
  const btnHitlBackRecord = document.getElementById('btn-hitl-back-record');

  // Estado Local do Módulo de Visita
  const voiceVisitState = {
    durationSeconds: 0,
    transcript: '',
    structuredNotes: '',
    interestLevel: 3,
    selectedTagIds: new Set(),
    selectedTagNames: new Set(),
    audioBase64: null,
    audioBlob: null,
    catalogTags: [],
    shouldOpenWhatsApp: true,
  };

  const interestDescriptions = {
    1: '1 - Sem Interesse / Descartado',
    2: '2 - Baixo / Reticente',
    3: '3 - Médio / Em Avaliação',
    4: '4 - Elevado / Forte Candidato',
    5: '5 - Proposta Iminente / Entusiasmo Total',
  };

  // Carrega tags corporativas da agência se necessário
  async function loadAgencyTags() {
    if (voiceVisitState.catalogTags.length > 0) return voiceVisitState.catalogTags;
    try {
      const tags = await Api.getObjectionTags();
      voiceVisitState.catalogTags = tags || [];
    } catch (err) {
      console.warn('[Visitas] Falha ao carregar tags de objeção:', err);
      // Fallback com tags essenciais
      voiceVisitState.catalogTags = [
        { id: 1, tag: 'Preço Elevado', categoria: 'preco' },
        { id: 2, tag: 'Área Inferior ao Esperado', categoria: 'dimensao' },
        { id: 3, tag: 'Ruído da Rua / Zona Movimentada', categoria: 'localizacao' },
        { id: 4, tag: 'Falta de Garagem / Estacionamento', categoria: 'caracteristica' },
        { id: 5, tag: 'Exposição Solar Fraca', categoria: 'caracteristica' },
        { id: 6, tag: 'Necessita de Obras Profundas', categoria: 'estado' },
        { id: 7, tag: 'Piso Elevado sem Elevador', categoria: 'caracteristica' },
      ];
    }
    return voiceVisitState.catalogTags;
  }

  function renderObjectionChips() {
    if (!hitlObjectionChipsGrid) return;
    if (!voiceVisitState.catalogTags.length) {
      hitlObjectionChipsGrid.innerHTML = '<span style="font-size: 12px; color: var(--color-outline);">Nenhuma tag cadastrada.</span>';
      return;
    }

    hitlObjectionChipsGrid.innerHTML = voiceVisitState.catalogTags.map((t) => {
      const isActive = voiceVisitState.selectedTagIds.has(t.id);
      return `
        <button type="button" class="objection-chip ${isActive ? 'active' : ''}" data-tag-id="${t.id}" data-tag-name="${t.tag}">
          ${t.tag}
        </button>
      `;
    }).join('');

    hitlObjectionChipsGrid.querySelectorAll('.objection-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const tId = parseInt(chip.getAttribute('data-tag-id'), 10);
        const tName = chip.getAttribute('data-tag-name');
        if (voiceVisitState.selectedTagIds.has(tId)) {
          voiceVisitState.selectedTagIds.delete(tId);
          voiceVisitState.selectedTagNames.delete(tName);
          chip.classList.remove('active');
        } else {
          voiceVisitState.selectedTagIds.add(tId);
          voiceVisitState.selectedTagNames.add(tName);
          chip.classList.add('active');
        }

        if (hitlObjectionsCount) {
          const c = voiceVisitState.selectedTagIds.size;
          hitlObjectionsCount.textContent = `${c} ${c === 1 ? 'selecionada' : 'selecionadas'}`;
        }
        updateHitlWhatsAppPreview();
      });
    });

    if (hitlObjectionsCount) {
      const c = voiceVisitState.selectedTagIds.size;
      hitlObjectionsCount.textContent = `${c} ${c === 1 ? 'selecionada' : 'selecionadas'}`;
    }
  }

  function updateHitlInterestUI(level) {
    voiceVisitState.interestLevel = level;
    hitlStarBtns.forEach((btn) => {
      const bLevel = parseInt(btn.getAttribute('data-level'), 10);
      btn.classList.toggle('active', bLevel === level);
    });

    if (hitlInterestLabel) {
      hitlInterestLabel.textContent = interestDescriptions[level] || `${level} de 5`;
    }
    updateHitlWhatsAppPreview();
  }

  function updateHitlWhatsAppPreview() {
    const focused = Api.getSelectedProperty();
    const user = Api.getUser();
    const notes = hitlNotesInput ? hitlNotesInput.value.trim() : '';

    const text = AudioRecorder.generateWhatsAppFeedback({
      propriedade: focused,
      consultorNome: user ? user.nome : 'Consultor Imobiliário',
      nivelInteresse: voiceVisitState.interestLevel,
      notasEstruturadas: notes,
      objectionNames: Array.from(voiceVisitState.selectedTagNames),
    });

    if (hitlPreviewText) {
      hitlPreviewText.textContent = text;
    }

    if (hitlPreviewPhone && focused) {
      hitlPreviewPhone.textContent = focused.telefone_proprietario
        ? `WhatsApp: ${focused.telefone_proprietario}`
        : 'Sem telemóvel cadastrado';
    }
  }

  function transitionToReviewStage(data) {
    if (voiceStageRecording) voiceStageRecording.style.display = 'none';
    if (voiceStageReview) voiceStageReview.style.display = 'block';

    voiceVisitState.durationSeconds = data.audio_duracao_segundos || 0;
    voiceVisitState.transcript = data.transcricao || '';
    voiceVisitState.structuredNotes = data.notas_estruturadas || data.transcricao || '';

    if (hitlDurationLabel) {
      hitlDurationLabel.textContent = voiceVisitState.durationSeconds > 0
        ? `Áudio: ${voiceVisitState.durationSeconds}s gravados`
        : 'Entrada escrita de notas';
    }

    if (hitlNotesInput) {
      hitlNotesInput.value = voiceVisitState.structuredNotes;
    }

    // Pré-seleciona nível de interesse retornado da IA/NLP
    updateHitlInterestUI(data.nivel_interesse || 3);

    // Pré-seleciona tags detectadas
    voiceVisitState.selectedTagIds.clear();
    voiceVisitState.selectedTagNames.clear();

    if (data.detected_tag_ids && data.detected_tag_ids.length > 0) {
      data.detected_tag_ids.forEach((id) => voiceVisitState.selectedTagIds.add(id));
    }
    if (data.detected_tags && data.detected_tags.length > 0) {
      data.detected_tags.forEach((name) => voiceVisitState.selectedTagNames.add(name));
    }

    // Se as tags foram detectadas apenas por nome, busca os IDs correspondentes no catálogo
    if (voiceVisitState.selectedTagNames.size > 0 && voiceVisitState.catalogTags.length > 0) {
      voiceVisitState.catalogTags.forEach((t) => {
        for (const name of voiceVisitState.selectedTagNames) {
          if (name.toLowerCase() === t.tag.toLowerCase()) {
            voiceVisitState.selectedTagIds.add(t.id);
          }
        }
      });
    }

    renderObjectionChips();
    updateHitlWhatsAppPreview();
  }

  function resetToRecordingStage() {
    if (voiceStageRecording) voiceStageRecording.style.display = 'block';
    if (voiceStageReview) voiceStageReview.style.display = 'none';

    if (voiceTimerLabel) voiceTimerLabel.textContent = '00:00';
    if (voiceProgressBar) voiceProgressBar.style.width = '0%';
    if (voiceStatusText) {
      voiceStatusText.textContent = 'Toque no botão para iniciar o relato da visita';
      voiceStatusText.style.color = 'var(--color-primary)';
    }
    if (btnAudioTrigger) {
      btnAudioTrigger.classList.remove('is-recording');
    }
    if (btnStopAndReview) btnStopAndReview.style.display = 'none';
    if (btnCancelVoice) btnCancelVoice.style.display = 'none';
    if (voiceLiveTranscriptBox) voiceLiveTranscriptBox.style.display = 'none';
    if (voiceLiveTranscriptText) voiceLiveTranscriptText.textContent = '-';
  }

  function syncVoicePropertyContext() {
    const focused = Api.getSelectedProperty();
    if (focused) {
      if (voicePropertyBanner) voicePropertyBanner.style.display = 'flex';
      if (voiceNoPropAlert) voiceNoPropAlert.style.display = 'none';
      if (voicePropTitle) voicePropTitle.textContent = `${focused.tipologia} • ${focused.titulo}`;
      if (voicePropOwner) {
        voicePropOwner.textContent = `Proprietário: ${focused.nome_proprietario || 'Não informado'} (${focused.telefone_proprietario || 'Sem tel.'})`;
      }
    } else {
      if (voicePropertyBanner) voicePropertyBanner.style.display = 'none';
      if (voiceNoPropAlert) voiceNoPropAlert.style.display = 'block';
    }
  }

  async function openVoiceVisit() {
    syncVoicePropertyContext();
    await loadAgencyTags();
    resetToRecordingStage();
    openDrawer(drawerVoiceVisit);
  }

  if (btnOpenVoice) btnOpenVoice.addEventListener('click', openVoiceVisit);
  if (navVisitas) navVisitas.addEventListener('click', openVoiceVisit);
  if (btnCloseVoiceVisit) {
    btnCloseVoiceVisit.addEventListener('click', () => {
      AudioRecorder.cancelRecording();
      closeDrawer(drawerVoiceVisit);
    });
  }

  if (btnChangeVoiceProp || btnSelectPropForVoice) {
    const handler = () => {
      closeDrawer(drawerVoiceVisit);
      handleOpenPortfolio();
    };
    if (btnChangeVoiceProp) btnChangeVoiceProp.addEventListener('click', handler);
    if (btnSelectPropForVoice) btnSelectPropForVoice.addEventListener('click', handler);
  }

  // Alternador de Modo de Entrada (Microfone vs Digitação)
  if (btnModeMic && btnModeText) {
    btnModeMic.addEventListener('click', () => {
      btnModeMic.classList.add('active');
      btnModeText.classList.remove('active');
      if (voicePanelMic) voicePanelMic.style.display = 'block';
      if (voicePanelText) voicePanelText.style.display = 'none';
    });

    btnModeText.addEventListener('click', () => {
      btnModeText.classList.add('active');
      btnModeMic.classList.remove('active');
      if (voicePanelMic) voicePanelMic.style.display = 'none';
      if (voicePanelText) voicePanelText.style.display = 'block';
    });
  }

  // Callbacks do Gravador de Áudio
  AudioRecorder.onTick = (currentSeconds, remainingSeconds, percent) => {
    if (voiceTimerLabel) {
      const mins = String(Math.floor(currentSeconds / 60)).padStart(2, '0');
      const secs = String(currentSeconds % 60).padStart(2, '0');
      voiceTimerLabel.textContent = `${mins}:${secs}`;
    }
    if (voiceProgressBar) {
      voiceProgressBar.style.width = `${percent}%`;
    }
    if (voiceStatusText) {
      voiceStatusText.textContent = `A gravar relato (${remainingSeconds}s restantes)...`;
      voiceStatusText.style.color = 'var(--color-error)';
    }
  };

  AudioRecorder.onTranscript = (transcriptText) => {
    if (voiceLiveTranscriptBox && voiceLiveTranscriptText) {
      voiceLiveTranscriptBox.style.display = 'block';
      voiceLiveTranscriptText.textContent = `"${transcriptText}"`;
    }
  };

  AudioRecorder.onError = (err) => {
    if (voiceStatusText) {
      voiceStatusText.textContent = 'Acesso ao microfone indisponível. Utilize a aba "Digitar Notas" ou o botão Demo.';
      voiceStatusText.style.color = 'var(--color-error)';
    }
    if (btnAudioTrigger) btnAudioTrigger.classList.remove('is-recording');
    if (btnStopAndReview) btnStopAndReview.style.display = 'none';
  };

  AudioRecorder.onStop = async (result) => {
    if (btnAudioTrigger) btnAudioTrigger.classList.remove('is-recording');
    if (voiceStatusText) {
      voiceStatusText.textContent = 'Processando e estruturando notas da visita com IA...';
      voiceStatusText.style.color = 'var(--color-tertiary)';
    }

    const focused = Api.getSelectedProperty();

    try {
      // Dispara chamada para o endpoint de processamento semântico
      const processed = await Api.processVisitAudio({
        raw_text: result.transcript,
        audio_duracao_segundos: result.durationSeconds,
        audio_base64: result.audioBase64,
        property_id: focused ? focused.id : null,
      });

      transitionToReviewStage(processed);
    } catch (err) {
      console.warn('[Visitas] Processamento no servidor falhou ou offline. Utilizando parser local:', err);
      // Fallback local se o servidor estiver inacessível
      transitionToReviewStage({
        transcricao: result.transcript || 'Relato verbal da visita gravado em campo.',
        notas_estruturadas: result.transcript
          ? `• ${result.transcript}`
          : '• Visita realizada. Sem observações adicionais.',
        nivel_interesse: 3,
        audio_duracao_segundos: result.durationSeconds,
        detected_tags: [],
        detected_tag_ids: [],
      });
    }
  };

  // Botão de Gatilho de Gravação
  if (btnAudioTrigger) {
    btnAudioTrigger.addEventListener('click', async () => {
      const focused = Api.getSelectedProperty();
      if (!focused) {
        if (voiceNoPropAlert) voiceNoPropAlert.style.display = 'block';
        return;
      }

      if (!AudioRecorder.isRecording) {
        try {
          await AudioRecorder.startRecording();
          btnAudioTrigger.classList.add('is-recording');
          if (btnStopAndReview) btnStopAndReview.style.display = 'inline-block';
          if (btnCancelVoice) btnCancelVoice.style.display = 'inline-block';
        } catch (err) {
          console.warn('[AudioRecorder] Falha ao iniciar:', err);
        }
      } else {
        AudioRecorder.stopRecording();
      }
    });
  }

  if (btnStopAndReview) {
    btnStopAndReview.addEventListener('click', () => {
      AudioRecorder.stopRecording();
    });
  }

  if (btnCancelVoice) {
    btnCancelVoice.addEventListener('click', () => {
      AudioRecorder.cancelRecording();
      resetToRecordingStage();
    });
  }

  // Simulação Demo de Nota Oral (para homologação e testes ágeis)
  if (btnDemoVoiceSim) {
    btnDemoVoiceSim.addEventListener('click', async () => {
      const focused = Api.getSelectedProperty();
      const sampleText = "O cliente Dr. Silva adorou a sala e a luminosidade do terraço, mas achou o preço um pouco elevado e fez reparos ao ruído da rua. Tem forte intenção de avançar com proposta formal se ajustarmos o valor.";
      
      if (voiceStatusText) {
        voiceStatusText.textContent = 'Simulando áudio de 24s e estruturando notas...';
      }

      try {
        const processed = await Api.processVisitAudio({
          raw_text: sampleText,
          audio_duracao_segundos: 24,
          property_id: focused ? focused.id : null,
        });
        transitionToReviewStage(processed);
      } catch (e) {
        transitionToReviewStage({
          transcricao: sampleText,
          notas_estruturadas: "• O cliente Dr. Silva adorou a sala e a luminosidade do terraço.\n• Achou o preço um pouco elevado e fez reparos ao ruído da rua.\n• Tem forte intenção de avançar com proposta formal.",
          nivel_interesse: 4,
          audio_duracao_segundos: 24,
          detected_tags: ['Preço Elevado', 'Ruído da Rua / Zona Movimentada'],
          detected_tag_ids: [],
        });
      }
    });
  }

  // Processamento manual da aba "Digitar Notas"
  if (btnProcessManualText && voiceManualText) {
    btnProcessManualText.addEventListener('click', async () => {
      const raw = voiceManualText.value.trim();
      if (!raw) {
        alert('Por favor, introduza as notas ou relato da visita.');
        return;
      }
      const focused = Api.getSelectedProperty();

      btnProcessManualText.disabled = true;
      btnProcessManualText.textContent = 'A estruturar...';

      try {
        const processed = await Api.processVisitAudio({
          raw_text: raw,
          audio_duracao_segundos: 0,
          property_id: focused ? focused.id : null,
        });
        transitionToReviewStage(processed);
      } catch (err) {
        transitionToReviewStage({
          transcricao: raw,
          notas_estruturadas: `• ${raw}`,
          nivel_interesse: 3,
          audio_duracao_segundos: 0,
          detected_tags: [],
          detected_tag_ids: [],
        });
      } finally {
        btnProcessManualText.disabled = false;
        btnProcessManualText.textContent = 'Estruturar e Rever (Human-in-the-Loop)';
      }
    });
  }

  // Interatividade no Ecrã de Revisão HITL
  hitlStarBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const level = parseInt(btn.getAttribute('data-level'), 10);
      updateHitlInterestUI(level);
    });
  });

  if (hitlNotesInput) {
    hitlNotesInput.addEventListener('input', () => {
      updateHitlWhatsAppPreview();
    });
  }

  if (btnHitlBackRecord) {
    btnHitlBackRecord.addEventListener('click', () => {
      resetToRecordingStage();
    });
  }

  // Submissão do Ecrã de Revisão Human-in-the-Loop
  async function submitHitlReview(sendWhatsApp = true) {
    const focused = Api.getSelectedProperty();
    if (!focused) {
      if (hitlError) {
        hitlError.textContent = 'Selecione um imóvel antes de salvar a visita.';
        hitlError.style.display = 'block';
      }
      return;
    }

    const notes = hitlNotesInput ? hitlNotesInput.value.trim() : '';
    if (!notes) {
      if (hitlError) {
        hitlError.textContent = 'O resumo ou notas da visita não podem estar em branco.';
        hitlError.style.display = 'block';
      }
      return;
    }

    const payload = {
      property_id: focused.id,
      cliente_nome: hitlClientName ? hitlClientName.value.trim() : null,
      cliente_telefone: hitlClientPhone ? hitlClientPhone.value.trim() : null,
      audio_duracao_segundos: voiceVisitState.durationSeconds || null,
      transcricao: voiceVisitState.transcript || notes,
      notas_estruturadas: notes,
      nivel_interesse: voiceVisitState.interestLevel,
      objection_tag_ids: Array.from(voiceVisitState.selectedTagIds),
      feedback_enviado_proprietario: sendWhatsApp,
    };

    if (btnHitlSaveAndWhatsapp) btnHitlSaveAndWhatsapp.disabled = true;
    if (btnHitlSaveOnly) btnHitlSaveOnly.disabled = true;

    try {
      let created = null;

      // Se houver conexão de rede
      if (navigator.onLine) {
        created = await Api.createVisit(payload);
      } else {
        // Enfileira offline
        AudioRecorder.enqueueOfflineVisit(payload);
      }

      // Se solicitado disparo do WhatsApp, abre imediatamente o Deep Link
      if (sendWhatsApp) {
        const text = (created && created.whatsapp_feedback_text) || AudioRecorder.generateWhatsAppFeedback({
          propriedade: focused,
          consultorNome: Api.getUser() ? Api.getUser().nome : 'Consultor',
          nivelInteresse: payload.nivel_interesse,
          notasEstruturadas: payload.notas_estruturadas,
          objectionNames: Array.from(voiceVisitState.selectedTagNames),
        });

        const waUrl = (created && created.whatsapp_deep_link) || AudioRecorder.getWhatsAppDeepLink(
          focused.telefone_proprietario,
          text
        );
        window.open(waUrl, '_blank');
      }

      closeDrawer(drawerVoiceVisit);
      alert(sendWhatsApp
        ? '✓ Visita registrada com sucesso! A abrir WhatsApp com o feedback ao proprietário...'
        : '✓ Visita registrada com sucesso na carteira.');

    } catch (err) {
      console.warn('[Visitas] Erro ao registrar visita online, salvando na fila offline:', err);
      AudioRecorder.enqueueOfflineVisit(payload);

      if (sendWhatsApp) {
        const text = AudioRecorder.generateWhatsAppFeedback({
          propriedade: focused,
          consultorNome: Api.getUser() ? Api.getUser().nome : 'Consultor',
          nivelInteresse: payload.nivel_interesse,
          notasEstruturadas: payload.notas_estruturadas,
          objectionNames: Array.from(voiceVisitState.selectedTagNames),
        });
        const waUrl = AudioRecorder.getWhatsAppDeepLink(focused.telefone_proprietario, text);
        window.open(waUrl, '_blank');
      }

      closeDrawer(drawerVoiceVisit);
      alert('✓ Visita salva na fila offline do telemóvel. Será sincronizada assim que restabelecida a ligação.');
    } finally {
      if (btnHitlSaveAndWhatsapp) btnHitlSaveAndWhatsapp.disabled = false;
      if (btnHitlSaveOnly) btnHitlSaveOnly.disabled = false;
    }
  }

  if (formHitlReview) {
    formHitlReview.addEventListener('submit', (e) => {
      e.preventDefault();
      submitHitlReview(true);
    });
  }

  if (btnHitlSaveOnly) {
    btnHitlSaveOnly.addEventListener('click', () => {
      submitHitlReview(false);
    });
  }

  // =========================================================================
  // 11. GESTÃO DE SCRIPTS DE VÍDEO CURTO E TELEPROMPTER (FASE 7)
  // =========================================================================
  const btnOpenTeleprompter = document.getElementById('btn-open-teleprompter');
  const navScripts = document.getElementById('nav-scripts');
  const drawerScripts = document.getElementById('drawer-scripts');
  const btnCloseScripts = document.getElementById('btn-close-scripts');
  const btnCloseScriptsDrawer = document.getElementById('btn-close-scripts-drawer');

  const scriptsPropSubtitle = document.getElementById('scripts-prop-subtitle');
  const scriptsCardTipologia = document.getElementById('scripts-card-tipologia');
  const scriptsCardTitulo = document.getElementById('scripts-card-titulo');
  const scriptsCardLocalizacao = document.getElementById('scripts-card-localizacao');
  const scriptsCardPreco = document.getElementById('scripts-card-preco');

  const objButtons = document.querySelectorAll('.scripts-obj-btn');
  const btnRegenerateScript = document.getElementById('btn-regenerate-script');
  const scriptTempoEstimado = document.getElementById('script-tempo-estimado');
  const scriptTotalPalavras = document.getElementById('script-total-palavras');

  const scriptBlockGancho = document.getElementById('script-block-gancho');
  const scriptBlockDestaques = document.getElementById('script-block-destaques');
  const scriptBlockCta = document.getElementById('script-block-cta');
  const scriptErrorMsg = document.getElementById('script-error-msg');

  const btnLaunchPrompter = document.getElementById('btn-launch-prompter');
  const btnCopyScriptText = document.getElementById('btn-copy-script-text');

  // Elementos do Teleprompter
  const teleprompterModal = document.getElementById('teleprompter-modal');
  const prompterBtnClose = document.getElementById('prompter-btn-close');
  const prompterSpeedDown = document.getElementById('prompter-speed-down');
  const prompterSpeedUp = document.getElementById('prompter-speed-up');
  const prompterFontDown = document.getElementById('prompter-font-down');
  const prompterFontUp = document.getElementById('prompter-font-up');
  const prompterBtnRestart = document.getElementById('prompter-btn-restart');
  const teleprompterBtnPlayPause = document.getElementById('teleprompter-btn-play-pause');
  const prompterBtnCopy = document.getElementById('prompter-btn-copy');

  // Estado interno de Scripts
  let currentScriptObjective = 'angariacao';
  let currentLoadedScript = null;

  // Inicializa o módulo Teleprompter
  if (typeof Teleprompter !== 'undefined' && Teleprompter.init) {
    Teleprompter.init();
  }

  /**
   * Abre a gaveta de Scripts para o imóvel ativo ou selecionado.
   */
  async function openScriptsDrawer() {
    let prop = Api.getSelectedProperty();

    // Se não houver imóvel selecionado, tenta selecionar o primeiro da carteira
    if (!prop) {
      if (cachedProperties && cachedProperties.length > 0) {
        prop = cachedProperties[0];
        Api.setSelectedProperty(prop);
      } else {
        try {
          const resp = await Api.getProperties({ status: 'Ativo', limit: 1 });
          if (resp && resp.items && resp.items.length > 0) {
            prop = resp.items[0];
            Api.setSelectedProperty(prop);
          }
        } catch {
          // segue sem imóvel ou usa fallback
        }
      }
    }

    if (!prop) {
      alert('Por favor, selecione ou cadastre um imóvel ativo na carteira para gerar roteiros de vídeo.');
      openPortfolioDrawer();
      return;
    }

    // Renderiza dados do imóvel no card do script
    if (scriptsCardTipologia) scriptsCardTipologia.textContent = prop.tipologia || 'Imóvel';
    if (scriptsCardTitulo) scriptsCardTitulo.textContent = prop.titulo || 'Imóvel Exclusivo';
    if (scriptsCardLocalizacao) scriptsCardLocalizacao.textContent = prop.concelho || prop.morada || 'Portugal';
    if (scriptsCardPreco) {
      scriptsCardPreco.textContent = prop.preco ? currencyFormatter.format(prop.preco) : 'Sob Consulta';
    }
    if (scriptsPropSubtitle) {
      scriptsPropSubtitle.textContent = `Imóvel ativo #${prop.id}`;
    }

    if (drawerScripts) {
      drawerScripts.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }

    await loadScriptForCurrentSelection();
  }

  function closeScriptsDrawer() {
    if (drawerScripts) {
      drawerScripts.style.display = 'none';
      document.body.style.overflow = '';
    }
  }

  /**
   * Carrega ou gera o roteiro com base no imóvel e objetivo atual.
   */
  async function loadScriptForCurrentSelection() {
    const prop = Api.getSelectedProperty();
    if (!prop) return;

    if (scriptErrorMsg) scriptErrorMsg.style.display = 'none';

    // Estado visual de carregamento
    if (scriptBlockGancho) scriptBlockGancho.textContent = 'A gerar gancho magnético...';
    if (scriptBlockDestaques) scriptBlockDestaques.textContent = 'A selecionar os melhores destaques do imóvel...';
    if (scriptBlockCta) scriptBlockCta.textContent = 'A estruturar a chamada para ação...';

    try {
      // Tenta gerar via API
      const result = await Api.generateScript({
        property_id: prop.id,
        objetivo: currentScriptObjective,
        tom: 'sofisticado',
      });
      renderScriptData(result);
    } catch (err) {
      console.warn('Falha na API de scripts, utilizando motor offline de contingência:', err);
      // Fallback offline resiliente
      if (typeof Teleprompter !== 'undefined' && Teleprompter.generateOfflineScript) {
        const offlineResult = Teleprompter.generateOfflineScript(prop, currentScriptObjective);
        renderScriptData(offlineResult);
      } else {
        if (scriptErrorMsg) {
          scriptErrorMsg.textContent = 'Não foi possível gerar o roteiro.';
          scriptErrorMsg.style.display = 'block';
        }
      }
    }
  }

  /**
   * Renderiza os dados do roteiro gerado na interface.
   */
  function renderScriptData(scriptData) {
    currentLoadedScript = scriptData;

    if (scriptBlockGancho) scriptBlockGancho.textContent = scriptData.gancho || '-';
    if (scriptBlockDestaques) {
      const d1 = scriptData.destaque_1 || '';
      const d2 = scriptData.destaque_2 || '';
      scriptBlockDestaques.textContent = `${d1}\n\n${d2}`.trim() || '-';
    }
    if (scriptBlockCta) scriptBlockCta.textContent = scriptData.cta || '-';

    if (scriptTempoEstimado) {
      scriptTempoEstimado.textContent = `~${scriptData.tempo_estimado_segundos || 35}s`;
    }
    if (scriptTotalPalavras) {
      scriptTotalPalavras.textContent = `${scriptData.total_palavras || 0} palavras`;
    }
  }

  // Eventos de Abertura / Fechamento do Drawer de Scripts
  if (btnOpenTeleprompter) {
    btnOpenTeleprompter.addEventListener('click', openScriptsDrawer);
  }

  if (navScripts) {
    navScripts.addEventListener('click', openScriptsDrawer);
  }

  if (btnCloseScripts) {
    btnCloseScripts.addEventListener('click', closeScriptsDrawer);
  }

  if (btnCloseScriptsDrawer) {
    btnCloseScriptsDrawer.addEventListener('click', closeScriptsDrawer);
  }

  // Troca de Objetivos Comerciais (Angariação / Baixa de Preço / Open House)
  objButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      objButtons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentScriptObjective = btn.getAttribute('data-obj') || 'angariacao';
      loadScriptForCurrentSelection();
    });
  });

  // Botão de Regeneração
  if (btnRegenerateScript) {
    btnRegenerateScript.addEventListener('click', loadScriptForCurrentSelection);
  }

  // Lançar no Teleprompter
  if (btnLaunchPrompter) {
    btnLaunchPrompter.addEventListener('click', () => {
      if (!currentLoadedScript) {
        alert('Por favor, aguarde a geração do roteiro.');
        return;
      }
      closeScriptsDrawer();
      Teleprompter.loadScript(currentLoadedScript);
      Teleprompter.open();
    });
  }

  // Copiar Roteiro do Drawer
  if (btnCopyScriptText) {
    btnCopyScriptText.addEventListener('click', async () => {
      try {
        await Teleprompter.copyScriptToClipboard();
        const orig = btnCopyScriptText.textContent;
        btnCopyScriptText.textContent = '✓ Roteiro Copiado!';
        btnCopyScriptText.style.background = 'var(--color-secondary)';
        setTimeout(() => {
          btnCopyScriptText.textContent = orig;
          btnCopyScriptText.style.background = 'var(--color-primary)';
        }, 2000);
      } catch (err) {
        alert('Não foi possível copiar para a área de transferência.');
      }
    });
  }

  // Controles do Teleprompter
  if (prompterBtnClose) {
    prompterBtnClose.addEventListener('click', () => {
      Teleprompter.close();
    });
  }

  if (prompterSpeedDown) {
    prompterSpeedDown.addEventListener('click', () => Teleprompter.decreaseSpeed());
  }

  if (prompterSpeedUp) {
    prompterSpeedUp.addEventListener('click', () => Teleprompter.increaseSpeed());
  }

  if (prompterFontDown) {
    prompterFontDown.addEventListener('click', () => Teleprompter.decreaseFontSize());
  }

  if (prompterFontUp) {
    prompterFontUp.addEventListener('click', () => Teleprompter.increaseFontSize());
  }

  if (prompterBtnRestart) {
    prompterBtnRestart.addEventListener('click', () => Teleprompter.reset());
  }

  if (teleprompterBtnPlayPause) {
    teleprompterBtnPlayPause.addEventListener('click', () => Teleprompter.togglePlay());
  }

  if (prompterBtnCopy) {
    prompterBtnCopy.addEventListener('click', async () => {
      try {
        await Teleprompter.copyScriptToClipboard();
        const orig = prompterBtnCopy.textContent;
        prompterBtnCopy.textContent = '✓ Copiado';
        setTimeout(() => {
          prompterBtnCopy.textContent = orig;
        }, 1800);
      } catch {
        // silencia
      }
    });
  }

  // ==========================================================================
  // 12. Módulo de Esfera de Influência, Pós-Venda e Aniversários de Escritura (Fase 8)
  // ==========================================================================
  const anniversaryMorningBanner = document.getElementById('anniversary-morning-banner');
  const anniversaryBannerTitle = document.getElementById('anniversary-banner-title');
  const anniversaryBannerSubtitle = document.getElementById('anniversary-banner-subtitle');
  const btnBannerFelicitar = document.getElementById('btn-banner-felicitar');

  const btnOpenContacts = document.getElementById('btn-open-contacts');
  const navEsfera = document.getElementById('nav-esfera');
  const drawerContacts = document.getElementById('drawer-contacts');
  const btnCloseContacts = document.getElementById('btn-close-contacts');
  const contactsCountLabel = document.getElementById('contacts-count-label');
  const contactsSearchInput = document.getElementById('contacts-search-input');
  const contactsFilterBar = document.getElementById('contacts-filter-bar');
  const contactsListContainer = document.getElementById('contacts-list-container');

  const btnOpenNewContact = document.getElementById('btn-open-new-contact');
  const modalNewContact = document.getElementById('modal-new-contact');
  const btnCloseNewContact = document.getElementById('btn-close-new-contact');
  const formNewContact = document.getElementById('form-new-contact');
  const contactNameInput = document.getElementById('contact-name-input');
  const contactPhoneInput = document.getElementById('contact-phone-input');
  const contactEmailInput = document.getElementById('contact-email-input');
  const contactTypeSelect = document.getElementById('contact-type-select');
  const contactEscrituraDate = document.getElementById('contact-escritura-date');
  const contactNotesInput = document.getElementById('contact-notes-input');
  const newContactError = document.getElementById('new-contact-error');
  const btnSubmitNewContact = document.getElementById('btn-submit-new-contact');

  const modalContactWhatsapp = document.getElementById('modal-contact-whatsapp');
  const btnCloseContactWhatsapp = document.getElementById('btn-close-contact-whatsapp');
  const whatsappContactTargetLabel = document.getElementById('whatsapp-contact-target-label');
  const whatsappActiveContactId = document.getElementById('whatsapp-active-contact-id');
  const whatsappTemplateChips = document.getElementById('whatsapp-template-chips');
  const whatsappPreviewTextarea = document.getElementById('whatsapp-preview-textarea');
  const btnSendWhatsappNow = document.getElementById('btn-send-whatsapp-now');
  const btnCopyWhatsappText = document.getElementById('btn-copy-whatsapp-text');

  const modalConfirmAnonymize = document.getElementById('modal-confirm-anonymize');
  const btnCloseAnonymize = document.getElementById('btn-close-anonymize');
  const btnCancelAnonymize = document.getElementById('btn-cancel-anonymize');
  const btnExecuteAnonymize = document.getElementById('btn-execute-anonymize');
  const anonymizeTargetContactId = document.getElementById('anonymize-target-contact-id');
  const anonymizeTargetContactName = document.getElementById('anonymize-target-contact-name');

  let currentContactsFilter = '';
  let contactsSearchDebounce = null;
  let currentGeneratedWhatsappUrl = '';

  async function checkMorningAnniversaries() {
    if (!Api.isAuthenticated()) return;
    try {
      const res = await Api.getAnniversaryContacts();
      if (res && res.items && res.items.length > 0) {
        if (anniversaryMorningBanner) {
          anniversaryMorningBanner.style.display = 'block';
          const count = res.items.length;
          anniversaryBannerTitle.textContent = `${count} ${count === 1 ? 'Aniversário' : 'Aniversários'} de Escritura Hoje!`;
          const nomes = res.items.map(c => c.nome).slice(0, 2).join(', ');
          const extra = count > 2 ? ` e mais ${count - 2}` : '';
          anniversaryBannerSubtitle.textContent = `Celebração de ${nomes}${extra}. Envie os parabéns via WhatsApp.`;
        }

        // Notificação móvel matinal das 09:00 (Web Notification API)
        if ('Notification' in window) {
          if (Notification.permission === 'granted') {
            new Notification('Fecho - Aniversário de Escritura às 09:00', {
              body: `${res.items[0].nome} celebra aniversário de escritura hoje! Toque para felicitar.`,
              icon: '/static/img/screen.png'
            });
          } else if (Notification.permission === 'default') {
            Notification.requestPermission();
          }
        }
      } else {
        if (anniversaryMorningBanner) anniversaryMorningBanner.style.display = 'none';
      }
    } catch (e) {
      console.warn('[Contacts] Não foi possível verificar aniversários matinais:', e);
    }
  }

  async function loadContactsList() {
    if (!contactsListContainer) return;

    try {
      contactsListContainer.innerHTML = '<p style="text-align: center; color: var(--color-outline); font-size: 13px; padding: 24px 0;">A carregar contactos...</p>';

      const params = {};
      if (contactsSearchInput && contactsSearchInput.value.trim()) {
        params.q = contactsSearchInput.value.trim();
      }

      if (currentContactsFilter === 'aniversario') {
        params.apenas_aniversario_hoje = true;
      } else if (currentContactsFilter) {
        params.tipo = currentContactsFilter;
      }

      const res = await Api.getContacts(params);
      const items = res.items || [];

      if (contactsCountLabel) {
        contactsCountLabel.textContent = `${items.length} ${items.length === 1 ? 'contacto' : 'contactos'} na esfera`;
      }

      if (items.length === 0) {
        contactsListContainer.innerHTML = `
          <div style="text-align: center; padding: 36px 16px; color: var(--color-outline);">
            <p style="font-size: 14px; font-weight: 500;">Nenhum contacto encontrado</p>
            <p style="font-size: 12px; margin-top: 4px;">Registe um novo contacto ou concretize a venda de um imóvel para alimentar a esfera.</p>
          </div>
        `;
        return;
      }

      let html = '';
      for (const c of items) {
        const isAni = c.is_aniversario_hoje;
        const cardClass = isAni ? 'contact-card is-anniversary' : 'contact-card';
        const aniBadge = isAni
          ? `<span class="badge-anniversary">🎉 ${c.anos_escritura || 1} ${c.anos_escritura === 1 ? 'Ano' : 'Anos'} de Escritura Hoje!</span>`
          : '';
        const rgpdBadge = c.anonimizado ? '<span class="badge-anonymized">RGPD Anonimizado</span>' : '';
        const typeBadge = `<span class="badge-contact-type">${escapeHtml(c.tipo)}</span>`;

        let escrituraInfo = '';
        if (c.data_escritura) {
          const parts = c.data_escritura.split('-');
          const dataFmt = parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : c.data_escritura;
          escrituraInfo = `<span>📅 Escritura: <strong>${dataFmt}</strong></span>`;
        }

        const propInfo = c.property_titulo
          ? `<span>🏠 Imóvel: ${escapeHtml(c.property_titulo)}</span>`
          : '';

        let actionsHtml = '';
        if (!c.anonimizado) {
          actionsHtml = `
            <div class="contact-actions-row">
              <button type="button" class="btn-card-action btn-card-primary" data-action="whatsapp" data-id="${c.id}" data-name="${escapeHtml(c.nome)}">
                💬 WhatsApp (1 Toque)
              </button>
              <button type="button" class="btn-card-action" data-action="anonymize" data-id="${c.id}" data-name="${escapeHtml(c.nome)}" style="color: #b91c1c; border-color: rgba(185, 28, 28, 0.3);">
                ⚖️ Anonimizar RGPD
              </button>
            </div>
          `;
        } else {
          actionsHtml = `
            <div class="contact-actions-row">
              <span style="font-size: 11px; color: var(--color-outline);">Dados pessoais anonimizados pelo RGPD</span>
            </div>
          `;
        }

        html += `
          <div class="${cardClass}" data-contact-id="${c.id}">
            <div class="contact-card-header">
              <div>
                <h4 class="contact-name">${escapeHtml(c.nome)}</h4>
                <div class="contact-meta">
                  <span>📞 ${escapeHtml(c.telemovel)}</span>
                  ${rgpdBadge}
                </div>
              </div>
              <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                ${typeBadge}
                ${aniBadge}
              </div>
            </div>

            ${(escrituraInfo || propInfo) ? `
              <div class="contact-details" style="display: flex; flex-direction: column; gap: 2px;">
                ${propInfo}
                ${escrituraInfo}
              </div>
            ` : ''}

            ${c.notas ? `<p class="contact-details" style="font-style: italic; margin-top: 4px;">"${escapeHtml(c.notas)}"</p>` : ''}

            ${actionsHtml}
          </div>
        `;
      }

      contactsListContainer.innerHTML = html;
    } catch (e) {
      contactsListContainer.innerHTML = `<p style="text-align: center; color: var(--color-error); font-size: 13px; padding: 24px 0;">Erro ao carregar contactos: ${escapeHtml(e.message)}</p>`;
    }
  }

  async function openWhatsAppModal(contactId) {
    if (!modalContactWhatsapp) return;
    try {
      whatsappActiveContactId.value = contactId;
      whatsappPreviewTextarea.value = 'A gerar mensagem dinâmica...';
      btnSendWhatsappNow.disabled = true;

      const contact = await Api.getContact(contactId);
      if (whatsappContactTargetLabel) {
        whatsappContactTargetLabel.textContent = `${contact.nome} • ${contact.telemovel}`;
      }

      const defaultTemplate = contact.is_aniversario_hoje ? 'aniversario_escritura' : 'pos_venda_geral';
      setActiveWhatsAppTemplateChip(defaultTemplate);

      await generateAndDisplayWhatsAppMessage(contactId, defaultTemplate);
      openDrawer(modalContactWhatsapp);
    } catch (e) {
      alert(`Erro ao abrir modal de WhatsApp: ${e.message}`);
    }
  }

  function setActiveWhatsAppTemplateChip(template) {
    if (!whatsappTemplateChips) return;
    const chips = whatsappTemplateChips.querySelectorAll('.whatsapp-chip-btn');
    chips.forEach(btn => {
      if (btn.dataset.template === template) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  async function generateAndDisplayWhatsAppMessage(contactId, template) {
    try {
      whatsappPreviewTextarea.value = 'A preparar mensagem...';
      btnSendWhatsappNow.disabled = true;

      const res = await Api.generateContactWhatsApp(contactId, {
        tipo_mensagem: template
      });

      whatsappPreviewTextarea.value = res.texto;
      currentGeneratedWhatsappUrl = res.whatsapp_url;
      btnSendWhatsappNow.disabled = false;
    } catch (e) {
      whatsappPreviewTextarea.value = `Erro ao gerar mensagem: ${e.message}`;
      btnSendWhatsappNow.disabled = true;
    }
  }

  function openAnonymizeModal(contactId, contactName) {
    if (!modalConfirmAnonymize) return;
    anonymizeTargetContactId.value = contactId;
    anonymizeTargetContactName.textContent = contactName || 'este cliente';
    openDrawer(modalConfirmAnonymize);
  }

  // Event Listeners da Esfera de Influência
  if (btnOpenContacts) {
    btnOpenContacts.addEventListener('click', () => {
      openDrawer(drawerContacts);
      loadContactsList();
    });
  }

  if (navEsfera) {
    navEsfera.addEventListener('click', () => {
      openDrawer(drawerContacts);
      loadContactsList();
    });
  }

  if (btnCloseContacts) {
    btnCloseContacts.addEventListener('click', () => closeDrawer(drawerContacts));
  }

  if (btnBannerFelicitar) {
    btnBannerFelicitar.addEventListener('click', () => {
      currentContactsFilter = 'aniversario';
      if (contactsFilterBar) {
        const chips = contactsFilterBar.querySelectorAll('.filter-chip-btn');
        chips.forEach(c => c.classList.toggle('active', c.dataset.filter === 'aniversario'));
      }
      openDrawer(drawerContacts);
      loadContactsList();
    });
  }

  if (contactsSearchInput) {
    contactsSearchInput.addEventListener('input', () => {
      clearTimeout(contactsSearchDebounce);
      contactsSearchDebounce = setTimeout(() => {
        loadContactsList();
      }, 300);
    });
  }

  if (contactsFilterBar) {
    contactsFilterBar.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-chip-btn');
      if (!btn) return;
      contactsFilterBar.querySelectorAll('.filter-chip-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentContactsFilter = btn.dataset.filter || '';
      loadContactsList();
    });
  }

  // Ações nos Cards de Contatos (WhatsApp e RGPD)
  if (contactsListContainer) {
    contactsListContainer.addEventListener('click', (e) => {
      const waBtn = e.target.closest('[data-action="whatsapp"]');
      if (waBtn) {
        const id = parseInt(waBtn.dataset.id, 10);
        openWhatsAppModal(id);
        return;
      }

      const anonBtn = e.target.closest('[data-action="anonymize"]');
      if (anonBtn) {
        const id = parseInt(anonBtn.dataset.id, 10);
        const name = anonBtn.dataset.name;
        openAnonymizeModal(id, name);
        return;
      }
    });
  }

  // Modal Novo Contato
  if (btnOpenNewContact) {
    btnOpenNewContact.addEventListener('click', () => {
      if (formNewContact) formNewContact.reset();
      if (newContactError) newContactError.style.display = 'none';
      openDrawer(modalNewContact);
    });
  }

  if (btnCloseNewContact) {
    btnCloseNewContact.addEventListener('click', () => closeDrawer(modalNewContact));
  }

  if (formNewContact) {
    formNewContact.addEventListener('submit', async (e) => {
      e.preventDefault();
      newContactError.style.display = 'none';
      btnSubmitNewContact.disabled = true;
      btnSubmitNewContact.textContent = 'A gravar...';

      try {
        const payload = {
          nome: contactNameInput.value.trim(),
          telemovel: contactPhoneInput.value.trim(),
          email: contactEmailInput.value.trim() || null,
          tipo: contactTypeSelect.value,
          data_escritura: contactEscrituraDate.value || null,
          notas: contactNotesInput.value.trim() || null,
        };

        await Api.createContact(payload);
        closeDrawer(modalNewContact);
        loadContactsList();
        checkMorningAnniversaries();
      } catch (err) {
        newContactError.textContent = err.message || 'Erro ao cadastrar contacto.';
        newContactError.style.display = 'block';
      } finally {
        btnSubmitNewContact.disabled = false;
        btnSubmitNewContact.textContent = 'Gravar Contacto';
      }
    });
  }

  // Modal de WhatsApp
  if (btnCloseContactWhatsapp) {
    btnCloseContactWhatsapp.addEventListener('click', () => closeDrawer(modalContactWhatsapp));
  }

  if (whatsappTemplateChips) {
    whatsappTemplateChips.addEventListener('click', async (e) => {
      const chip = e.target.closest('.whatsapp-chip-btn');
      if (!chip) return;
      const template = chip.dataset.template;
      setActiveWhatsAppTemplateChip(template);

      const contactId = parseInt(whatsappActiveContactId.value, 10);
      if (contactId) {
        await generateAndDisplayWhatsAppMessage(contactId, template);
      }
    });
  }

  if (btnSendWhatsappNow) {
    btnSendWhatsappNow.addEventListener('click', () => {
      if (!currentGeneratedWhatsappUrl) return;
      window.open(currentGeneratedWhatsappUrl, '_blank');
    });
  }

  if (btnCopyWhatsappText) {
    btnCopyWhatsappText.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(whatsappPreviewTextarea.value);
        const orig = btnCopyWhatsappText.textContent;
        btnCopyWhatsappText.textContent = '✓ Copiado com Sucesso';
        setTimeout(() => {
          btnCopyWhatsappText.textContent = orig;
        }, 1800);
      } catch {
        alert('Texto copiado!');
      }
    });
  }

  // Modal Anonimização RGPD
  if (btnCloseAnonymize) {
    btnCloseAnonymize.addEventListener('click', () => closeDrawer(modalConfirmAnonymize));
  }

  if (btnCancelAnonymize) {
    btnCancelAnonymize.addEventListener('click', () => closeDrawer(modalConfirmAnonymize));
  }

  if (btnExecuteAnonymize) {
    btnExecuteAnonymize.addEventListener('click', async () => {
      const id = parseInt(anonymizeTargetContactId.value, 10);
      if (!id) return;

      btnExecuteAnonymize.disabled = true;
      btnExecuteAnonymize.textContent = 'A anonimizar...';

      try {
        await Api.anonymizeContact(id);
        closeDrawer(modalConfirmAnonymize);
        loadContactsList();
        checkMorningAnniversaries();
      } catch (err) {
        alert(`Erro ao anonimizar: ${err.message}`);
      } finally {
        btnExecuteAnonymize.disabled = false;
        btnExecuteAnonymize.textContent = 'Confirmar Anonimização';
      }
    });
  }

  // 13. Tratamento do Formulário de Login
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      loginError.style.display = 'none';
      btnSubmitLogin.disabled = true;
      btnSubmitLogin.textContent = 'A validar...';

      try {
        const email = loginEmailInput.value.trim();
        const password = loginPasswordInput.value;
        const result = await Api.login(email, password);
        updateAuthUI(result.user);
      } catch (err) {
        loginError.textContent = err.message || 'Erro de autenticação.';
        loginError.style.display = 'block';
      } finally {
        btnSubmitLogin.disabled = false;
        btnSubmitLogin.textContent = 'Iniciar Sessão';
      }
    });
  }

  // 11. Preenchimento de Demonstração
  if (btnDemoConsultor) {
    btnDemoConsultor.addEventListener('click', () => {
      loginEmailInput.value = 'consultor@fecho.pt';
      loginPasswordInput.value = 'senha_segura_consultor';
      loginForm.dispatchEvent(new Event('submit'));
    });
  }

  if (btnDemoDiretor) {
    btnDemoDiretor.addEventListener('click', () => {
      loginEmailInput.value = 'diretor@fecho.pt';
      loginPasswordInput.value = 'senha_segura_diretor';
      loginForm.dispatchEvent(new Event('submit'));
    });
  }

  // 12. Botão de Logout
  if (btnLogout) {
    btnLogout.addEventListener('click', () => {
      Api.logout();
      updateAuthUI(null);
    });
  }

  // 13. Ouvintes de Eventos Globais de Sessão e Imóveis
  window.addEventListener('fecho:unauthorized', () => {
    updateAuthUI(null);
  });

  window.addEventListener('fecho:logout', () => {
    updateAuthUI(null);
  });

  window.addEventListener('fecho:property_selected', (event) => {
    renderFocusProperty(event.detail);
  });

  // 14. Verificação de Sessão Inicial
  if (Api.isAuthenticated()) {
    try {
      const user = await Api.getMe();
      updateAuthUI(user);
    } catch {
      Api.logout();
      updateAuthUI(null);
    }
  } else {
    updateAuthUI(null);
  }
});
