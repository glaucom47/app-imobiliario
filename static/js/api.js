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
   * Encerra a sessão do usuário.
   */
  logout() {
    this.setToken(null);
    this.setUser(null);
    this.setSelectedProperty(null);
    window.dispatchEvent(new CustomEvent('fecho:logout'));
  }
};
