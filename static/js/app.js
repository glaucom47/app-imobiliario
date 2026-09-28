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
  [drawerPortfolio, modalNewProperty, modalTransitionStatus].forEach((overlay) => {
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

  // 10. Tratamento do Formulário de Login
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
