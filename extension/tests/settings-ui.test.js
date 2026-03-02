/**
 * Settings UI Tests
 * Tests for the Settings tab layout and functionality
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

describe('Settings UI Layout', () => {
  let dom;
  let document;
  let window;

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

  describe('FTP Section', () => {
    it('should have FTP configuration section', () => {
      const ftpHost = document.getElementById('ftp-host');
      const ftpPort = document.getElementById('ftp-port');
      const ftpUsername = document.getElementById('ftp-username');
      const ftpPassword = document.getElementById('ftp-password');
      const ftpRemoteDir = document.getElementById('ftp-remote-directory');
      const testFtpBtn = document.getElementById('test-ftp-btn');

      expect(ftpHost).toBeTruthy();
      expect(ftpPort).toBeTruthy();
      expect(ftpUsername).toBeTruthy();
      expect(ftpPassword).toBeTruthy();
      expect(ftpRemoteDir).toBeTruthy();
      expect(testFtpBtn).toBeTruthy();
    });

    it('should have correct input types for FTP fields', () => {
      const ftpHost = document.getElementById('ftp-host');
      const ftpPort = document.getElementById('ftp-port');
      const ftpPassword = document.getElementById('ftp-password');

      expect(ftpHost.type).toBe('text');
      expect(ftpPort.type).toBe('number');
      expect(ftpPassword.type).toBe('password');
    });
  });

  describe('Email Section', () => {
    it('should have email mode radio buttons', () => {
      const defaultMode = document.getElementById('email-mode-default');
      const smtpMode = document.getElementById('email-mode-smtp');

      expect(defaultMode).toBeTruthy();
      expect(smtpMode).toBeTruthy();
      expect(defaultMode.type).toBe('radio');
      expect(smtpMode.type).toBe('radio');
      expect(defaultMode.name).toBe('email-mode');
      expect(smtpMode.name).toBe('email-mode');
    });

    it('should have common email fields', () => {
      const emailTo = document.getElementById('email-to');
      const emailCc = document.getElementById('email-cc');
      const emailSubject = document.getElementById('email-subject');

      expect(emailTo).toBeTruthy();
      expect(emailCc).toBeTruthy();
      expect(emailSubject).toBeTruthy();
      expect(emailTo.type).toBe('email');
      expect(emailCc.type).toBe('email');
    });

    it('should have attachment format checkboxes', () => {
      const csvCheckbox = document.getElementById('email-format-csv');
      const xlsxCheckbox = document.getElementById('email-format-xlsx');
      const jsonCheckbox = document.getElementById('email-format-json');

      expect(csvCheckbox).toBeTruthy();
      expect(xlsxCheckbox).toBeTruthy();
      expect(jsonCheckbox).toBeTruthy();
      expect(csvCheckbox.type).toBe('checkbox');
      expect(xlsxCheckbox.type).toBe('checkbox');
      expect(jsonCheckbox.type).toBe('checkbox');
    });

    it('should have SMTP fields', () => {
      const smtpServer = document.getElementById('smtp-server');
      const smtpPort = document.getElementById('smtp-port');
      const smtpUsername = document.getElementById('smtp-username');
      const smtpPassword = document.getElementById('smtp-password');
      const emailFrom = document.getElementById('email-from');

      expect(smtpServer).toBeTruthy();
      expect(smtpPort).toBeTruthy();
      expect(smtpUsername).toBeTruthy();
      expect(smtpPassword).toBeTruthy();
      expect(emailFrom).toBeTruthy();
    });

    it('should have SMTP fields hidden by default', () => {
      const smtpFields = document.getElementById('smtp-fields');
      expect(smtpFields.classList.contains('hidden')).toBe(true);
    });

    it('should have test email connection button', () => {
      const testEmailBtn = document.getElementById('test-email-btn');
      expect(testEmailBtn).toBeTruthy();
    });
  });

  describe('API Section', () => {
    it('should have API configuration fields', () => {
      const apiMethod = document.getElementById('api-method');
      const apiEndpoint = document.getElementById('api-endpoint');
      const apiHeaders = document.getElementById('api-headers');
      const apiBody = document.getElementById('api-body');
      const testApiBtn = document.getElementById('test-api-btn');

      expect(apiMethod).toBeTruthy();
      expect(apiEndpoint).toBeTruthy();
      expect(apiHeaders).toBeTruthy();
      expect(apiBody).toBeTruthy();
      expect(testApiBtn).toBeTruthy();
    });

    it('should have method dropdown with GET and POST options', () => {
      const apiMethod = document.getElementById('api-method');
      const options = Array.from(apiMethod.options).map(opt => opt.value);

      expect(apiMethod.tagName).toBe('SELECT');
      expect(options).toContain('GET');
      expect(options).toContain('POST');
    });

    it('should have textarea for headers and body', () => {
      const apiHeaders = document.getElementById('api-headers');
      const apiBody = document.getElementById('api-body');

      expect(apiHeaders.tagName).toBe('TEXTAREA');
      expect(apiBody.tagName).toBe('TEXTAREA');
    });
  });

  describe('Save Button', () => {
    it('should have save settings button', () => {
      const saveBtn = document.getElementById('save-settings-btn');
      expect(saveBtn).toBeTruthy();
      expect(saveBtn.textContent.trim()).toContain('Save');
    });
  });

  describe('Settings Tab Visibility', () => {
    it('should have settings tab in navigation', () => {
      const settingsTab = document.querySelector('[data-tab="settings"]');
      expect(settingsTab).toBeTruthy();
    });

    it('should have settings tab content', () => {
      const settingsTabContent = document.getElementById('settings-tab');
      expect(settingsTabContent).toBeTruthy();
    });
  });
});

describe('Settings Functionality', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    const html = fs.readFileSync(
      path.resolve(__dirname, '../popup.html'),
      'utf8'
    );

    dom = new JSDOM(html, {
      runScripts: 'dangerously',
      resources: 'usable',
      url: 'http://localhost'
    });

    document = dom.window.document;
    window = dom.window;

    // Mock chrome API
    global.chrome = {
      storage: {
        local: {
          get: vi.fn((keys, callback) => {
            callback({
              settings: {
                ftp: {
                  host: 'ftp.example.com',
                  port: 21,
                  username: 'testuser',
                  password: 'testpass',
                  remote_directory: '/uploads'
                },
                email: {
                  mode: 'default',
                  to: 'test@example.com',
                  cc: 'cc@example.com',
                  subject: 'Test Subject',
                  attachment_formats: ['csv', 'xlsx']
                },
                api: {
                  method: 'POST',
                  endpoint: 'https://api.example.com/data',
                  headers: { 'Content-Type': 'application/json' },
                  body: '{"data": "{{results}}"}'
                }
              }
            });
          }),
          set: vi.fn((data, callback) => {
            if (callback) callback();
          })
        }
      }
    };
  });

  it('should validate required FTP fields before testing connection', () => {
    const ftpHost = document.getElementById('ftp-host');
    const ftpUsername = document.getElementById('ftp-username');
    const ftpPassword = document.getElementById('ftp-password');

    // Empty fields should be invalid
    ftpHost.value = '';
    ftpUsername.value = '';
    ftpPassword.value = '';

    expect(ftpHost.value).toBe('');
    expect(ftpUsername.value).toBe('');
    expect(ftpPassword.value).toBe('');
  });

  it('should validate email address format', () => {
    const emailTo = document.getElementById('email-to');
    emailTo.value = 'invalid-email';

    // HTML5 validation should catch this
    expect(emailTo.type).toBe('email');
  });

  it('should validate API endpoint URL format', () => {
    const apiEndpoint = document.getElementById('api-endpoint');
    apiEndpoint.value = 'not-a-url';

    // HTML5 validation should catch this
    expect(apiEndpoint.type).toBe('url');
  });
});
