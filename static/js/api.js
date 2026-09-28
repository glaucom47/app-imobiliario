/**
 * Cliente HTTP da API REST - Fecho (fecho.pt)
 * Gerencia autenticação via JWT, injeção de cabeçalhos e tratamento centralizado de erros.
 */

const Api = {
  baseUrl: '/api/v1',
  tokenKey: 'fecho_jwt_token',

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
        // Redireciona ou limpa credencial expirada
        this.setToken(null);
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
  }
};
