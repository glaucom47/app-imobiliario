/**
 * Inicialização e Bootstrap Client-side - Fecho (fecho.pt)
 * Registro de Service Worker, gestão de sessão e autenticação na interface móvel.
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

  // 2. Elementos da Interface
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

  // 3. Atualização do cabeçalho com dados da sessão
  function updateAuthUI(user) {
    if (user) {
      if (userBadge) {
        userBadge.textContent = `${user.nome} • ${user.role.toUpperCase()}`;
        userBadge.className = user.role === 'diretor'
          ? 'status-pill status-pill-notarized'
          : 'status-pill status-pill-secondary';
      }
      if (btnLogout) {
        btnLogout.style.display = 'inline-flex';
      }
      if (authModal) {
        authModal.style.display = 'none';
      }
    } else {
      if (userBadge) {
        userBadge.textContent = 'Não autenticado';
        userBadge.className = 'status-pill status-pill-error';
      }
      if (btnLogout) {
        btnLogout.style.display = 'none';
      }
      if (authModal) {
        authModal.style.display = 'flex';
      }
    }
  }

  // 4. Verificação de sessão inicial
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

  // 5. Tratamento de submissão do formulário de login
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

  // 6. Preenchimento de demonstração de desenvolvimento
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

  // 7. Botão de Logout
  if (btnLogout) {
    btnLogout.addEventListener('click', () => {
      Api.logout();
      updateAuthUI(null);
    });
  }

  // 8. Ouvintes de eventos globais de sessão
  window.addEventListener('fecho:unauthorized', () => {
    updateAuthUI(null);
  });

  window.addEventListener('fecho:logout', () => {
    updateAuthUI(null);
  });
});
