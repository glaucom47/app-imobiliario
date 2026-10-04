/**
 * Cliente HTTP da API REST - Fecho (fecho.pt)
 * Gerencia autenticação via JWT, controle de sessão local, RBAC e injeção de cabeçalhos.
 */

const Api = {
  baseUrl: '/api/v1',
  tokenKey: 'fecho_jwt_token',
  userKey: 'fecho_user_data',

  getToken() {
    return localStorage.getItem(this.tokenKey);
  },

  setToken(token) {
    if (token) {
      localStorage.setItem(this.tokenKey, token);
    } else {
      localStorage.removeItem(this.tokenKey);
    }
  },

  getUser() {
    try {
      const data = localStorage.getItem(this.userKey);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  setUser(user) {
    if (user) {
      localStorage.setItem(this.userKey, JSON.stringify(user));
    } else {
      localStorage.removeItem(this.userKey);
    }
  },

  isAuthenticated() {
    return !!this.getToken();
  },

  isDiretor() {
    const user = this.getUser();
    return user && user.role === 'diretor';
  },

  isConsultor() {
    const user = this.getUser();
    return user && (user.role === 'consultor' || user.role === 'diretor');
  },

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        // Limpa credencial expirada e notifica
        this.setToken(null);
        this.setUser(null);
        window.dispatchEvent(new CustomEvent('fecho:unauthorized'));
      }

      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.detail || `Erro na requisição: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error(`[API Error] ${endpoint}:`, error);
      throw error;
    }
  },

  /**
   * Autentica o usuário por e-mail e senha.
   */
  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (data && data.access_token) {
      this.setToken(data.access_token);
      this.setUser(data.user);
      window.dispatchEvent(new CustomEvent('fecho:authenticated', { detail: data.user }));
    }
    return data;
  },

  /**
   * Obtém o perfil atualizado do usuário autenticado no servidor.
   */
  async getMe() {
    const user = await this.request('/auth/me');
    if (user) {
      this.setUser(user);
    }
    return user;
  },

  /**
   * Renova o token JWT de acesso.
   */
  async refresh() {
    const data = await this.request('/auth/refresh', {
      method: 'POST',
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
      this.setUser(data.user);
    }
    return data;
  },

  /**
   * Regista uma nova agência e o respetivo utilizador diretor.
   */
  async registerAgency(payload) {
    const data = await this.request('/auth/register-agency', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
      this.setUser(data.user);
      window.dispatchEvent(new CustomEvent('fecho:authenticated', { detail: data.user }));
    }
    return data;
  },

  /**
   * Regista um novo consultor associado a uma agência.
   */
  async registerConsultor(payload) {
    const data = await this.request('/auth/register-consultor', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
      this.setUser(data.user);
      window.dispatchEvent(new CustomEvent('fecho:authenticated', { detail: data.user }));
    }
    return data;
  },

  /**
   * Obtém lista de agências ativas para seleção de consultores no registo.
   */
  async getActiveAgencies() {
    return await this.request('/auth/agencies');
  },

  selectedPropertyKey: 'fecho_selected_property',

  getSelectedProperty() {
    try {
      const data = localStorage.getItem(this.selectedPropertyKey);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  setSelectedProperty(property) {
    if (property) {
      localStorage.setItem(this.selectedPropertyKey, JSON.stringify(property));
      window.dispatchEvent(new CustomEvent('fecho:property_selected', { detail: property }));
    } else {
      localStorage.removeItem(this.selectedPropertyKey);
      window.dispatchEvent(new CustomEvent('fecho:property_selected', { detail: null }));
    }
  },

  /**
   * Lista os imóveis da agência com parâmetros opcionais.
   */
  async getProperties(params = {}) {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.tipologia) query.append('tipologia', params.tipologia);
    if (params.consultor_id) query.append('consultor_id', params.consultor_id);
    if (params.busca) query.append('busca', params.busca);
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/properties${queryString}`);
  },

  /**
   * Obtém detalhes de um imóvel.
   */
  async getProperty(id) {
    return await this.request(`/properties/${id}`);
  },

  /**
   * Cria um novo imóvel na carteira da agência.
   */
  async createProperty(propertyData) {
    return await this.request('/properties', {
      method: 'POST',
      body: JSON.stringify(propertyData),
    });
  },

  /**
   * Atualiza dados cadastrais de um imóvel.
   */
  async updateProperty(id, propertyData) {
    return await this.request(`/properties/${id}`, {
      method: 'PUT',
      body: JSON.stringify(propertyData),
    });
  },

  /**
   * Realiza a transição de estado do imóvel na máquina de estados.
   * Se novo_status === 'Vendido', exige { nome_comprador, telefone_comprador, data_escritura }.
   */
  async transitionPropertyStatus(id, transitionData) {
    return await this.request(`/properties/${id}/transition`, {
      method: 'POST',
      body: JSON.stringify(transitionData),
    });
  },

  /**
   * Remove um imóvel sem visitas.
   */
  async deleteProperty(id) {
    return await this.request(`/properties/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Obtém o catálogo de tags de objeções da agência.
   */
  async getObjectionTags() {
    return await this.request('/visits/tags');
  },

  /**
   * Processa nota de voz ou texto oral para estruturação inteligente (Human-in-the-Loop).
   */
  async processVisitAudio(payload) {
    return await this.request('/visits/audio', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Registra a visita no sistema com suas objeções vinculadas.
   */
  async createVisit(visitData) {
    return await this.request('/visits', {
      method: 'POST',
      body: JSON.stringify(visitData),
    });
  },

  /**
   * Lista visitas da agência.
   */
  async getVisits(params = {}) {
    const query = new URLSearchParams();
    if (params.property_id) query.append('property_id', params.property_id);
    if (params.consultor_id) query.append('consultor_id', params.consultor_id);
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/visits${queryString}`);
  },

  /**
   * Obtém detalhes de uma visita.
   */
  async getVisit(id) {
    return await this.request(`/visits/${id}`);
  },

  /**
   * Marca o feedback ao proprietário como enviado.
   */
  async markVisitFeedbackSent(id) {
    return await this.request(`/visits/${id}/feedback-sent`, {
      method: 'PATCH',
    });
  },

  /**
   * Obtém os objetivos comerciais de scripts de marketing.
   */
  async getScriptObjectives() {
    return await this.request('/scripts/objectives');
  },

  /**
   * Gera um roteiro em 3 blocos (Gancho, 2 Destaques e CTA).
   */
  async generateScript(payload) {
    return await this.request('/scripts/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Obtém sugestão rápida de roteiro para um imóvel específico.
   */
  async getPropertyScript(propertyId, params = {}) {
    const query = new URLSearchParams();
    if (params.objetivo) query.append('objetivo', params.objetivo);
    if (params.tom) query.append('tom', params.tom);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/scripts/property/${propertyId}${queryString}`);
  },

  /**
   * Lista contatos da esfera de influência e pós-venda.
   */
  async getContacts(params = {}) {
    const query = new URLSearchParams();
    if (params.q) query.append('q', params.q);
    if (params.tipo) query.append('tipo', params.tipo);
    if (params.apenas_aniversario_hoje) query.append('apenas_aniversario_hoje', 'true');
    if (params.consultor_id) query.append('consultor_id', params.consultor_id);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/contacts${queryString}`);
  },

  /**
   * Obtém a lista de contatos que celebram aniversário da escritura hoje (alerta das 09:00).
   */
  async getAnniversaryContacts() {
    return await this.request('/contacts/anniversaries');
  },

  /**
   * Obtém detalhes de um contato.
   */
  async getContact(id) {
    return await this.request(`/contacts/${id}`);
  },

  /**
   * Cadastra manualmente um novo contato na esfera de influência.
   */
  async createContact(contactData) {
    return await this.request('/contacts', {
      method: 'POST',
      body: JSON.stringify(contactData),
    });
  },

  /**
   * Atualiza dados de um contato.
   */
  async updateContact(id, contactData) {
    return await this.request(`/contacts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(contactData),
    });
  },

  /**
   * Gera mensagem dinâmica estruturada de pós-venda e URL Deep Link para o WhatsApp.
   */
  async generateContactWhatsApp(id, payload) {
    return await this.request(`/contacts/${id}/whatsapp`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Executa a rotina de anonimização conforme RGPD ('Cliente Anonimizado').
   */
  async anonymizeContact(id) {
    return await this.request(`/contacts/${id}/anonymize`, {
      method: 'POST',
    });
  },

  /**
   * Remove um contato avulso desvinculado.
   */
  async deleteContact(id) {
    return await this.request(`/contacts/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Métodos do Backoffice (Exclusivos para Perfil Diretor)
   */
  async getBackofficeKPIs(dias = null) {
    const query = dias ? `?dias=${dias}` : '';
    return await this.request(`/backoffice/kpis${query}`);
  },

  async getBackofficeObjectionsAnalytics(propertyId = null) {
    const query = propertyId ? `?property_id=${propertyId}` : '';
    return await this.request(`/backoffice/objections-analytics${query}`);
  },

  async getBackofficeTags() {
    return await this.request('/backoffice/tags');
  },

  async createBackofficeTag(tagData) {
    return await this.request('/backoffice/tags', {
      method: 'POST',
      body: JSON.stringify(tagData),
    });
  },

  async updateBackofficeTag(tagId, tagData) {
    return await this.request(`/backoffice/tags/${tagId}`, {
      method: 'PUT',
      body: JSON.stringify(tagData),
    });
  },

  async getBackofficeSettings() {
    return await this.request('/backoffice/settings');
  },

  async updateBackofficeSettings(settingsData) {
    return await this.request('/backoffice/settings', {
      method: 'PUT',
      body: JSON.stringify(settingsData),
    });
  },

  async getBackofficeConsultores() {
    return await this.request('/backoffice/consultores');
  },

  async createBackofficeConsultor(consultorData) {
    return await this.request('/backoffice/consultores', {
      method: 'POST',
      body: JSON.stringify(consultorData),
    });
  },

  async updateBackofficeConsultorStatus(consultorId, statusData) {
    return await this.request(`/backoffice/consultores/${consultorId}/status`, {
      method: 'PATCH',
      body: JSON.stringify(statusData),
    });
  },

  async updateBackofficeConsultor(consultorId, consultorData) {
    return await this.request(`/backoffice/consultores/${consultorId}`, {
      method: 'PUT',
      body: JSON.stringify(consultorData),
    });
  },

  async downloadExportCsv(tipo, propertyId = null) {
    let url = `${this.baseUrl}/backoffice/export/csv?tipo=${encodeURIComponent(tipo)}`;
    if (propertyId) {
      url += `&property_id=${encodeURIComponent(propertyId)}`;
    }
    const token = this.getToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(url, { headers });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Falha ao exportar relatório CSV.' }));
      throw new Error(err.detail || 'Falha ao exportar relatório CSV.');
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition');
    let filename = `fecho_${tipo}.csv`;
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename=(.+?)(;|$)/);
      if (match && match[1]) {
        filename = match[1].replace(/["']/g, '');
      }
    }
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  // ==========================================
  // CAPTAÇÃO E ANGARIAÇÃO (LEADS & FONTES ABERTAS)
  // ==========================================

  async getLeads(params = {}) {
    const query = new URLSearchParams();
    if (params.fonte) query.append('fonte', params.fonte);
    if (params.status) query.append('status', params.status);
    if (params.concelho) query.append('concelho', params.concelho);
    if (params.tipologia) query.append('tipologia', params.tipologia);
    if (params.consultor_id) query.append('consultor_id', params.consultor_id);
    if (params.busca) query.append('busca', params.busca);
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/leads${queryString}`);
  },

  async getLeadStats() {
    return await this.request('/leads/stats');
  },

  async getLead(id) {
    return await this.request(`/leads/${id}`);
  },

  async createManualLead(leadData) {
    return await this.request('/leads/manual', {
      method: 'POST',
      body: JSON.stringify(leadData),
    });
  },

  async extractLeadUrl(url) {
    return await this.request('/leads/extrair-url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  },

  async triggerLeadScan(scanData = {}) {
    return await this.request('/leads/varredura', {
      method: 'POST',
      body: JSON.stringify(scanData),
    });
  },

  async convertLead(id, convertData = {}) {
    return await this.request(`/leads/${id}/converter`, {
      method: 'POST',
      body: JSON.stringify(convertData),
    });
  },

  async updateLeadStatus(id, statusData) {
    return await this.request(`/leads/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify(statusData),
    });
  },

  async registerLeadRgpd(id, data = {}) {
    return await this.request(`/leads/${id}/oposicao-rgpd`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // ==========================================
  // DIREÇÃO COMERCIAL & GESTÃO ATIVA DE EQUIPA (FSD 8)
  // ==========================================

  async getCommercialDashboard(filtro = 'este_mes') {
    return await this.request(`/backoffice/commercial-dashboard?filtro=${encodeURIComponent(filtro)}`);
  },

  async getSalesFunnel(filtro = 'este_mes', consultorId = null) {
    let url = `/backoffice/sales-funnel?filtro=${encodeURIComponent(filtro)}`;
    if (consultorId) {
      url += `&consultor_id=${encodeURIComponent(consultorId)}`;
    }
    return await this.request(url);
  },

  async getConsultoresPerformance(ano = null, mes = null) {
    const params = new URLSearchParams();
    if (ano) params.append('ano', ano);
    if (mes) params.append('mes', mes);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return await this.request(`/backoffice/consultores-performance${qs}`);
  },

  async getConsultorIndividualPerformance(consultorId, ano = null, mes = null) {
    const params = new URLSearchParams();
    if (ano) params.append('ano', ano);
    if (mes) params.append('mes', mes);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return await this.request(`/backoffice/consultor/${consultorId}/performance${qs}`);
  },

  async startWeeklyMeeting(consultorId) {
    return await this.request(`/backoffice/meetings/start?consultor_id=${encodeURIComponent(consultorId)}`, {
      method: 'POST',
    });
  },

  async saveWeeklyMeeting(meetingData) {
    return await this.request('/backoffice/meetings/save', {
      method: 'POST',
      body: JSON.stringify(meetingData),
    });
  },

  async getConsultorMeetings(consultorId) {
    return await this.request(`/backoffice/consultor/${consultorId}/meetings`);
  },

  async getCommercialGoals(ano = null, mes = null, consultorId = null) {
    const params = new URLSearchParams();
    if (ano) params.append('ano', ano);
    if (mes) params.append('mes', mes);
    if (consultorId) params.append('consultor_id', consultorId);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return await this.request(`/backoffice/goals${qs}`);
  },

  async setCommercialGoal(goalData) {
    return await this.request('/backoffice/goals', {
      method: 'POST',
      body: JSON.stringify(goalData),
    });
  },

  async getPipelineDeals(consultorId = null, fase = null, ativoApenas = true) {
    const params = new URLSearchParams();
    if (consultorId) params.append('consultor_id', consultorId);
    if (fase) params.append('fase', fase);
    if (ativoApenas !== null) params.append('ativo_apenas', ativoApenas);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return await this.request(`/backoffice/pipeline${qs}`);
  },

  async createPipelineDeal(dealData) {
    return await this.request('/backoffice/pipeline', {
      method: 'POST',
      body: JSON.stringify(dealData),
    });
  },

  async updatePipelineDeal(dealId, dealData) {
    return await this.request(`/backoffice/pipeline/${dealId}`, {
      method: 'PUT',
      body: JSON.stringify(dealData),
    });
  },

  async deletePipelineDeal(dealId) {
    return await this.request(`/backoffice/pipeline/${dealId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Encerra a sessão do usuário.
   */
  logout() {
    this.setToken(null);
    this.setUser(null);
    this.setSelectedProperty(null);
    window.dispatchEvent(new CustomEvent('fecho:logout'));
  }
};
