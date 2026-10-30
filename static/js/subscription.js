/**
 * Fecho - Estado do período de teste e subscrição (faixa informativa + pagamento Stripe).
 * Sem innerHTML com dados dinâmicos: apenas textContent (prevenção de XSS).
 */
(function () {
  'use strict';

  let banner = null;
  let ultimoEstado = null;

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  function ensureBanner() {
    if (banner) return banner;
    banner = el('div', 'fecho-subscription-banner');
    banner.id = 'fecho-subscription-banner';
    banner.setAttribute('role', 'status');
    banner.hidden = true;
    banner.appendChild(el('span', 'fecho-subscription-text'));

    const acoes = el('span', 'fecho-subscription-actions');
    const btnMensal = el('button', 'fecho-subscription-btn', 'Mensal · 29 € + IVA');
    btnMensal.type = 'button';
    btnMensal.addEventListener('click', () => checkout('mensal', btnMensal));
    const btnAnual = el('button', 'fecho-subscription-btn fecho-subscription-btn-alt', 'Anual · 290 € + IVA');
    btnAnual.type = 'button';
    btnAnual.addEventListener('click', () => checkout('anual', btnAnual));
    acoes.appendChild(btnMensal);
    acoes.appendChild(btnAnual);
    banner.appendChild(acoes);

    document.body.prepend(banner);
    return banner;
  }

  function show(message, variant, withButtons) {
    const b = ensureBanner();
    b.querySelector('.fecho-subscription-text').textContent = message;
    b.querySelector('.fecho-subscription-actions').hidden = !withButtons;
    b.dataset.variant = variant;
    b.hidden = false;
  }

  function hide() {
    if (banner) banner.hidden = true;
  }

  async function checkout(periodo, btn) {
    if (!ultimoEstado || !ultimoEstado.pagamento_online_disponivel) {
      window.alert(
        'Planos Fecho: 29 € + IVA/mês ou 290 € + IVA/ano (até 3 utilizadores).\n\n' +
        'O pagamento online estará disponível muito em breve. ' +
        'Os seus dados ficam guardados e acessíveis para consulta.'
      );
      return;
    }
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'A abrir pagamento seguro...';
    try {
      const data = await Api.createCheckout(periodo);
      if (data && data.url && data.url.startsWith('https://')) {
        window.location.href = data.url;
        return;
      }
      throw new Error('Resposta inválida do serviço de pagamento.');
    } catch (err) {
      const msg = String(err.message || '');
      window.alert(msg.includes('diretor') || msg.includes('Diretor') || msg.includes('403')
        ? 'Apenas o diretor da agência pode ativar a subscrição.'
        : (msg || 'Não foi possível iniciar o pagamento.'));
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  async function abrirPortal(btn) {
    btn.disabled = true;
    try {
      const data = await Api.openBillingPortal();
      if (data && data.url && data.url.startsWith('https://')) window.location.href = data.url;
    } catch (err) {
      window.alert(err.message || 'Não foi possível abrir a gestão da subscrição.');
    } finally {
      btn.disabled = false;
    }
  }

  function renderBotaoPortal(status) {
    // Apenas no backoffice (diretor), ao lado do botão de terminar sessão
    const logout = document.getElementById('btn-backoffice-logout');
    let btn = document.getElementById('btn-gerir-subscricao');
    if (!logout || !status || !status.tem_subscricao) {
      if (btn) btn.remove();
      return;
    }
    if (!btn) {
      btn = el('button', logout.className, 'Gerir subscrição');
      btn.id = 'btn-gerir-subscricao';
      btn.type = 'button';
      btn.addEventListener('click', () => abrirPortal(btn));
      logout.parentNode.insertBefore(btn, logout);
    }
  }

  function render(status) {
    ultimoEstado = status;
    renderBotaoPortal(status);
    if (!status) return hide();
    if (!status.escrita_permitida) {
      return show(
        'O período de teste terminou. Os seus dados estão disponíveis apenas para consulta. Escolha um plano:',
        'blocked',
        true
      );
    }
    if (status.plano_status === 'trial' && status.dias_restantes_trial !== null) {
      const d = status.dias_restantes_trial;
      const msg = d <= 1 ? 'Último dia do período de teste gratuito.' : `Faltam ${d} dias de teste gratuito.`;
      return show(msg, d <= 2 ? 'warning' : 'info', true);
    }
    if (status.plano_status === 'pendente') {
      return show('Pagamento pendente. Atualize o método de pagamento em "Gerir subscrição" para evitar a suspensão.', 'warning', false);
    }
    return hide();
  }

  async function refresh() {
    if (typeof Api === 'undefined' || !Api.isAuthenticated()) {
      ultimoEstado = null;
      return hide();
    }
    try {
      render(await Api.getBillingStatus());
    } catch {
      // Silencioso: a faixa é apenas informativa
    }
  }

  function tratarRetornoPagamento() {
    const params = new URLSearchParams(window.location.search);
    const r = params.get('pagamento');
    if (!r) return;
    params.delete('pagamento');
    const limpo = window.location.pathname + (params.toString() ? `?${params}` : '') + window.location.hash;
    window.history.replaceState({}, '', limpo);
    if (r === 'sucesso') {
      show('Pagamento recebido. A ativar a sua subscrição...', 'info', false);
      // O webhook do Stripe pode demorar alguns segundos
      setTimeout(refresh, 4000);
      setTimeout(refresh, 10000);
    } else if (r === 'cancelado') {
      show('Pagamento cancelado. Pode ativar a subscrição quando quiser.', 'info', false);
      setTimeout(refresh, 5000);
    }
  }

  window.addEventListener('fecho:subscricao', () => refresh());
  window.addEventListener('fecho:authenticated', () => refresh());
  window.addEventListener('fecho:unauthorized', hide);

  window.FechoSubscricao = { refresh, hide };

  function init() {
    tratarRetornoPagamento();
    refresh();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
