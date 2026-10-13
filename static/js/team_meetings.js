/**
 * Reunião de Equipa (coletiva) — Presença em 1 toque + atividade lançada pelo Diretor.
 * Módulo isolado do backoffice.html. Depende de `Api` (static/js/api.js).
 * Segurança: toda interpolação dinâmica em innerHTML passa por escapeHtml().
 */
(function () {
  'use strict';

  const PRESENCAS = ['Presente', 'Atraso', 'Ausente', 'AusenciaJustificada'];
  const PRESENCA_LABEL = {
    Presente: '✓ Presente',
    Atraso: '⏱ Atraso',
    Ausente: '✕ Ausente',
    AusenciaJustificada: '⊘ Justificada',
  };
  const CAMPOS = [
    ['contactos', 'Contactos'],
    ['reunioes_angariacao', 'Reun. Ang.'],
    ['angariacoes', 'Angariações'],
    ['exclusivos', 'Exclusivos'],
    ['visitas', 'Visitas'],
    ['propostas', 'Propostas'],
    ['cpcv', 'CPCV'],
    ['escrituras', 'Escrituras'],
  ];
  const TIPO_LABEL = { diaria: 'Diária', semanal: 'Semanal', outra: 'Outra' };

  let current = null;       // reunião aberta no editor
  let editExcecional = false;
  let historico = [];
  let periodoDias = 30;

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function fmtData(iso) {
    try {
      return new Date(iso).toLocaleString('pt-PT', { dateStyle: 'medium', timeStyle: 'short' });
    } catch (_) { return iso; }
  }

  function isHoje(iso) {
    const d = new Date(iso);
    const h = new Date();
    return d.getFullYear() === h.getFullYear() && d.getMonth() === h.getMonth() && d.getDate() === h.getDate();
  }

  function notify(msg, isError) {
    if (typeof window.showToast === 'function') { window.showToast(msg, isError ? 'error' : 'success'); return; }
    const el = document.getElementById('tm-feedback');
    if (el) {
      el.textContent = msg;
      el.style.color = isError ? 'var(--color-error)' : 'var(--color-secondary)';
    }
  }

  // ---------------------------------------------------------------- Assiduidade
  function assidClass(pct) {
    if (pct === null || pct === undefined) return 'na';
    if (pct >= 90) return 'verde';
    if (pct >= 70) return 'amarelo';
    return 'vermelho';
  }

  function assidPill(pct) {
    const txt = (pct === null || pct === undefined) ? '—' : `${pct}%`;
    return `<span class="tm-assid tm-assid--${assidClass(pct)}">${escapeHtml(txt)}</span>`;
  }

  async function loadStats() {
    const tbody = document.getElementById('tm-stats-body');
    if (!tbody) return;
    try {
      const data = await Api.getAttendanceStats(periodoDias);
      const rows = data.consultores || [];
      document.getElementById('tm-stats-total').textContent =
        `${data.total_reunioes} reunião(ões) nos últimos ${data.dias} dias`;
      if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="tm-meta" style="text-align:center;padding:16px;">Sem consultores ativos.</td></tr>';
        return;
      }
      tbody.innerHTML = rows.map((r) => `
        <tr>
          <td><strong>${escapeHtml(r.nome)}</strong></td>
          <td>${Number(r.presentes)}</td>
          <td>${Number(r.atrasos)}</td>
          <td>${Number(r.ausentes)}</td>
          <td>${Number(r.justificadas)}</td>
          <td>${assidPill(r.assiduidade_pct)}</td>
        </tr>`).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="color:var(--color-error);padding:16px;">${escapeHtml(err.message)}</td></tr>`;
    }
  }

  // ---------------------------------------------------------------- Histórico
  async function loadHistory() {
    const list = document.getElementById('tm-history-list');
    if (!list) return;
    try {
      historico = await Api.listTeamMeetings(30);
      if (!historico.length) {
        list.innerHTML = '<li class="tm-meta" style="cursor:default;">Ainda não existem reuniões de equipa registadas.</li>';
        return;
      }
      list.innerHTML = historico.map((m) => `
        <li data-id="${Number(m.id)}" tabindex="0" role="button" aria-label="Abrir reunião de ${escapeHtml(fmtData(m.data_hora))}">
          <div>
            <strong style="font-size:13px;">${escapeHtml(fmtData(m.data_hora))}</strong>
            <div class="tm-meta">${escapeHtml(TIPO_LABEL[m.tipo] || m.tipo)} · ${Number(m.total_presentes)}/${Number(m.total_consultores)} presentes · ${escapeHtml(m.diretor_nome || '')}</div>
          </div>
          <span class="tm-badge ${m.bloqueada ? 'tm-badge--lock' : 'tm-badge--open'}">${m.bloqueada ? '🔒 Consolidada' : '✎ Editável'}</span>
        </li>`).join('');
    } catch (err) {
      list.innerHTML = `<li style="color:var(--color-error);cursor:default;">${escapeHtml(err.message)}</li>`;
    }
  }

  // ---------------------------------------------------------------- Editor
  function renderEditor(meeting) {
    current = meeting;
    editExcecional = false;
    const box = document.getElementById('tm-editor');
    if (!box) return;
    const locked = meeting.bloqueada;
    const dis = locked ? 'disabled' : '';

    const head = CAMPOS.map(([, label]) => `<th scope="col">${escapeHtml(label)}</th>`).join('');
    const rows = meeting.linhas.map((l) => `
      <tr data-consultor="${Number(l.consultor_id)}">
        <td><strong>${escapeHtml(l.consultor_nome || ('#' + l.consultor_id))}</strong></td>
        <td><button type="button" class="tm-presenca" data-v="${escapeHtml(l.presenca)}" ${dis}
              aria-label="Presença de ${escapeHtml(l.consultor_nome || '')}: toque para alterar">${escapeHtml(PRESENCA_LABEL[l.presenca] || l.presenca)}</button></td>
        ${CAMPOS.map(([campo]) => `
          <td><input class="tm-num" type="number" inputmode="numeric" min="0" max="10000" step="1"
                data-campo="${campo}" value="${Number(l[campo]) || 0}" ${dis}
                aria-label="${escapeHtml(campo)}"></td>`).join('')}
        <td><input class="tm-note" type="text" maxlength="2000" data-campo="nota" value="${escapeHtml(l.nota || '')}" ${dis} placeholder="Nota"></td>
      </tr>`).join('');

    box.innerHTML = `
      <section class="tm-card" aria-labelledby="tm-editor-title">
        <div class="tm-card-head">
          <div>
            <h3 id="tm-editor-title">Reunião ${escapeHtml(TIPO_LABEL[meeting.tipo] || meeting.tipo)} · ${escapeHtml(fmtData(meeting.data_hora))}</h3>
            <div class="tm-meta">Toque na presença para alternar: Presente → Atraso → Ausente → Justificada</div>
          </div>
          <span class="tm-badge ${locked ? 'tm-badge--lock' : 'tm-badge--open'}">${locked ? '🔒 Consolidada (+24h)' : '✎ Editável até 24h'}</span>
        </div>
        <div class="tm-grid-wrap">
          <table class="tm-grid">
            <thead><tr><th scope="col">Consultor</th><th scope="col">Presença</th>${head}<th scope="col">Nota</th></tr></thead>
            <tbody>${rows || '<tr><td colspan="11" class="tm-meta">Sem consultores ativos na agência.</td></tr>'}</tbody>
          </table>
        </div>
        <label for="tm-notas-gerais" class="tm-meta" style="display:block;margin-top:14px;">Notas gerais da reunião</label>
        <textarea id="tm-notas-gerais" maxlength="5000" rows="2" ${dis}
          style="width:100%;border:1px solid var(--color-outline-variant);border-radius:10px;padding:10px;font:inherit;">${escapeHtml(meeting.notas_gerais || '')}</textarea>
        <div class="tm-actions">
          ${locked ? '<button type="button" id="tm-btn-unlock" class="btn-secondary-ghost" style="width:auto;padding:0 16px;">Edição excecional</button>' : ''}
          <button type="button" id="tm-btn-save" class="btn-primary-action" style="width:auto;padding:0 20px;" ${dis}>Guardar Reunião</button>
        </div>
        <p id="tm-feedback" class="tm-meta" role="status" aria-live="polite" style="margin-top:8px;"></p>
      </section>`;
    box.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function collectPayload() {
    const linhas = [];
    document.querySelectorAll('#tm-editor tr[data-consultor]').forEach((tr) => {
      const linha = {
        consultor_id: Number(tr.dataset.consultor),
        presenca: tr.querySelector('.tm-presenca').dataset.v,
      };
      tr.querySelectorAll('.tm-num').forEach((inp) => {
        const v = parseInt(inp.value, 10);
        linha[inp.dataset.campo] = Number.isFinite(v) && v >= 0 ? Math.min(v, 10000) : 0;
      });
      const nota = tr.querySelector('.tm-note').value.trim();
      linha.nota = nota || null;
      linhas.push(linha);
    });
    return {
      linhas,
      notas_gerais: document.getElementById('tm-notas-gerais')?.value ?? null,
      confirmar_edicao_excecional: editExcecional,
    };
  }

  async function save() {
    if (!current) return;
    const btn = document.getElementById('tm-btn-save');
    btn.disabled = true;
    btn.textContent = 'A guardar...';
    try {
      const updated = await Api.updateTeamMeeting(current.id, collectPayload());
      renderEditor(updated);
      notify('Reunião guardada com sucesso.');
      await Promise.all([loadHistory(), loadStats()]);
    } catch (err) {
      notify(err.message || 'Falha ao guardar a reunião.', true);
      btn.disabled = false;
      btn.textContent = 'Guardar Reunião';
    }
  }

  function unlock() {
    const ok = window.confirm(
      'Esta reunião já foi consolidada (mais de 24h).\n' +
      'A edição excecional ficará registada na auditoria com o seu utilizador e data.\nDeseja continuar?'
    );
    if (!ok) return;
    editExcecional = true;
    document.querySelectorAll('#tm-editor input, #tm-editor textarea, #tm-editor .tm-presenca, #tm-btn-save')
      .forEach((el) => { el.disabled = false; });
    document.getElementById('tm-btn-unlock')?.remove();
  }

  async function startToday() {
    const tipo = document.getElementById('tm-tipo')?.value || 'diaria';
    const existeHoje = historico.some((m) => isHoje(m.data_hora));
    if (existeHoje && !window.confirm('Já existe uma reunião registada hoje. Criar uma NOVA reunião (a anterior é preservada)?')) {
      return;
    }
    const btn = document.getElementById('tm-btn-start');
    btn.disabled = true;
    try {
      const meeting = await Api.createTeamMeeting(tipo);
      renderEditor(meeting);
      await loadHistory();
    } catch (err) {
      notify(err.message || 'Não foi possível iniciar a reunião.', true);
    } finally {
      btn.disabled = false;
    }
  }

  // ---------------------------------------------------------------- Eventos
  function bind() {
    const root = document.getElementById('tab-team-meetings');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = '1';

    root.addEventListener('click', (ev) => {
      const t = ev.target;
      if (t.closest('#tm-btn-start')) return startToday();
      if (t.closest('#tm-btn-save')) return save();
      if (t.closest('#tm-btn-unlock')) return unlock();

      const chip = t.closest('.tm-presenca');
      if (chip && !chip.disabled) {
        const next = PRESENCAS[(PRESENCAS.indexOf(chip.dataset.v) + 1) % PRESENCAS.length];
        chip.dataset.v = next;
        chip.textContent = PRESENCA_LABEL[next];
        return;
      }

      const per = t.closest('.tm-period button');
      if (per) {
        periodoDias = Number(per.dataset.dias);
        root.querySelectorAll('.tm-period button').forEach((b) => b.classList.toggle('active', b === per));
        return loadStats();
      }

      const item = t.closest('#tm-history-list li[data-id]');
      if (item) {
        const m = historico.find((h) => h.id === Number(item.dataset.id));
        if (m) renderEditor(m);
      }
    });

    root.addEventListener('keydown', (ev) => {
      const item = ev.target.closest && ev.target.closest('#tm-history-list li[data-id]');
      if (item && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); item.click(); }
    });

    // Seleciona o conteúdo ao focar um campo numérico (lançamento rápido).
    root.addEventListener('focusin', (ev) => {
      if (ev.target.classList && ev.target.classList.contains('tm-num')) ev.target.select();
    });
  }

  async function load() {
    bind();
    await Promise.all([loadHistory(), loadStats()]);
  }

  window.TeamMeetings = { load, assidPill };
})();
