/**
 * TenGod API Client for JavaScript/Node.js
 * @version 1.5.0
 */

class TenGodClient {
  /**
   * Create a new TenGod client
   * @param {Object} config - Client configuration
   * @param {string} config.baseURL - Base URL of the API
   * @param {string} [config.apiKey] - API key for authentication
   * @param {number} [config.timeout=30000] - Request timeout in milliseconds
   */
  constructor(config) {
    this.baseURL = config.baseURL;
    this.apiKey = config.apiKey || '';
    this.timeout = config.timeout || 30000;
    
    if (typeof fetch === 'undefined') {
      throw new Error('Fetch API is not available. Use a Node.js environment or polyfill.');
    }
  }

  /**
   * Set the authentication API key
   * @param {string} apiKey - The API key
   */
  setApiKey(apiKey) {
    this.apiKey = apiKey;
  }

  /**
   * Set the request timeout
   * @param {number} timeout - Timeout in milliseconds
   */
  setTimeout(timeout) {
    this.timeout = timeout;
  }

  /**
   * Make an HTTP request
   * @private
   */
  async _request(method, endpoint, data = null) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const options = {
      method,
      headers,
      signal: AbortSignal.timeout(this.timeout)
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, options);
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error || `HTTP error ${response.status}`);
      }
      
      return result;
    } catch (error) {
      if (error.name === 'TimeoutError') {
        throw new Error(`Request timed out after ${this.timeout}ms`);
      }
      throw error;
    }
  }

  /**
   * Calculate Bazi (Eight Characters)
   * @param {Object} params - Bazi calculation parameters
   * @param {number} params.year - Year of birth
   * @param {number} params.month - Month of birth
   * @param {number} params.day - Day of birth
   * @param {number} params.hour - Hour of birth (0-23)
   * @param {number} params.minute - Minute of birth (0-59)
   * @param {number} params.gender - Gender (1=male, 0=female)
   * @param {boolean} [params.solar_calendar=true] - Use solar calendar
   * @returns {Promise<Object>} Bazi calculation result
   */
  async calculateBazi(params) {
    return this._request('POST', '/api/v1/bazi/calculate', {
      year: params.year,
      month: params.month,
      day: params.day,
      hour: params.hour,
      minute: params.minute || 0,
      gender: params.gender,
      solar_calendar: params.solar_calendar !== false
    });
  }

  /**
   * Get palace information
   * @param {number} palaceId - Palace ID (1-12)
   * @returns {Promise<Object>} Palace information
   */
  async getPalace(palaceId) {
    return this._request('GET', `/api/v1/palace/${palaceId}`);
  }

  /**
   * Get star information
   * @param {number} starId - Star ID
   * @returns {Promise<Object>} Star information
   */
  async getStar(starId) {
    return this._request('GET', `/api/v1/star/${starId}`);
  }

  /**
   * Analyze combination of stars
   * @param {number[]} starIds - Array of star IDs
   * @param {string} analysisType - Analysis type ('compatibility', 'interaction', 'strength')
   * @returns {Promise<Object>} Combination analysis result
   */
  async analyzeCombination(starIds, analysisType = 'compatibility') {
    return this._request('POST', '/api/v1/analysis/combination', {
      star_ids: starIds,
      analysis_type: analysisType
    });
  }

  /**
   * Health check
   * @returns {Promise<Object>} Health status
   */
  async healthCheck() {
    return this._request('GET', '/health');
  }

  /**
   * Get API version
   * @returns {Promise<Object>} API version info
   */
  async getVersion() {
    return this._request('GET', '/api/v1/version');
  }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TenGodClient;
} else if (typeof window !== 'undefined') {
  window.TenGodClient = TenGodClient;
}

export default TenGodClient;
