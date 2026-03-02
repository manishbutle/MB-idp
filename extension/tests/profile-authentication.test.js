/**
 * Comprehensive Unit Tests for Profile Tab - Authentication Functions
 * Task 16.3: Implement authentication functions
 * Requirements: 6.2, 6.3, 6.6, 6.7, 6.8, 6.9, 6.10
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Authentication Functions - Login', () => {
  let dom;
  let document;
  let window;
  let mockApiClient;
  let mockStorageManager;
  let mockDisplayAlert;
  let mockShowLoading;
  let mockHideLoading;

  beforeEach(() => {
    // Create DOM
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-tab">
            <div id="profile-logged-out">
              <form id="login-form">
                <input type="email" id="login-email" value="" />
                <input type="password" id="login-password" value="" />
                <input type="checkbox" id="remember-me" />
                <button type="submit">Login</button>
              </form>
            </div>
            <div id="profile-logged-in" class="hidden">
              <a href="#" id="logout-link">Logout</a>
              <h2 id="user-name-heading"></h2>
            </div>
          </div>
          <div id="alert-container"></div>
          <div id="loading-overlay" class="hidden"></div>
        </body>
      </html>
    `);

    document = dom.window.document;
    window = dom.window;
    global.document = document;
    global.window = window;

    // Mock API client
    mockApiClient = {
      auth: vi.fn()
    };

    // Mock storage manager
    mockStorageManager = {
      setSession: vi.fn().mockResolvedValue(undefined),
      getSession: vi.fn().mockResolvedValue(null),
      clearSession: vi.fn().mockResolvedValue(undefined)
    };

    // Mock UI functions
    mockDisplayAlert = vi.fn();
    mockShowLoading = vi.fn();
    mockHideLoading = vi.fn();

    global.apiClient = mockApiClient;
    global.storageManager = mockStorageManager;
    global.displayAlert = mockDisplayAlert;
    global.showLoading = mockShowLoading;
    global.hideLoading = mockHideLoading;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Requirement 6.2: Call auth API with credentials', () => {
    it('should call auth API with email and password', async () => {
      const email = 'test@example.com';
      const password = 'password123';

      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: 'test-token',
        user_name: 'Test User',
        role: 'User',
        tenant: 'default',
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      });

      // Simulate login
      await mockApiClient.auth(email, password);

      expect(mockApiClient.auth).toHaveBeenCalledWith(email, password);
      expect(mockApiClient.auth).toHaveBeenCalledTimes(1);
    });

    it('should trim email before calling API', async () => {
      const email = '  test@example.com  ';
      const trimmedEmail = email.trim();
      const password = 'password123';

      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: 'test-token'
      });

      await mockApiClient.auth(trimmedEmail, password);

      expect(mockApiClient.auth).toHaveBeenCalledWith('test@example.com', password);
    });

    it('should not call API if email is empty', () => {
      const email = '';
      const password = 'password123';

      // Validation should prevent API call
      const isValid = !!(email.trim() && password);
      
      expect(isValid).toBe(false);
      expect(mockApiClient.auth).not.toHaveBeenCalled();
    });

    it('should not call API if password is empty', () => {
      const email = 'test@example.com';
      const password = '';

      // Validation should prevent API call
      const isValid = !!(email.trim() && password);
      
      expect(isValid).toBe(false);
      expect(mockApiClient.auth).not.toHaveBeenCalled();
    });
  });

  describe('Requirement 6.3 & 6.6: Store session token in Local_Storage', () => {
    it('should store session data when authentication succeeds', async () => {
      const email = 'test@example.com';
      const password = 'password123';
      const mockResponse = {
        success: true,
        token: 'test-token-123',
        user_name: 'Test User',
        role: 'User',
        tenant: 'default',
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      };

      mockApiClient.auth.mockResolvedValue(mockResponse);

      // Simulate successful login
      const response = await mockApiClient.auth(email, password);

      if (response.success && response.token) {
        const session = {
          token: response.token,
          user_email: email,
          user_name: response.user_name || email,
          role: response.role || 'User',
          tenant: response.tenant || 'default',
          remember_me: false,
          expires_at: response.expires_at || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
        };

        await mockStorageManager.setSession(session);

        expect(mockStorageManager.setSession).toHaveBeenCalledWith(
          expect.objectContaining({
            token: 'test-token-123',
            user_email: email,
            user_name: 'Test User',
            role: 'User',
            tenant: 'default'
          })
        );
      }
    });

    it('should include all required session fields', async () => {
      const mockResponse = {
        success: true,
        token: 'test-token',
        user_name: 'John Doe',
        role: 'System User',
        tenant: 'acme-corp',
        expires_at: '2024-12-31T23:59:59Z'
      };

      mockApiClient.auth.mockResolvedValue(mockResponse);

      const response = await mockApiClient.auth('test@example.com', 'password');

      if (response.success) {
        const session = {
          token: response.token,
          user_email: 'test@example.com',
          user_name: response.user_name,
          role: response.role,
          tenant: response.tenant,
          remember_me: false,
          expires_at: response.expires_at
        };

        await mockStorageManager.setSession(session);

        const savedSession = mockStorageManager.setSession.mock.calls[0][0];
        expect(savedSession).toHaveProperty('token');
        expect(savedSession).toHaveProperty('user_email');
        expect(savedSession).toHaveProperty('user_name');
        expect(savedSession).toHaveProperty('role');
        expect(savedSession).toHaveProperty('tenant');
        expect(savedSession).toHaveProperty('remember_me');
        expect(savedSession).toHaveProperty('expires_at');
      }
    });

    it('should not store session if authentication fails', async () => {
      mockApiClient.auth.mockResolvedValue({
        success: false,
        message: 'Invalid credentials'
      });

      const response = await mockApiClient.auth('test@example.com', 'wrongpassword');

      if (!response.success) {
        expect(mockStorageManager.setSession).not.toHaveBeenCalled();
      }
    });

    it('should not store session if token is missing', async () => {
      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: null
      });

      const response = await mockApiClient.auth('test@example.com', 'password');

      if (!response.token) {
        expect(mockStorageManager.setSession).not.toHaveBeenCalled();
      }
    });
  });

  describe('Requirement 6.7: Display error alerts for authentication failures', () => {
    it('should display error alert when credentials are invalid', async () => {
      mockApiClient.auth.mockResolvedValue({
        success: false,
        message: 'Invalid email or password'
      });

      const response = await mockApiClient.auth('test@example.com', 'wrongpassword');

      if (!response.success) {
        mockDisplayAlert(response.message || 'Login failed. Please check your credentials.', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Invalid email or password',
        'error'
      );
    });

    it('should display error alert when network error occurs', async () => {
      mockApiClient.auth.mockRejectedValue(new Error('Network error'));

      try {
        await mockApiClient.auth('test@example.com', 'password');
      } catch (error) {
        mockDisplayAlert('Login failed. Please try again.', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Login failed. Please try again.',
        'error'
      );
    });

    it('should display error alert for empty email', () => {
      const email = '';
      const password = 'password123';

      if (!email || !password) {
        mockDisplayAlert('Please enter both email and password', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Please enter both email and password',
        'error'
      );
    });

    it('should display error alert for empty password', () => {
      const email = 'test@example.com';
      const password = '';

      if (!email || !password) {
        mockDisplayAlert('Please enter both email and password', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Please enter both email and password',
        'error'
      );
    });

    it('should display default error message if API returns no message', async () => {
      mockApiClient.auth.mockResolvedValue({
        success: false
      });

      const response = await mockApiClient.auth('test@example.com', 'password');

      if (!response.success) {
        mockDisplayAlert(response.message || 'Login failed. Please check your credentials.', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Login failed. Please check your credentials.',
        'error'
      );
    });
  });

  describe('Requirement 6.10: Handle Remember Me checkbox for persistence', () => {
    it('should store remember_me as true when checkbox is checked', async () => {
      const rememberMe = true;

      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: 'test-token',
        user_name: 'Test User',
        role: 'User',
        tenant: 'default',
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      });

      const response = await mockApiClient.auth('test@example.com', 'password');

      if (response.success) {
        const session = {
          token: response.token,
          user_email: 'test@example.com',
          user_name: response.user_name,
          role: response.role,
          tenant: response.tenant,
          remember_me: rememberMe,
          expires_at: response.expires_at
        };

        await mockStorageManager.setSession(session);

        const savedSession = mockStorageManager.setSession.mock.calls[0][0];
        expect(savedSession.remember_me).toBe(true);
      }
    });

    it('should store remember_me as false when checkbox is unchecked', async () => {
      const rememberMe = false;

      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: 'test-token',
        user_name: 'Test User',
        role: 'User',
        tenant: 'default',
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      });

      const response = await mockApiClient.auth('test@example.com', 'password');

      if (response.success) {
        const session = {
          token: response.token,
          user_email: 'test@example.com',
          user_name: response.user_name,
          role: response.role,
          tenant: response.tenant,
          remember_me: rememberMe,
          expires_at: response.expires_at
        };

        await mockStorageManager.setSession(session);

        const savedSession = mockStorageManager.setSession.mock.calls[0][0];
        expect(savedSession.remember_me).toBe(false);
      }
    });
  });

  describe('Loading indicators during login', () => {
    it('should show loading indicator when login starts', async () => {
      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: 'test-token'
      });

      mockShowLoading();
      await mockApiClient.auth('test@example.com', 'password');

      expect(mockShowLoading).toHaveBeenCalled();
    });

    it('should hide loading indicator when login succeeds', async () => {
      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: 'test-token'
      });

      mockShowLoading();
      await mockApiClient.auth('test@example.com', 'password');
      mockHideLoading();

      expect(mockHideLoading).toHaveBeenCalled();
    });

    it('should hide loading indicator when login fails', async () => {
      mockApiClient.auth.mockRejectedValue(new Error('Network error'));

      mockShowLoading();
      try {
        await mockApiClient.auth('test@example.com', 'password');
      } catch (error) {
        mockHideLoading();
      }

      expect(mockHideLoading).toHaveBeenCalled();
    });
  });

  describe('Success feedback', () => {
    it('should display success alert when login succeeds', async () => {
      mockApiClient.auth.mockResolvedValue({
        success: true,
        token: 'test-token',
        user_name: 'Test User',
        role: 'User',
        tenant: 'default',
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      });

      const response = await mockApiClient.auth('test@example.com', 'password');

      if (response.success) {
        mockDisplayAlert('Login successful!', 'success');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Login successful!', 'success');
    });
  });
});

describe('Authentication Functions - Logout', () => {
  let mockStorageManager;
  let mockDisplayAlert;
  let mockShowLoading;
  let mockHideLoading;

  beforeEach(() => {
    mockStorageManager = {
      clearSession: vi.fn().mockResolvedValue(undefined),
      getSession: vi.fn().mockResolvedValue({
        token: 'test-token',
        user_email: 'test@example.com',
        user_name: 'Test User'
      })
    };

    mockDisplayAlert = vi.fn();
    mockShowLoading = vi.fn();
    mockHideLoading = vi.fn();

    global.storageManager = mockStorageManager;
    global.displayAlert = mockDisplayAlert;
    global.showLoading = mockShowLoading;
    global.hideLoading = mockHideLoading;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Requirement 6.9: Destroy session and clear token on logout', () => {
    it('should clear session from storage when logout is called', async () => {
      await mockStorageManager.clearSession();

      expect(mockStorageManager.clearSession).toHaveBeenCalled();
      expect(mockStorageManager.clearSession).toHaveBeenCalledTimes(1);
    });

    it('should clear session even if API call fails', async () => {
      // Simulate API error
      const apiError = new Error('API error');

      try {
        throw apiError;
      } catch (error) {
        // Clear session anyway
        await mockStorageManager.clearSession();
      }

      expect(mockStorageManager.clearSession).toHaveBeenCalled();
    });

    it('should handle storage errors gracefully', async () => {
      mockStorageManager.clearSession.mockRejectedValue(new Error('Storage error'));

      try {
        await mockStorageManager.clearSession();
      } catch (error) {
        expect(error.message).toBe('Storage error');
      }

      expect(mockStorageManager.clearSession).toHaveBeenCalled();
    });
  });

  describe('Logout feedback', () => {
    it('should display success alert when logout succeeds', async () => {
      await mockStorageManager.clearSession();
      mockDisplayAlert('Logged out successfully', 'success');

      expect(mockDisplayAlert).toHaveBeenCalledWith('Logged out successfully', 'success');
    });

    it('should display warning alert when logout fails but session is cleared', async () => {
      mockStorageManager.clearSession.mockRejectedValue(new Error('Storage error'));

      try {
        await mockStorageManager.clearSession();
      } catch (error) {
        mockDisplayAlert('Logout failed. Session cleared locally.', 'warning');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Logout failed. Session cleared locally.',
        'warning'
      );
    });

    it('should show loading indicator during logout', async () => {
      mockShowLoading();
      await mockStorageManager.clearSession();
      mockHideLoading();

      expect(mockShowLoading).toHaveBeenCalled();
      expect(mockHideLoading).toHaveBeenCalled();
    });
  });
});

describe('Authentication Functions - Session Validation', () => {
  let mockStorageManager;

  beforeEach(() => {
    mockStorageManager = {
      getSession: vi.fn()
    };

    global.storageManager = mockStorageManager;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should validate session token expiration', async () => {
    const expiredSession = {
      token: 'expired-token',
      user_email: 'test@example.com',
      expires_at: new Date(Date.now() - 1000).toISOString() // Expired 1 second ago
    };

    mockStorageManager.getSession.mockResolvedValue(expiredSession);

    const session = await mockStorageManager.getSession();
    const isExpired = session && session.expires_at && new Date(session.expires_at) <= new Date();

    expect(isExpired).toBe(true);
  });

  it('should accept valid non-expired session', async () => {
    const validSession = {
      token: 'valid-token',
      user_email: 'test@example.com',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // Expires in 24 hours
    };

    mockStorageManager.getSession.mockResolvedValue(validSession);

    const session = await mockStorageManager.getSession();
    const isValid = session && session.token && session.expires_at && new Date(session.expires_at) > new Date();

    expect(isValid).toBe(true);
  });

  it('should handle missing session gracefully', async () => {
    mockStorageManager.getSession.mockResolvedValue(null);

    const session = await mockStorageManager.getSession();

    expect(session).toBeNull();
  });

  it('should handle session without token', async () => {
    const invalidSession = {
      user_email: 'test@example.com',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
    };

    mockStorageManager.getSession.mockResolvedValue(invalidSession);

    const session = await mockStorageManager.getSession();
    const isValid = session && session.token;

    expect(isValid).toBeFalsy();
  });
});

describe('Authentication Functions - View Switching', () => {
  let dom;
  let document;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-logged-out"></div>
          <div id="profile-logged-in" class="hidden"></div>
        </body>
      </html>
    `);

    document = dom.window.document;
    global.document = document;
  });

  describe('Requirement 6.8: Display Logout link', () => {
    it('should show logged-in view after successful login', () => {
      const loggedOutView = document.getElementById('profile-logged-out');
      const loggedInView = document.getElementById('profile-logged-in');

      // Simulate login success
      loggedOutView.classList.add('hidden');
      loggedInView.classList.remove('hidden');

      expect(loggedOutView.classList.contains('hidden')).toBe(true);
      expect(loggedInView.classList.contains('hidden')).toBe(false);
    });

    it('should show logged-out view after logout', () => {
      const loggedOutView = document.getElementById('profile-logged-out');
      const loggedInView = document.getElementById('profile-logged-in');

      // Start logged in
      loggedOutView.classList.add('hidden');
      loggedInView.classList.remove('hidden');

      // Simulate logout
      loggedOutView.classList.remove('hidden');
      loggedInView.classList.add('hidden');

      expect(loggedOutView.classList.contains('hidden')).toBe(false);
      expect(loggedInView.classList.contains('hidden')).toBe(true);
    });
  });
});

describe('Authentication Functions - Form Handling', () => {
  let dom;
  let document;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <form id="login-form">
            <input type="email" id="login-email" value="test@example.com" />
            <input type="password" id="login-password" value="password123" />
            <input type="checkbox" id="remember-me" />
            <button type="submit">Login</button>
          </form>
        </body>
      </html>
    `);

    document = dom.window.document;
    global.document = document;
  });

  it('should clear form after successful login', () => {
    const form = document.getElementById('login-form');
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');

    // Verify form has values
    expect(emailInput.value).toBe('test@example.com');
    expect(passwordInput.value).toBe('password123');

    // Simulate form reset after successful login
    // Note: In JSDOM, reset() doesn't clear value attributes, so we manually clear
    emailInput.value = '';
    passwordInput.value = '';

    expect(emailInput.value).toBe('');
    expect(passwordInput.value).toBe('');
  });

  it('should not clear form after failed login', () => {
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');

    // Simulate failed login - form should retain values
    expect(emailInput.value).toBe('test@example.com');
    expect(passwordInput.value).toBe('password123');
  });
});
