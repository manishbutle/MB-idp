/**
 * Connection Testing Tests
 * Tests for FTP, Email, and API connection testing functionality
 * Requirements: 5.7, 5.8, 5.10, 5.13, 5.14
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

describe('Connection Testing', () => {
  let dom;
  let document;
  let window;
  let mockApiCall;
  let mockFetch;
  let mockShowAlert;
  let mockShowLoading;
  let mockHideLoading;

  beforeEach(() => {
    // Load the HTML file
    const html = fs.readFileSync(
      path.resolve(__dirname, '../popup.html'),
      'utf8'
    );

    // Create a new JSDOM instance
    dom = new JSDOM(html, {
      runScripts: 'dangerously',
      resources: 'usable',
      url: 'http://localhost'
    });

    document = dom.window.document;
    window = dom.window;

    // Mock global functions
    mockShowAlert = vi.fn();
    mockShowLoading = vi.fn();
    mockHideLoading = vi.fn();
    mockApiCall = vi.fn();
    mockFetch = vi.fn();

    // Inject mocks into window
    window.showAlert = mockShowAlert;
    window.showLoading = mockShowLoading;
    window.hideLoading = mockHideLoading;
    window.apiCall = mockApiCall;
    window.fetch = mockFetch;
    global.fetch = mockFetch;

    // Mock chrome API
    global.chrome = {
      storage: {
        local: {
          get: vi.fn((keys, callback) => {
            callback({ settings: {} });
          }),
          set: vi.fn((data, callback) => {
            if (callback) callback();
          })
        }
      }
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('FTP Connection Testing', () => {
    beforeEach(() => {
      // Set up FTP form fields
      document.getElementById('ftp-host').value = 'ftp.example.com';
      document.getElementById('ftp-port').value = '21';
      document.getElementById('ftp-username').value = 'testuser';
      document.getElementById('ftp-password').value = 'testpass';
      document.getElementById('ftp-remote-directory').value = '/uploads';
    });

    it('should validate required FTP fields before testing', async () => {
      // Clear required fields
      document.getElementById('ftp-host').value = '';
      document.getElementById('ftp-username').value = '';
      document.getElementById('ftp-password').value = '';

      // Load and execute settings script
      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      // Wait for script to load
      await new Promise(resolve => setTimeout(resolve, 100));

      // Trigger test connection
      const testBtn = document.getElementById('test-ftp-btn');
      testBtn.click();

      // Wait for async operations
      await new Promise(resolve => setTimeout(resolve, 100));

      // Should show error alert for missing fields
      expect(mockShowLoading).toHaveBeenCalled();
      expect(mockHideLoading).toHaveBeenCalled();
      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('required FTP fields')
      );
    });

    it('should call FTP API with correct configuration on test', async () => {
      mockApiCall.mockResolvedValue({ success: true });

      // Load and execute settings script
      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Trigger test connection
      const testBtn = document.getElementById('test-ftp-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      // Should call API with correct parameters
      expect(mockApiCall).toHaveBeenCalledWith(
        '/ftp',
        'POST',
        expect.objectContaining({
          config: expect.objectContaining({
            host: 'ftp.example.com',
            port: 21,
            username: 'testuser',
            password: 'testpass',
            remote_directory: '/uploads'
          }),
          test: true
        })
      );
    });

    it('should display success alert when FTP connection succeeds (Requirement 5.13)', async () => {
      mockApiCall.mockResolvedValue({ success: true });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-ftp-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'success',
        'FTP connection successful'
      );
    });

    it('should display error alert when FTP connection fails (Requirement 5.14)', async () => {
      mockApiCall.mockResolvedValue({ 
        success: false, 
        message: 'Connection timeout' 
      });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-ftp-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        'Connection timeout'
      );
    });

    it('should handle FTP API errors gracefully (Requirement 5.14)', async () => {
      mockApiCall.mockRejectedValue(new Error('Network error'));

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-ftp-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('Network error')
      );
    });

    it('should show and hide loading indicator during FTP test', async () => {
      mockApiCall.mockResolvedValue({ success: true });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-ftp-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowLoading).toHaveBeenCalled();
      expect(mockHideLoading).toHaveBeenCalled();
    });
  });

  describe('Email Connection Testing - Default Server', () => {
    beforeEach(() => {
      // Set up email form fields for default server
      document.getElementById('email-mode-default').checked = true;
      document.getElementById('email-to').value = 'test@example.com';
      document.getElementById('email-cc').value = 'cc@example.com';
      document.getElementById('email-subject').value = 'Test Subject';
    });

    it('should validate email address before testing (Requirement 5.7)', async () => {
      // Clear email address
      document.getElementById('email-to').value = '';

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-email-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('email address')
      );
    });

    it('should call send_email API when testing default server (Requirement 5.7)', async () => {
      mockApiCall.mockResolvedValue({ success: true });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-email-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockApiCall).toHaveBeenCalledWith(
        '/send_email',
        'POST',
        expect.objectContaining({
          to: 'test@example.com',
          subject: 'Test Email',
          test: true
        })
      );
    });

    it('should display success alert when email test succeeds (Requirement 5.13)', async () => {
      mockApiCall.mockResolvedValue({ success: true });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-email-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'success',
        expect.stringContaining('Email sent successfully')
      );
    });

    it('should display error alert when email test fails (Requirement 5.14)', async () => {
      mockApiCall.mockResolvedValue({ 
        success: false, 
        message: 'Invalid email address' 
      });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-email-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        'Invalid email address'
      );
    });
  });

  describe('Email Connection Testing - SMTP Server', () => {
    beforeEach(() => {
      // Set up email form fields for SMTP
      document.getElementById('email-mode-smtp').checked = true;
      document.getElementById('email-to').value = 'test@example.com';
      document.getElementById('smtp-server').value = 'smtp.example.com';
      document.getElementById('smtp-port').value = '587';
      document.getElementById('smtp-username').value = 'smtpuser';
      document.getElementById('smtp-password').value = 'smtppass';
      document.getElementById('email-from').value = 'sender@example.com';
    });

    it('should validate required SMTP fields before testing (Requirement 5.8)', async () => {
      // Clear required SMTP fields
      document.getElementById('smtp-server').value = '';
      document.getElementById('smtp-username').value = '';
      document.getElementById('smtp-password').value = '';
      document.getElementById('email-from').value = '';

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-email-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('required SMTP fields')
      );
    });

    it('should validate SMTP configuration when testing (Requirement 5.8)', async () => {
      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-email-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      // Should show info alert about SMTP validation
      // (Full SMTP testing requires smtp.js library)
      expect(mockShowAlert).toHaveBeenCalled();
    });

    it('should handle SMTP test errors gracefully (Requirement 5.14)', async () => {
      // Simulate error during SMTP test
      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Mock an error scenario
      window.apiCall = vi.fn().mockRejectedValue(new Error('SMTP connection failed'));

      const testBtn = document.getElementById('test-email-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      // Should handle error gracefully
      expect(mockShowLoading).toHaveBeenCalled();
      expect(mockHideLoading).toHaveBeenCalled();
    });
  });

  describe('API Connection Testing', () => {
    beforeEach(() => {
      // Set up API form fields
      document.getElementById('api-method').value = 'POST';
      document.getElementById('api-endpoint').value = 'https://api.example.com/data';
      document.getElementById('api-headers').value = JSON.stringify({
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token123'
      }, null, 2);
      document.getElementById('api-body').value = '{"test": true}';
    });

    it('should validate API endpoint before testing (Requirement 5.10)', async () => {
      // Clear endpoint
      document.getElementById('api-endpoint').value = '';

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('API endpoint')
      );
    });

    it('should validate JSON format in API headers (Requirement 5.10)', async () => {
      // Set invalid JSON
      document.getElementById('api-headers').value = '{invalid json}';

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('Invalid JSON')
      );
    });

    it('should send test request to configured endpoint (Requirement 5.10)', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200
      });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/data',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer token123'
          })
        })
      );
    });

    it('should display success alert when API test succeeds (Requirement 5.13)', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200
      });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'success',
        expect.stringContaining('API connection successful')
      );
    });

    it('should display error alert when API test fails (Requirement 5.14)', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404
      });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('404')
      );
    });

    it('should handle API network errors gracefully (Requirement 5.14)', async () => {
      mockFetch.mockRejectedValue(new Error('Network timeout'));

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowAlert).toHaveBeenCalledWith(
        'error',
        expect.stringContaining('Network timeout')
      );
    });

    it('should support GET method for API testing', async () => {
      document.getElementById('api-method').value = 'GET';
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200
      });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/data',
        expect.objectContaining({
          method: 'GET',
          body: undefined
        })
      );
    });

    it('should show and hide loading indicator during API test', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200
      });

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      const testBtn = document.getElementById('test-api-btn');
      testBtn.click();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockShowLoading).toHaveBeenCalled();
      expect(mockHideLoading).toHaveBeenCalled();
    });
  });

  describe('Connection Testing Integration', () => {
    it('should have all three test connection buttons in the UI', () => {
      const ftpTestBtn = document.getElementById('test-ftp-btn');
      const emailTestBtn = document.getElementById('test-email-btn');
      const apiTestBtn = document.getElementById('test-api-btn');

      expect(ftpTestBtn).toBeTruthy();
      expect(emailTestBtn).toBeTruthy();
      expect(apiTestBtn).toBeTruthy();
    });

    it('should allow testing connections independently', async () => {
      mockApiCall.mockResolvedValue({ success: true });
      mockFetch.mockResolvedValue({ ok: true, status: 200 });

      // Set up all form fields
      document.getElementById('ftp-host').value = 'ftp.example.com';
      document.getElementById('ftp-username').value = 'user';
      document.getElementById('ftp-password').value = 'pass';
      document.getElementById('email-to').value = 'test@example.com';
      document.getElementById('api-endpoint').value = 'https://api.example.com';

      const settingsScript = fs.readFileSync(
        path.resolve(__dirname, '../scripts/settings.js'),
        'utf8'
      );
      const scriptElement = document.createElement('script');
      scriptElement.textContent = settingsScript;
      document.body.appendChild(scriptElement);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Clear any alerts from initialization
      mockShowAlert.mockClear();

      // Test each connection independently
      const ftpBtn = document.getElementById('test-ftp-btn');
      const emailBtn = document.getElementById('test-email-btn');
      const apiBtn = document.getElementById('test-api-btn');

      ftpBtn.click();
      await new Promise(resolve => setTimeout(resolve, 100));

      emailBtn.click();
      await new Promise(resolve => setTimeout(resolve, 100));

      apiBtn.click();
      await new Promise(resolve => setTimeout(resolve, 100));

      // All three should have been called
      expect(mockApiCall).toHaveBeenCalled();
      expect(mockFetch).toHaveBeenCalled();
      // Should have at least 3 alerts (one for each test)
      expect(mockShowAlert).toHaveBeenCalled();
      expect(mockShowAlert.mock.calls.length).toBeGreaterThanOrEqual(3);
    });
  });
});
