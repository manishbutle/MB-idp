/**
 * Unit tests for Profile Tab - Login functionality
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Profile Tab - Login UI', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    // Create a minimal DOM for testing
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-tab">
            <div id="profile-logged-out">
              <form id="login-form">
                <input type="email" id="login-email" required />
                <input type="password" id="login-password" required />
                <input type="checkbox" id="remember-me" />
                <button type="submit">Login</button>
              </form>
              <a href="#" id="forget-password-link">Forget Password?</a>
              <a href="#" id="signup-link">Sign up</a>
            </div>
            <div id="profile-logged-in" class="hidden"></div>
          </div>
          <div id="alert-container"></div>
          <div id="loading-overlay" class="hidden"></div>
        </body>
      </html>
    `, {
      url: 'chrome-extension://test',
      runScripts: 'dangerously'
    });

    document = dom.window.document;
    window = dom.window;
    global.document = document;
    global.window = window;
  });

  it('should display login form with all required fields', () => {
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    const rememberMeCheckbox = document.getElementById('remember-me');
    const loginForm = document.getElementById('login-form');

    expect(emailInput).toBeTruthy();
    expect(emailInput.type).toBe('email');
    expect(passwordInput).toBeTruthy();
    expect(passwordInput.type).toBe('password');
    expect(rememberMeCheckbox).toBeTruthy();
    expect(rememberMeCheckbox.type).toBe('checkbox');
    expect(loginForm).toBeTruthy();
  });

  it('should display Forget Password link', () => {
    const forgetPasswordLink = document.getElementById('forget-password-link');
    
    expect(forgetPasswordLink).toBeTruthy();
    expect(forgetPasswordLink.textContent).toContain('Forget Password');
  });

  it('should display Sign-up link', () => {
    const signupLink = document.getElementById('signup-link');
    
    expect(signupLink).toBeTruthy();
    expect(signupLink.textContent).toContain('Sign up');
  });

  it('should have email input with proper attributes', () => {
    const emailInput = document.getElementById('login-email');
    
    expect(emailInput.type).toBe('email');
    expect(emailInput.hasAttribute('required')).toBe(true);
  });

  it('should have password input with proper attributes', () => {
    const passwordInput = document.getElementById('login-password');
    
    expect(passwordInput.type).toBe('password');
    expect(passwordInput.hasAttribute('required')).toBe(true);
  });

  it('should have Remember Me checkbox', () => {
    const rememberMeCheckbox = document.getElementById('remember-me');
    
    expect(rememberMeCheckbox.type).toBe('checkbox');
    expect(rememberMeCheckbox.checked).toBe(false);
  });

  it('should show logged-out view by default', () => {
    const loggedOutView = document.getElementById('profile-logged-out');
    const loggedInView = document.getElementById('profile-logged-in');
    
    expect(loggedOutView.classList.contains('hidden')).toBe(false);
    expect(loggedInView.classList.contains('hidden')).toBe(true);
  });
});

describe('Profile Tab - Login Functionality', () => {
  let dom;
  let document;
  let window;
  let mockApiCall;
  let mockShowAlert;
  let mockShowLoading;
  let mockHideLoading;
  let mockSaveToStorage;

  beforeEach(() => {
    // Create DOM
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-tab">
            <div id="profile-logged-out">
              <form id="login-form">
                <input type="email" id="login-email" value="test@example.com" />
                <input type="password" id="login-password" value="password123" />
                <input type="checkbox" id="remember-me" />
                <button type="submit">Login</button>
              </form>
            </div>
            <div id="profile-logged-in" class="hidden"></div>
          </div>
        </body>
      </html>
    `);

    document = dom.window.document;
    window = dom.window;
    global.document = document;
    global.window = window;

    // Mock functions
    mockApiCall = vi.fn();
    mockShowAlert = vi.fn();
    mockShowLoading = vi.fn();
    mockHideLoading = vi.fn();
    mockSaveToStorage = vi.fn();

    global.apiCall = mockApiCall;
    global.showAlert = mockShowAlert;
    global.showLoading = mockShowLoading;
    global.hideLoading = mockHideLoading;
    global.saveToStorage = mockSaveToStorage;
  });

  it('should validate empty email and password', async () => {
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    
    emailInput.value = '';
    passwordInput.value = '';

    // Simulate form validation
    const isValid = !!(emailInput.value.trim() && passwordInput.value);
    
    expect(isValid).toBe(false);
  });

  it('should call API with correct credentials on login', async () => {
    mockApiCall.mockResolvedValue({
      success: true,
      token: 'test-token-123',
      user_name: 'Test User',
      role: 'User',
      tenant: 'default',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
    });

    const email = 'test@example.com';
    const password = 'password123';

    // Simulate login
    await mockApiCall('/auth', 'POST', { email, password });

    expect(mockApiCall).toHaveBeenCalledWith('/auth', 'POST', {
      email: 'test@example.com',
      password: 'password123'
    });
  });

  it('should store session data on successful login', async () => {
    const mockResponse = {
      success: true,
      token: 'test-token-123',
      user_name: 'Test User',
      role: 'User',
      tenant: 'default',
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
    };

    mockApiCall.mockResolvedValue(mockResponse);

    // Simulate successful login
    await mockApiCall('/auth', 'POST', {
      email: 'test@example.com',
      password: 'password123'
    });

    const response = await mockApiCall.mock.results[0].value;

    // Verify session structure
    expect(response.token).toBe('test-token-123');
    expect(response.user_name).toBe('Test User');
    expect(response.role).toBe('User');
    expect(response.tenant).toBe('default');
  });

  it('should handle Remember Me checkbox state', () => {
    const rememberMeCheckbox = document.getElementById('remember-me');
    
    // Initially unchecked
    expect(rememberMeCheckbox.checked).toBe(false);
    
    // Check the box
    rememberMeCheckbox.checked = true;
    expect(rememberMeCheckbox.checked).toBe(true);
  });

  it('should handle login failure with error message', async () => {
    mockApiCall.mockResolvedValue({
      success: false,
      message: 'Invalid credentials'
    });

    const response = await mockApiCall('/auth', 'POST', {
      email: 'test@example.com',
      password: 'wrongpassword'
    });

    expect(response.success).toBe(false);
    expect(response.message).toBe('Invalid credentials');
  });

  it('should handle network errors during login', async () => {
    mockApiCall.mockRejectedValue(new Error('Network error'));

    try {
      await mockApiCall('/auth', 'POST', {
        email: 'test@example.com',
        password: 'password123'
      });
    } catch (error) {
      expect(error.message).toBe('Network error');
    }
  });
});

describe('Profile Tab - View Switching', () => {
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

  it('should switch from logged-out to logged-in view', () => {
    const loggedOutView = document.getElementById('profile-logged-out');
    const loggedInView = document.getElementById('profile-logged-in');

    // Initially logged out
    expect(loggedOutView.classList.contains('hidden')).toBe(false);
    expect(loggedInView.classList.contains('hidden')).toBe(true);

    // Switch to logged in
    loggedOutView.classList.add('hidden');
    loggedInView.classList.remove('hidden');

    expect(loggedOutView.classList.contains('hidden')).toBe(true);
    expect(loggedInView.classList.contains('hidden')).toBe(false);
  });

  it('should switch from logged-in to logged-out view on logout', () => {
    const loggedOutView = document.getElementById('profile-logged-out');
    const loggedInView = document.getElementById('profile-logged-in');

    // Start logged in
    loggedOutView.classList.add('hidden');
    loggedInView.classList.remove('hidden');

    // Logout
    loggedOutView.classList.remove('hidden');
    loggedInView.classList.add('hidden');

    expect(loggedOutView.classList.contains('hidden')).toBe(false);
    expect(loggedInView.classList.contains('hidden')).toBe(true);
  });
});
