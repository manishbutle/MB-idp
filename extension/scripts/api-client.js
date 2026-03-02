/**
 * API Client Module
 * Handles all API communication with the backend
 * Requirements: 14.6, 14.7, 15.1
 */

class APIClient {
  constructor() {
    // API Gateway base URL - should be configured based on deployment
    this.baseURL = 'https://fqknm97ju4.execute-api.us-east-1.amazonaws.com/prod'; // TODO: Update with actual API Gateway URL
    this.timeout = 30000; // 30 seconds
  }

  /**
   * Make an API call
   * @param {string} endpoint - API endpoint path
   * @param {string} method - HTTP method (GET, POST, etc.)
   * @param {Object} data - Request body data
   * @param {boolean} requiresAuth - Whether authentication is required
   * @returns {Promise<Object>} API response
   */
  async call(endpoint, method = 'GET', data = null, requiresAuth = false) {
    try {
      const headers = {
        'Content-Type': 'application/json'
      };

      let url = `${this.baseURL}${endpoint}`;

      // Add authentication as query parameter if required (to avoid API Gateway header parsing)
      if (requiresAuth) {
        const session = await storageManager.getSession();
        if (!session || !session.token) {
          throw new Error('Authentication required. Please log in.');
        }
        // Add token as query parameter instead of header
        const separator = endpoint.includes('?') ? '&' : '?';
        url += `${separator}auth_token=${encodeURIComponent(session.token)}`;
        console.log('[API] Token being used:', session.token.substring(0, 50) + '...');
        console.log('[API] Token contains = ?', session.token.includes('='));
      }

      const options = {
        method,
        headers,
        signal: AbortSignal.timeout(this.timeout)
      };

      if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
      }

      const response = await fetch(url, options);

      // Handle HTTP error status codes
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Parse JSON response
      return await response.json();
    } catch (error) {
      // Handle network timeouts
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        throw new Error('Request timed out. Please check your connection and try again.');
      }

      // Handle network connectivity issues
      if (error.message === 'Failed to fetch') {
        throw new Error('Network error. Please check your internet connection.');
      }

      // Re-throw other errors
      throw error;
    }
  }

  /**
   * Process document
   * @param {Object} documentData - Document data to process
   * @returns {Promise<Object>} Processing results
   */
  async processDocument(documentData) {
    return this.call('/process_document', 'POST', documentData, true);
  }

  /**
   * Get processing history
   * @param {number} page - Page number (not used with DynamoDB pagination)
   * @param {number} limit - Items per page
   * @returns {Promise<Object>} History data
   */
  async getHistory(page = 1, limit = 20) {
    return this.call(`/history?page_size=${limit}`, 'GET', null, true);
  }

  /**
   * Get datapoints/prompts
   * @returns {Promise<Object>} Prompts data
   */
  async getDatapoints() {
    return this.call('/datapoints', 'GET', null, true);
  }

  /**
   * Reset prompts - reload from server
   * @returns {Promise<Object>} Prompts data
   */
  async resetPrompts() {
    return this.call('/reset_prompts', 'POST', {}, true);
  }

  /**
   * User authentication
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} Auth response with token
   */
  async auth(email, password) {
    // Add timestamp to bust any API Gateway cache
    const timestamp = Date.now();
    return this.call(`/auth?t=${timestamp}`, 'POST', { email, password }, false);
  }

  /**
   * Get total documents processed
   * @returns {Promise<Object>} Document count
   */
  async getTotalDocumentProcessed() {
    return this.call('/total_document_processed', 'GET', null, true);
  }

  /**
   * Get available balance
   * @returns {Promise<Object>} Balance data
   */
  async getAvailableBalance() {
    return this.call('/available_balance', 'GET', null, true);
  }

  /**
   * Upload file to FTP server
   * @param {string} fileName - Name of the file
   * @param {string} fileContent - Base64 encoded file content
   * @param {string} remoteDirectory - Optional remote directory path
   * @returns {Promise<Object>} Upload response
   */
  async uploadToFTP(fileName, fileContent, remoteDirectory = '') {
    const data = {
      file_name: fileName,
      file_content: fileContent
    };
    
    if (remoteDirectory) {
      data.remote_directory = remoteDirectory;
    }
    
    return this.call('/ftp', 'POST', data, true);
  }

  /**
   * Send email with attachments
   * @param {string} to - Recipient email address
   * @param {string} cc - CC email addresses
   * @param {string} subject - Email subject
   * @param {Array} attachments - Array of attachment objects with fileName and fileContent (base64)
   * @returns {Promise<Object>} Send email response
   */
  async sendEmail(to, cc, subject, attachments) {
    const data = {
      to,
      cc,
      subject,
      attachments
    };
    
    return this.call('/send_email', 'POST', data, true);
  }

  /**
   * Get user transactions
   * @param {number} page - Page number (not used with DynamoDB pagination)
   * @param {number} limit - Items per page
   * @returns {Promise<Object>} Transactions data
   */
  async getMyTransactions(page = 1, limit = 20) {
    return this.call(`/mytransactions?page_size=${limit}`, 'GET', null, true);
  }

  /**
   * Update user profile
   * @param {string} firstName - User's first name
   * @param {string} lastName - User's last name
   * @returns {Promise<Object>} Profile update response
   */
  async updateProfile(firstName, lastName) {
    return this.call('/profile_change', 'POST', { first_name: firstName, last_name: lastName }, true);
  }

  /**
   * Change user password
   * @param {string} currentPassword - Current password
   * @param {string} newPassword - New password
   * @param {string} confirmPassword - Confirm new password
   * @returns {Promise<Object>} Password change response
   */
  async changePassword(currentPassword, newPassword, confirmPassword) {
    return this.call('/password_change', 'POST', { 
      current_password: currentPassword, 
      new_password: newPassword,
      confirm_password: confirmPassword
    }, true);
  }

  /**
   * Top up user credits
   * @param {number} amount - Amount to top up
   * @param {string} remark - Optional remark
   * @returns {Promise<Object>} Top up response
   */
  async topUp(amount, remark = '') {
    return this.call('/top_up', 'POST', { amount, remark }, true);
  }

  /**
   * Add credit to user account (Admin only)
   * @param {string} email - User email
   * @param {number} amount - Credit amount to add
   * @returns {Promise<Object>} Add credit response
   */
  async addCredit(email, amount) {
    return this.call('/add_credit', 'POST', { email, amount }, true);
  }

  /**
   * User registration
   * @param {Object} userData - User registration data
   * @returns {Promise<Object>} Registration response
   */
  async signUp(userData) {
    return this.call('/sign_up', 'POST', userData, false);
  }

  /**
   * Request password reset
   * @param {string} email - User email
   * @returns {Promise<Object>} Forget password response
   */
  async forgetPassword(email) {
    return this.call('/forget_password', 'POST', { email }, false);
  }

  /**
   * Reset password with token
   * @param {string} token - Reset token
   * @param {string} newPassword - New password
   * @returns {Promise<Object>} Reset password response
   */
  async resetPassword(token, newPassword) {
    return this.call('/reset_password', 'POST', { token, new_password: newPassword }, false);
  }

  /**
   * Submit data to external API
   * @param {string} endpoint - API endpoint URL
   * @param {string} method - HTTP method
   * @param {Object} headers - Request headers
   * @param {Object} body - Request body
   * @returns {Promise<Object>} API response
   */
  async submitToExternalAPI(endpoint, method, headers, body) {
    // This is a direct call to external API, not through our backend
    try {
      const options = {
        method,
        headers: headers || { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(this.timeout)
      };

      if (body && (method === 'POST' || method === 'PUT')) {
        options.body = typeof body === 'string' ? body : JSON.stringify(body);
      }

      const response = await fetch(endpoint, options);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        throw new Error('Request timed out. Please check your connection and try again.');
      }
      if (error.message === 'Failed to fetch') {
        throw new Error('Network error. Please check your internet connection.');
      }
      throw error;
    }
  }
}

// Export singleton instance
const apiClient = new APIClient();

// For use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = apiClient;
}
