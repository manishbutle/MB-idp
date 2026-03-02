/**
 * Local Storage Utility Module
 * Provides functions for storing/retrieving data from Chrome storage API
 * with encryption/decryption for sensitive credentials
 * 
 * Requirements: 13.2, 17.4
 */

// Simple encryption/decryption using Web Crypto API
// Note: For production, consider using a more robust encryption library
class StorageManager {
  constructor() {
    this.storage = chrome.storage.local;
    // Encryption key - in production, this should be derived from user credentials
    this.encryptionKey = 'ai-doc-processing-key-2024';
  }

  /**
   * Encrypt sensitive data using simple XOR cipher
   * For production, use Web Crypto API with AES-GCM
   * @param {string} text - Text to encrypt
   * @returns {string} Encrypted text in base64
   */
  encrypt(text) {
    if (!text) return '';
    
    try {
      const key = this.encryptionKey;
      let encrypted = '';
      
      for (let i = 0; i < text.length; i++) {
        const charCode = text.charCodeAt(i) ^ key.charCodeAt(i % key.length);
        encrypted += String.fromCharCode(charCode);
      }
      
      // Convert to base64
      return btoa(encrypted);
    } catch (error) {
      console.error('Encryption error:', error);
      throw new Error('Failed to encrypt data');
    }
  }

  /**
   * Decrypt sensitive data
   * @param {string} encryptedText - Encrypted text in base64
   * @returns {string} Decrypted text
   */
  decrypt(encryptedText) {
    if (!encryptedText) return '';
    
    try {
      // Decode from base64
      const encrypted = atob(encryptedText);
      const key = this.encryptionKey;
      let decrypted = '';
      
      for (let i = 0; i < encrypted.length; i++) {
        const charCode = encrypted.charCodeAt(i) ^ key.charCodeAt(i % key.length);
        decrypted += String.fromCharCode(charCode);
      }
      
      return decrypted;
    } catch (error) {
      console.error('Decryption error:', error);
      throw new Error('Failed to decrypt data');
    }
  }

  /**
   * Store data in Chrome local storage
   * @param {string} key - Storage key
   * @param {any} value - Value to store
   * @returns {Promise<void>}
   */
  async set(key, value) {
    return new Promise((resolve, reject) => {
      this.storage.set({ [key]: value }, () => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve();
        }
      });
    });
  }

  /**
   * Retrieve data from Chrome local storage
   * @param {string} key - Storage key
   * @returns {Promise<any>} Retrieved value
   */
  async get(key) {
    return new Promise((resolve, reject) => {
      this.storage.get([key], (result) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(result[key]);
        }
      });
    });
  }

  /**
   * Remove data from Chrome local storage
   * @param {string} key - Storage key
   * @returns {Promise<void>}
   */
  async remove(key) {
    return new Promise((resolve, reject) => {
      this.storage.remove(key, () => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve();
        }
      });
    });
  }

  /**
   * Clear all data from Chrome local storage
   * @returns {Promise<void>}
   */
  async clear() {
    return new Promise((resolve, reject) => {
      this.storage.clear(() => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve();
        }
      });
    });
  }

  /**
   * Store session data
   * @param {Object} session - Session object
   * @returns {Promise<void>}
   */
  async setSession(session) {
    return this.set('session', session);
  }

  /**
   * Retrieve session data
   * @returns {Promise<Object|null>} Session object or null
   */
  async getSession() {
    return this.get('session');
  }

  /**
   * Clear session data
   * @returns {Promise<void>}
   */
  async clearSession() {
    return this.remove('session');
  }

  /**
   * Store prompts data with timestamp
   * @param {Array} prompts - Array of prompt objects
   * @returns {Promise<void>}
   */
  async setPrompts(prompts) {
    const data = {
      prompts: prompts,
      last_sync: new Date().toISOString()
    };
    return this.set('prompts', data);
  }

  /**
   * Retrieve prompts data
   * @returns {Promise<Object|null>} Prompts object with last_sync or null
   */
  async getPrompts() {
    return this.get('prompts');
  }

  /**
   * Store FTP settings with encrypted password
   * @param {Object} ftpSettings - FTP configuration
   * @returns {Promise<void>}
   */
  async setFTPSettings(ftpSettings) {
    const encrypted = { ...ftpSettings };
    if (encrypted.password) {
      encrypted.password = this.encrypt(encrypted.password);
    }
    
    const settings = await this.get('settings') || {};
    settings.ftp = encrypted;
    return this.set('settings', settings);
  }

  /**
   * Retrieve FTP settings with decrypted password
   * @returns {Promise<Object|null>} FTP settings or null
   */
  async getFTPSettings() {
    const settings = await this.get('settings');
    if (!settings || !settings.ftp) return null;
    
    const ftp = { ...settings.ftp };
    if (ftp.password) {
      ftp.password = this.decrypt(ftp.password);
    }
    return ftp;
  }

  /**
   * Store Email settings with encrypted password
   * @param {Object} emailSettings - Email configuration
   * @returns {Promise<void>}
   */
  async setEmailSettings(emailSettings) {
    const encrypted = { ...emailSettings };
    if (encrypted.smtp_password) {
      encrypted.smtp_password = this.encrypt(encrypted.smtp_password);
    }
    
    const settings = await this.get('settings') || {};
    settings.email = encrypted;
    return this.set('settings', settings);
  }

  /**
   * Retrieve Email settings with decrypted password
   * @returns {Promise<Object|null>} Email settings or null
   */
  async getEmailSettings() {
    const settings = await this.get('settings');
    if (!settings || !settings.email) return null;
    
    const email = { ...settings.email };
    if (email.smtp_password) {
      email.smtp_password = this.decrypt(email.smtp_password);
    }
    return email;
  }

  /**
   * Store API settings
   * @param {Object} apiSettings - API configuration
   * @returns {Promise<void>}
   */
  async setAPISettings(apiSettings) {
    const settings = await this.get('settings') || {};
    settings.api = apiSettings;
    return this.set('settings', settings);
  }

  /**
   * Retrieve API settings
   * @returns {Promise<Object|null>} API settings or null
   */
  async getAPISettings() {
    const settings = await this.get('settings');
    return settings?.api || null;
  }

  /**
   * Retrieve all settings
   * @returns {Promise<Object>} All settings
   */
  async getAllSettings() {
    const settings = await this.get('settings') || {};
    
    // Decrypt passwords
    if (settings.ftp?.password) {
      settings.ftp.password = this.decrypt(settings.ftp.password);
    }
    if (settings.email?.smtp_password) {
      settings.email.smtp_password = this.decrypt(settings.email.smtp_password);
    }
    
    return settings;
  }

  /**
   * Store current processing results
   * @param {Object} results - Processing results
   * @returns {Promise<void>}
   */
  async setCurrentResults(results) {
    return this.set('current_results', results);
  }

  /**
   * Retrieve current processing results
   * @returns {Promise<Object|null>} Processing results or null
   */
  async getCurrentResults() {
    return this.get('current_results');
  }

  /**
   * Clear current processing results
   * @returns {Promise<void>}
   */
  async clearCurrentResults() {
    return this.remove('current_results');
  }
}

// Export singleton instance
const storageManager = new StorageManager();

// For use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = storageManager;
}
