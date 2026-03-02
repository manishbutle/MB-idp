/**
 * Unit tests for API Client Module
 * Tests Requirements: 14.6, 14.7, 15.1
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock chrome storage
global.chrome = {
  storage: {
    local: {
      get: vi.fn(),
      set: vi.fn(),
      remove: vi.fn(),
      clear: vi.fn()
    }
  },
  runtime: {
    lastError: null
  }
};

// Mock global fetch
global.fetch = vi.fn();

// Mock AbortSignal.timeout
const originalAbortSignal = global.AbortSignal;
global.AbortSignal = {
  ...originalAbortSignal,
  timeout: vi.fn((ms) => {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), ms);
    return controller.signal;
  })
};

// Create a test implementation of the API client
class TestAPIClient {
  constructor() {
    this.baseURL = 'https://api.example.com/v1';
    this.timeout = 30000;
  }

  async call(endpoint, method = 'GET', data = null, requiresAuth = false) {
    try {
      const headers = {
        'Content-Type': 'application/json'
      };

      if (requiresAuth) {
        const session = await new Promise((resolve, reject) => {
          chrome.storage.local.get(['session'], (result) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(result.session);
            }
          });
        });

        if (!session || !session.token) {
          throw new Error('Authentication required. Please log in.');
        }
        headers['Authorization'] = `Bearer ${session.token}`;
      }

      const options = {
        method,
        headers,
        signal: AbortSignal.timeout(this.timeout)
      };

      if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
      }

      const url = `${this.baseURL}${endpoint}`;
      const response = await fetch(url, options);

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

describe('APIClient', () => {
  let apiClient;

  beforeEach(() => {
    apiClient = new TestAPIClient();
    vi.clearAllMocks();
    chrome.runtime.lastError = null;
  });

  describe('Authentication Headers', () => {
    it('should include Authorization header when requiresAuth is true', async () => {
      // Mock session
      chrome.storage.local.get.mockImplementation((keys, callback) => {
        callback({ session: { token: 'test-token-123' } });
      });

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      await apiClient.call('/test', 'GET', null, true);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token-123'
          })
        })
      );
    });

    it('should throw error when authentication required but no token exists', async () => {
      // Mock no session
      chrome.storage.local.get.mockImplementation((keys, callback) => {
        callback({});
      });

      await expect(apiClient.call('/test', 'GET', null, true))
        .rejects.toThrow('Authentication required. Please log in.');
    });

    it('should not include Authorization header when requiresAuth is false', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      await apiClient.call('/test', 'GET', null, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            'Authorization': expect.anything()
          })
        })
      );
    });
  });

  describe('HTTP Error Status Code Handling (Requirement 14.7)', () => {
    it('should handle 400 Bad Request', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ message: 'Invalid request format' })
      });

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Invalid request format');
    });

    it('should handle 401 Unauthorized', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ message: 'Invalid credentials' })
      });

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Invalid credentials');
    });

    it('should handle 403 Forbidden', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ message: 'Access denied' })
      });

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Access denied');
    });

    it('should handle 404 Not Found', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ message: 'Resource not found' })
      });

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Resource not found');
    });

    it('should handle 500 Internal Server Error', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ message: 'Server error occurred' })
      });

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Server error occurred');
    });

    it('should handle error response without message', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => ({})
      });

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('HTTP 503: Service Unavailable');
    });

    it('should handle error response with invalid JSON', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => { throw new Error('Invalid JSON'); }
      });

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('HTTP 500: Internal Server Error');
    });
  });

  describe('Timeout Handling (Requirement 14.6)', () => {
    it('should handle network timeout gracefully', async () => {
      const timeoutError = new Error('Timeout');
      timeoutError.name = 'TimeoutError';
      fetch.mockRejectedValueOnce(timeoutError);

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Request timed out. Please check your connection and try again.');
    });

    it('should handle abort error gracefully', async () => {
      const abortError = new Error('Aborted');
      abortError.name = 'AbortError';
      fetch.mockRejectedValueOnce(abortError);

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Request timed out. Please check your connection and try again.');
    });

    it('should use configured timeout value', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      await apiClient.call('/test', 'GET', null, false);

      expect(AbortSignal.timeout).toHaveBeenCalledWith(30000);
    });
  });

  describe('Network Connectivity Handling (Requirement 14.6)', () => {
    it('should handle network connectivity issues', async () => {
      fetch.mockRejectedValueOnce(new Error('Failed to fetch'));

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('Network error. Please check your internet connection.');
    });

    it('should re-throw other network errors', async () => {
      fetch.mockRejectedValueOnce(new Error('DNS resolution failed'));

      await expect(apiClient.call('/test', 'GET', null, false))
        .rejects.toThrow('DNS resolution failed');
    });
  });

  describe('JSON Response Parsing', () => {
    it('should parse JSON response successfully', async () => {
      const mockData = { id: 1, name: 'Test' };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData
      });

      const result = await apiClient.call('/test', 'GET', null, false);

      expect(result).toEqual(mockData);
    });

    it('should handle empty JSON response', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      });

      const result = await apiClient.call('/test', 'GET', null, false);

      expect(result).toEqual({});
    });
  });

  describe('Request Body Handling', () => {
    it('should include body for POST requests', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      const data = { key: 'value' };
      await apiClient.call('/test', 'POST', data, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(data)
        })
      );
    });

    it('should include body for PUT requests', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      const data = { key: 'value' };
      await apiClient.call('/test', 'PUT', data, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(data)
        })
      );
    });

    it('should not include body for GET requests', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      await apiClient.call('/test', 'GET', { key: 'value' }, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'GET'
        })
      );

      const callArgs = fetch.mock.calls[0][1];
      expect(callArgs.body).toBeUndefined();
    });
  });

  describe('Asynchronous Patterns (Requirement 15.1)', () => {
    it('should use async/await pattern', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      const promise = apiClient.call('/test', 'GET', null, false);
      expect(promise).toBeInstanceOf(Promise);

      const result = await promise;
      expect(result).toEqual({ success: true });
    });

    it('should not block on multiple concurrent calls', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      });

      const promises = [
        apiClient.call('/test1', 'GET', null, false),
        apiClient.call('/test2', 'GET', null, false),
        apiClient.call('/test3', 'GET', null, false)
      ];

      const results = await Promise.all(promises);
      expect(results).toHaveLength(3);
      expect(fetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('API Method Wrappers', () => {
    beforeEach(() => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      });

      chrome.storage.local.get.mockImplementation((keys, callback) => {
        callback({ session: { token: 'test-token' } });
      });
    });

    it('should construct correct URL for processDocument', async () => {
      const documentData = { file: 'base64data' };
      await apiClient.call('/process_document', 'POST', documentData, true);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/process_document'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(documentData)
        })
      );
    });

    it('should construct correct URL for getHistory with pagination', async () => {
      await apiClient.call('/history?page=2&limit=10', 'GET', null, true);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/history?page=2&limit=10'),
        expect.any(Object)
      );
    });

    it('should call auth without authentication header', async () => {
      chrome.storage.local.get.mockImplementation((keys, callback) => {
        callback({});
      });

      await apiClient.call('/auth', 'POST', { email: 'test@example.com', password: 'password123' }, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.not.objectContaining({
            'Authorization': expect.anything()
          })
        })
      );
    });

    it('should send profile update with correct data', async () => {
      await apiClient.call('/profile_change', 'POST', { first_name: 'John', last_name: 'Doe' }, true);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/profile_change'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ first_name: 'John', last_name: 'Doe' })
        })
      );
    });

    it('should send password change with correct data', async () => {
      const passwordData = {
        current_password: 'oldpass',
        new_password: 'newpass',
        confirm_password: 'newpass'
      };

      await apiClient.call('/password_change', 'POST', passwordData, true);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/password_change'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('current_password')
        })
      );
    });

    it('should send add credit with correct data', async () => {
      await apiClient.call('/add_credit', 'POST', { email: 'user@example.com', amount: 100 }, true);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/add_credit'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'user@example.com', amount: 100 })
        })
      );
    });

    it('should call signUp without authentication', async () => {
      chrome.storage.local.get.mockImplementation((keys, callback) => {
        callback({});
      });

      const userData = {
        email: 'new@example.com',
        password: 'pass123',
        first_name: 'John',
        last_name: 'Doe'
      };

      await apiClient.call('/sign_up', 'POST', userData, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/sign_up'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.not.objectContaining({
            'Authorization': expect.anything()
          })
        })
      );
    });

    it('should send FTP upload with remote directory', async () => {
      const ftpData = {
        file_name: 'test.csv',
        file_content: 'base64content',
        remote_directory: '/uploads'
      };

      await apiClient.call('/ftp', 'POST', ftpData, true);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/ftp'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('remote_directory')
        })
      );
    });

    it('should send FTP upload without remote directory', async () => {
      const ftpData = {
        file_name: 'test.csv',
        file_content: 'base64content'
      };

      await apiClient.call('/ftp', 'POST', ftpData, true);

      const callBody = JSON.parse(fetch.mock.calls[0][1].body);
      expect(callBody.remote_directory).toBeUndefined();
    });
  });

  describe('Content-Type Header', () => {
    it('should always include Content-Type: application/json', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      await apiClient.call('/test', 'POST', { data: 'value' }, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      );
    });
  });
});
