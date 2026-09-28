/**
 * Inicialização e Bootstrap Client-side - Fecho (fecho.pt)
 * Registro do Service Worker para suporte PWA offline e inicialização da interface.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('[Fecho] Inicializando aplicação móvel PWA...');

  // Registro de Service Worker para suporte offline
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/sw.js')
        .then((registration) => {
          console.log('[PWA] Service Worker registrado com sucesso:', registration.scope);
        })
        .catch((error) => {
          console.warn('[PWA] Falha ao registrar Service Worker:', error);
        });
    });
  }

  // Notificação visual de pronto para desenvolvimento
  const tenantBadge = document.getElementById('active-tenant-badge');
  if (tenantBadge) {
    tenantBadge.textContent = 'Fecho Demo';
  }
});
