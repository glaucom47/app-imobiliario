/**
 * Fecho - Estado do período de teste e subscrição (faixa informativa).
 * Mostra "Faltam N dias de teste" (aviso a partir de 2 dias) ou o modo só leitura.
 * Sem innerHTML com dados dinâmicos: apenas textContent (prevenção de XSS).
 */
(function () {
  'use strict';

  let banner = null;

  function ensureBanner() {
    if (banner) return banner;
    banner = document.createElement('div');
    banner.id = 'fecho-subscription-banner';
    banner.className = 'fecho-subscription-banner';
    banner.setAttribute('role', 'status');
    banner.hidden = true;

    const text = document.createElement('span');
    text.className = 'fecho-subscription-text';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'fecho-subscription-btn';
    btn.textContent = 'Ativar subscrição';
    btn.addEventListener('click', onActivate);

    banner.appendChild(text);
    banner.appendChild(btn);
    document.body.prepend(banner);
    return banner;
  }

  function show(message, variant, withButton) {
    const el = ensureBanner();
    el.querySelector('.fecho-subscription-text').textContent = message;
    el.querySelector('.fecho-subscription-btn').hidden = !withButton;
    el.dataset.variant = variant;
    el.hidden = false;
  }

  function hide() {
    if (banner) banner.hidden = true;
  }

  function onActivate() {
    // Fase B: substituído pelo redirecionamento para o Stripe Checkout.
    window.alert(
      'Planos Fecho: 29 € + IVA/mês ou 290 € + IVA/ano (até 3 utilizadores).\n\n' +
      'O pagamento online estará disponível muito em breve. ' +
      'Os seus dados ficam guardados e acessíveis para consulta.'
    );
  }

  function render(status) {
    if (!status) return hide();
    if (!status.escrita_permitida) {
      return show(
        'O período de teste terminou. Os seus dados estão disponíveis apenas para consulta.',
        'blocked',
        true
      );
    }
    if (status.plano_status === 'trial' && status.dias_restantes_trial !== null) {
      const d = status.dias_restantes_trial;
      const msg = d <= 1 ? 'Último dia do período de teste gratuito.' : `Faltam ${d} dias de teste gratuito.`;
      return show(msg, d <= 2 ? 'warning' : 'info', d <= 2);
    }
    if (status.plano_status === 'pendente') {
      return show('Pagamento pendente. Atualize o método de pagamento para evitar a suspensão.', 'warning', true);
    }
    return hide();
  }

  async function refresh() {
    if (typeof Api === 'undefined' || !Api.isAuthenticated()) return hide();
    try {
      render(await Api.getBillingStatus());
    } catch {
      // Silencioso: a faixa é apenas informativa
    }
  }

  window.addEventListener('fecho:subscricao', () => refresh());
  window.addEventListener('fecho:authenticated', () => refresh());
  window.addEventListener('fecho:unauthorized', hide);

  window.FechoSubscricao = { refresh, hide };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', refresh);
  } else {
    refresh();
  }
})();
