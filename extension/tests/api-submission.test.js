/**
 * Tests for API Submission functionality
 * Requirements: 3.6, 3.8, 3.9
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Dashboard - API Submission', () => {
  let dom;
  let document;
  let window;
  let dashboardState;
  let storageManager;
  let displayAlert;
  let handleSubmitToAPI;

  beforeEach(() => {
    // Create a new JSDOM instance
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <button id="submit-api-btn">Submit to API</button>
          <div id="alert-container"></div>
        </body>
      </html>
    `);

    document = dom.window.document;
    window = dom.window;
    global.document = document;
    global.window = window;

    // Mock dashboardState
    dashboardState = {
      currentResults: {
        'Invoice Number': 'INV-001',
        'Invoice Date': '2024-01-15',
        'Vendor Name': 'Acme Corp',
        'Total Amount': '1500.00'
      }
    };

    // Mock storageManager
    storageManager = {
      getAPISettings: vi.fn()
    };

    // Mock displayAlert
    displayAlert = vi.fn();

    // Mock fetch
    global.fetch = vi.fn();

    // Define handleSubmitToAPI function
    handleSubmitToAPI = async function() {
      try {
        // Check if there's data to submit
        if (!dashboardState.currentResults || Object.keys(dashboardState.currentResults).length === 0) {
          displayAlert('No data available to submit', 'warning');
          return;
        }

        // Retrieve API configuration from Local Storage (Requirement 3.6)
        const apiSettings = await storageManager.getAPISettings();
        
        if (!apiSettings) {
          displayAlert('API configuration not found. Please configure API settings first.', 'warning');
          return;
        }

        // Validate API configuration
        if (!apiSettings.endpoint) {
          displayAlert('Incomplete API configuration. Please check your API settings.', 'warning');
          return;
        }

        // Validate method
        const method = apiSettings.method || 'POST';
        if (!['GET', 'POST'].includes(method)) {
          displayAlert('Invalid API method. Only GET and POST are supported.', 'warning');
          return;
        }

        // Prepare the data to send
        const dataToSend = dashboardState.currentResults;

        // Parse headers if provided
        let headers = {
          'Content-Type': 'application/json'
        };
        
        if (apiSettings.headers) {
          try {
            // If headers is a string, parse it as JSON
            const customHeaders = typeof apiSettings.headers === 'string' 
              ? JSON.parse(apiSettings.headers) 
              : apiSettings.headers;
            headers = { ...headers, ...customHeaders };
          } catch (error) {
            console.warn('Failed to parse custom headers:', error);
            displayAlert('Invalid header format in API configuration. Using default headers.', 'warning');
          }
        }

        // Prepare request options
        const options = {
          method: method,
          headers: headers
        };

        // For POST requests, include body
        if (method === 'POST') {
          // If custom body template is provided, use it; otherwise send the data directly
          if (apiSettings.body) {
            try {
              // Replace placeholders in body template with actual data
              let bodyTemplate = apiSettings.body;
              
              // Simple placeholder replacement: {{fieldName}} with actual values
              Object.entries(dataToSend).forEach(([field, value]) => {
                const placeholder = new RegExp(`{{${field}}}`, 'g');
                bodyTemplate = bodyTemplate.replace(placeholder, value || '');
              });
              
              options.body = bodyTemplate;
            } catch (error) {
              console.warn('Failed to process body template:', error);
              // Fallback to sending data as JSON
              options.body = JSON.stringify(dataToSend);
            }
          } else {
            // Default: send data as JSON
            options.body = JSON.stringify(dataToSend);
          }
        }

        // Send data to configured endpoint (Requirement 3.6)
        const response = await fetch(apiSettings.endpoint, options);

        // Check response status
        if (!response.ok) {
          throw new Error(`API request failed with status ${response.status}: ${response.statusText}`);
        }

        // Try to parse response
        let responseData;
        try {
          responseData = await response.json();
        } catch (error) {
          // Response might not be JSON, that's okay
          responseData = await response.text();
        }

        // Display success alert (Requirement 3.9)
        displayAlert(
          'Data submitted successfully to external API',
          'success'
        );
      } catch (error) {
        console.error('Error submitting to API:', error);
        
        // Display error alert (Requirement 3.8)
        displayAlert(
          error.message || 'Failed to submit data to external API. Please check your API configuration and try again.',
          'error'
        );
      }
    };
  });

  it('should retrieve API configuration from Local Storage', async () => {
    // Test Requirement 3.6 - Retrieve API configuration from Local_Storage
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: { 'Authorization': 'Bearer token123' },
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(storageManager.getAPISettings).toHaveBeenCalled();
  });

  it('should send data to configured endpoint with POST method', async () => {
    // Test Requirement 3.6 - Send data to configured endpoint
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/webhook',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify(dashboardState.currentResults)
      })
    );
  });

  it('should send data to configured endpoint with GET method', async () => {
    // Test Requirement 3.6 - Support GET method
    const mockApiSettings = {
      method: 'GET',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/webhook',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        })
      })
    );
    
    // GET requests should not have a body
    const fetchCall = global.fetch.mock.calls[0][1];
    expect(fetchCall.body).toBeUndefined();
  });

  it('should include configured headers in the request', async () => {
    // Test Requirement 3.6 - Include configured headers
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: {
        'Authorization': 'Bearer token123',
        'X-Custom-Header': 'custom-value'
      },
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/webhook',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'Authorization': 'Bearer token123',
          'X-Custom-Header': 'custom-value'
        })
      })
    );
  });

  it('should parse headers from JSON string', async () => {
    // Test Requirement 3.6 - Parse headers if provided as string
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: '{"Authorization": "Bearer token123"}',
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/webhook',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer token123'
        })
      })
    );
  });

  it('should use custom body template with placeholder replacement', async () => {
    // Test Requirement 3.6 - Support custom body template
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: '{"invoice": "{{Invoice Number}}", "vendor": "{{Vendor Name}}", "amount": "{{Total Amount}}"}'
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/webhook',
      expect.objectContaining({
        body: '{"invoice": "INV-001", "vendor": "Acme Corp", "amount": "1500.00"}'
      })
    );
  });

  it('should display success alert when submission succeeds', async () => {
    // Test Requirement 3.9 - Display success alert
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'Data submitted successfully to external API',
      'success'
    );
  });

  it('should display error alert when submission fails', async () => {
    // Test Requirement 3.8 - Display error alert on failure
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error'
    });

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'API request failed with status 500: Internal Server Error',
      'error'
    );
  });

  it('should display error alert when network error occurs', async () => {
    // Test Requirement 3.8 - Display error alert on network error
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockRejectedValue(new Error('Network error'));

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'Network error',
      'error'
    );
  });

  it('should display warning when no data is available', async () => {
    // Test edge case - No data to submit
    dashboardState.currentResults = {};

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'No data available to submit',
      'warning'
    );
    expect(storageManager.getAPISettings).not.toHaveBeenCalled();
  });

  it('should display warning when API configuration is not found', async () => {
    // Test edge case - No API configuration
    storageManager.getAPISettings.mockResolvedValue(null);

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'API configuration not found. Please configure API settings first.',
      'warning'
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should display warning when endpoint is missing', async () => {
    // Test edge case - Incomplete configuration
    const mockApiSettings = {
      method: 'POST',
      endpoint: '',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'Incomplete API configuration. Please check your API settings.',
      'warning'
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should display warning when method is invalid', async () => {
    // Test edge case - Invalid HTTP method
    const mockApiSettings = {
      method: 'DELETE',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'Invalid API method. Only GET and POST are supported.',
      'warning'
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should handle invalid header JSON gracefully', async () => {
    // Test edge case - Invalid header JSON
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: 'invalid json',
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    // Should display warning about invalid headers but continue with default headers
    expect(displayAlert).toHaveBeenCalledWith(
      'Invalid header format in API configuration. Using default headers.',
      'warning'
    );
    
    // Should still make the request with default headers
    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/webhook',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        })
      })
    );
  });

  it('should handle non-JSON response gracefully', async () => {
    // Test edge case - Non-JSON response
    const mockApiSettings = {
      method: 'POST',
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => { throw new Error('Not JSON'); },
      text: async () => 'Success'
    });

    await handleSubmitToAPI();

    expect(displayAlert).toHaveBeenCalledWith(
      'Data submitted successfully to external API',
      'success'
    );
  });

  it('should default to POST method if not specified', async () => {
    // Test edge case - No method specified
    const mockApiSettings = {
      endpoint: 'https://api.example.com/webhook',
      headers: null,
      body: null
    };

    storageManager.getAPISettings.mockResolvedValue(mockApiSettings);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    await handleSubmitToAPI();

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/webhook',
      expect.objectContaining({
        method: 'POST'
      })
    );
  });
});
