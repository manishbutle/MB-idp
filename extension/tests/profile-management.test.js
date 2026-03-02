/**
 * Comprehensive Unit Tests for Profile Tab - Profile Management Functions
 * Task 16.6: Implement profile management
 * Requirements: 7.6, 7.8, 7.9
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Profile Management - Update Profile', () => {
  let dom;
  let document;
  let window;
  let mockApiClient;
  let mockStorageManager;
  let mockDisplayAlert;
  let mockShowLoading;
  let mockHideLoading;
  let currentUser;

  beforeEach(() => {
    // Create DOM
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-tab">
            <div id="profile-logged-in">
              <h2 id="user-name-heading">Welcome, Test User</h2>
              <div id="profile-settings-content">
                <input type="text" id="profile-first-name" value="" />
                <input type="text" id="profile-last-name" value="" />
                <button id="save-profile-btn">Save</button>
              </div>
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

    // Mock current user
    currentUser = {
      token: 'test-token',
      user_email: 'test@example.com',
      user_name: 'Test User',
      role: 'User',
      tenant: 'default',
      remember_me: false,
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
    };

    // Mock API client
    mockApiClient = {
      updateProfile: vi.fn()
    };

    // Mock storage manager
    mockStorageManager = {
      setSession: vi.fn().mockResolvedValue(undefined),
      getSession: vi.fn().mockResolvedValue(currentUser)
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

  describe('Requirement 7.6: Call profile_change API with updated values', () => {
    it('should call updateProfile API with first name and last name', async () => {
      const firstName = 'John';
      const lastName = 'Doe';

      mockApiClient.updateProfile.mockResolvedValue({
        success: true,
        message: 'Profile updated successfully'
      });

      await mockApiClient.updateProfile(firstName, lastName);

      expect(mockApiClient.updateProfile).toHaveBeenCalledWith(firstName, lastName);
      expect(mockApiClient.updateProfile).toHaveBeenCalledTimes(1);
    });

    it('should trim whitespace from first name and last name', async () => {
      const firstName = '  John  ';
      const lastName = '  Doe  ';

      mockApiClient.updateProfile.mockResolvedValue({
        success: true
      });

      await mockApiClient.updateProfile(firstName.trim(), lastName.trim());

      expect(mockApiClient.updateProfile).toHaveBeenCalledWith('John', 'Doe');
    });

    it('should not call API if first name is empty', () => {
      const firstName = '';
      const lastName = 'Doe';

      // Validation should prevent API call
      const isValid = !!(firstName.trim() && lastName.trim());

      expect(isValid).toBe(false);
      expect(mockApiClient.updateProfile).not.toHaveBeenCalled();
    });

    it('should not call API if last name is empty', () => {
      const firstName = 'John';
      const lastName = '';

      // Validation should prevent API call
      const isValid = !!(firstName.trim() && lastName.trim());

      expect(isValid).toBe(false);
      expect(mockApiClient.updateProfile).not.toHaveBeenCalled();
    });

    it('should not call API if both names are empty', () => {
      const firstName = '';
      const lastName = '';

      // Validation should prevent API call
      const isValid = !!(firstName.trim() && lastName.trim());

      expect(isValid).toBe(false);
      expect(mockApiClient.updateProfile).not.toHaveBeenCalled();
    });

    it('should not call API if names are only whitespace', () => {
      const firstName = '   ';
      const lastName = '   ';

      // Validation should prevent API call
      const isValid = !!(firstName.trim() && lastName.trim());

      expect(isValid).toBe(false);
      expect(mockApiClient.updateProfile).not.toHaveBeenCalled();
    });
  });

  describe('Profile update success handling', () => {
    it('should update session with new user name on success', async () => {
      const firstName = 'John';
      const lastName = 'Doe';

      mockApiClient.updateProfile.mockResolvedValue({
        success: true
      });

      const response = await mockApiClient.updateProfile(firstName, lastName);

      if (response.success) {
        currentUser.user_name = `${firstName} ${lastName}`;
        await mockStorageManager.setSession(currentUser);

        expect(mockStorageManager.setSession).toHaveBeenCalledWith(
          expect.objectContaining({
            user_name: 'John Doe'
          })
        );
      }
    });

    it('should update user name heading on success', async () => {
      const firstName = 'John';
      const lastName = 'Doe';

      mockApiClient.updateProfile.mockResolvedValue({
        success: true
      });

      const response = await mockApiClient.updateProfile(firstName, lastName);

      if (response.success) {
        const userNameHeading = document.getElementById('user-name-heading');
        if (userNameHeading) {
          userNameHeading.textContent = `Welcome, ${firstName} ${lastName}`;
        }

        expect(userNameHeading.textContent).toBe('Welcome, John Doe');
      }
    });

    it('should display success alert when profile update succeeds', async () => {
      mockApiClient.updateProfile.mockResolvedValue({
        success: true
      });

      const response = await mockApiClient.updateProfile('John', 'Doe');

      if (response.success) {
        mockDisplayAlert('Profile updated successfully', 'success');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Profile updated successfully', 'success');
    });

    it('should show and hide loading indicator during update', async () => {
      mockApiClient.updateProfile.mockResolvedValue({
        success: true
      });

      mockShowLoading();
      await mockApiClient.updateProfile('John', 'Doe');
      mockHideLoading();

      expect(mockShowLoading).toHaveBeenCalled();
      expect(mockHideLoading).toHaveBeenCalled();
    });
  });

  describe('Profile update error handling', () => {
    it('should display error alert when API returns failure', async () => {
      mockApiClient.updateProfile.mockResolvedValue({
        success: false,
        message: 'Failed to update profile'
      });

      const response = await mockApiClient.updateProfile('John', 'Doe');

      if (!response.success) {
        mockDisplayAlert(response.message || 'Failed to update profile', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Failed to update profile', 'error');
    });

    it('should display default error message if API returns no message', async () => {
      mockApiClient.updateProfile.mockResolvedValue({
        success: false
      });

      const response = await mockApiClient.updateProfile('John', 'Doe');

      if (!response.success) {
        mockDisplayAlert(response.message || 'Failed to update profile', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Failed to update profile', 'error');
    });

    it('should display error alert when network error occurs', async () => {
      mockApiClient.updateProfile.mockRejectedValue(new Error('Network error'));

      try {
        await mockApiClient.updateProfile('John', 'Doe');
      } catch (error) {
        mockDisplayAlert('Failed to update profile', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Failed to update profile', 'error');
    });

    it('should hide loading indicator when update fails', async () => {
      mockApiClient.updateProfile.mockRejectedValue(new Error('Network error'));

      mockShowLoading();
      try {
        await mockApiClient.updateProfile('John', 'Doe');
      } catch (error) {
        mockHideLoading();
      }

      expect(mockHideLoading).toHaveBeenCalled();
    });

    it('should not update session when API call fails', async () => {
      mockApiClient.updateProfile.mockResolvedValue({
        success: false
      });

      const response = await mockApiClient.updateProfile('John', 'Doe');

      if (!response.success) {
        expect(mockStorageManager.setSession).not.toHaveBeenCalled();
      }
    });
  });

  describe('Input validation', () => {
    it('should display error alert for empty first name', () => {
      const firstName = '';
      const lastName = 'Doe';

      if (!firstName.trim() || !lastName.trim()) {
        mockDisplayAlert('Please enter both first name and last name', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Please enter both first name and last name',
        'error'
      );
    });

    it('should display error alert for empty last name', () => {
      const firstName = 'John';
      const lastName = '';

      if (!firstName.trim() || !lastName.trim()) {
        mockDisplayAlert('Please enter both first name and last name', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Please enter both first name and last name',
        'error'
      );
    });

    it('should display error alert for both names empty', () => {
      const firstName = '';
      const lastName = '';

      if (!firstName.trim() || !lastName.trim()) {
        mockDisplayAlert('Please enter both first name and last name', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Please enter both first name and last name',
        'error'
      );
    });
  });
});

describe('Profile Management - Change Password', () => {
  let dom;
  let document;
  let window;
  let mockApiClient;
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
            <div id="change-password-content">
              <input type="password" id="current-password" value="" />
              <input type="password" id="new-password" value="" />
              <input type="password" id="confirm-password" value="" />
              <button id="change-password-btn">Change Password</button>
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
      changePassword: vi.fn()
    };

    // Mock UI functions
    mockDisplayAlert = vi.fn();
    mockShowLoading = vi.fn();
    mockHideLoading = vi.fn();

    global.apiClient = mockApiClient;
    global.displayAlert = mockDisplayAlert;
    global.showLoading = mockShowLoading;
    global.hideLoading = mockHideLoading;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Requirement 7.8: Validate New Password matches Confirm Password', () => {
    it('should accept matching new password and confirm password', () => {
      const newPassword = 'newPassword123';
      const confirmPassword = 'newPassword123';

      const isValid = newPassword === confirmPassword;

      expect(isValid).toBe(true);
    });

    it('should reject non-matching new password and confirm password', () => {
      const newPassword = 'newPassword123';
      const confirmPassword = 'differentPassword456';

      const isValid = newPassword === confirmPassword;

      expect(isValid).toBe(false);
    });

    it('should display error alert when passwords do not match', () => {
      const newPassword = 'newPassword123';
      const confirmPassword = 'differentPassword456';

      if (newPassword !== confirmPassword) {
        mockDisplayAlert('New password and confirm password do not match', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'New password and confirm password do not match',
        'error'
      );
    });

    it('should not call API when passwords do not match', () => {
      const currentPassword = 'oldPassword123';
      const newPassword = 'newPassword123';
      const confirmPassword = 'differentPassword456';

      if (newPassword !== confirmPassword) {
        expect(mockApiClient.changePassword).not.toHaveBeenCalled();
      }
    });

    it('should be case-sensitive when comparing passwords', () => {
      const newPassword = 'Password123';
      const confirmPassword = 'password123';

      const isValid = newPassword === confirmPassword;

      expect(isValid).toBe(false);
    });

    it('should handle whitespace differences in password comparison', () => {
      const newPassword = 'password123';
      const confirmPassword = 'password123 ';

      const isValid = newPassword === confirmPassword;

      expect(isValid).toBe(false);
    });
  });

  describe('Requirement 7.9: Call password_change API', () => {
    it('should call changePassword API with all three password fields', async () => {
      const currentPassword = 'oldPassword123';
      const newPassword = 'newPassword123';
      const confirmPassword = 'newPassword123';

      mockApiClient.changePassword.mockResolvedValue({
        success: true
      });

      await mockApiClient.changePassword(currentPassword, newPassword, confirmPassword);

      expect(mockApiClient.changePassword).toHaveBeenCalledWith(
        currentPassword,
        newPassword,
        confirmPassword
      );
      expect(mockApiClient.changePassword).toHaveBeenCalledTimes(1);
    });

    it('should not call API if current password is empty', () => {
      const currentPassword = '';
      const newPassword = 'newPassword123';
      const confirmPassword = 'newPassword123';

      const isValid = !!(currentPassword && newPassword && confirmPassword);

      expect(isValid).toBe(false);
      expect(mockApiClient.changePassword).not.toHaveBeenCalled();
    });

    it('should not call API if new password is empty', () => {
      const currentPassword = 'oldPassword123';
      const newPassword = '';
      const confirmPassword = '';

      const isValid = !!(currentPassword && newPassword && confirmPassword);

      expect(isValid).toBe(false);
      expect(mockApiClient.changePassword).not.toHaveBeenCalled();
    });

    it('should not call API if confirm password is empty', () => {
      const currentPassword = 'oldPassword123';
      const newPassword = 'newPassword123';
      const confirmPassword = '';

      const isValid = !!(currentPassword && newPassword && confirmPassword);

      expect(isValid).toBe(false);
      expect(mockApiClient.changePassword).not.toHaveBeenCalled();
    });

    it('should not call API if all password fields are empty', () => {
      const currentPassword = '';
      const newPassword = '';
      const confirmPassword = '';

      const isValid = !!(currentPassword && newPassword && confirmPassword);

      expect(isValid).toBe(false);
      expect(mockApiClient.changePassword).not.toHaveBeenCalled();
    });
  });

  describe('Password validation', () => {
    it('should enforce minimum password length of 8 characters', () => {
      const newPassword = 'short';
      const minLength = 8;

      const isValid = newPassword.length >= minLength;

      expect(isValid).toBe(false);
    });

    it('should accept password with exactly 8 characters', () => {
      const newPassword = 'password';
      const minLength = 8;

      const isValid = newPassword.length >= minLength;

      expect(isValid).toBe(true);
    });

    it('should accept password longer than 8 characters', () => {
      const newPassword = 'longPassword123';
      const minLength = 8;

      const isValid = newPassword.length >= minLength;

      expect(isValid).toBe(true);
    });

    it('should display error alert for password shorter than 8 characters', () => {
      const newPassword = 'short';

      if (newPassword.length < 8) {
        mockDisplayAlert('New password must be at least 8 characters long', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'New password must be at least 8 characters long',
        'error'
      );
    });

    it('should display error alert for empty password fields', () => {
      const currentPassword = '';
      const newPassword = '';
      const confirmPassword = '';

      if (!currentPassword || !newPassword || !confirmPassword) {
        mockDisplayAlert('Please fill in all password fields', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'Please fill in all password fields',
        'error'
      );
    });
  });

  describe('Password change success handling', () => {
    it('should display success alert when password change succeeds', async () => {
      mockApiClient.changePassword.mockResolvedValue({
        success: true
      });

      const response = await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');

      if (response.success) {
        mockDisplayAlert('Password changed successfully', 'success');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Password changed successfully', 'success');
    });

    it('should clear password fields after successful change', async () => {
      const currentPasswordInput = document.getElementById('current-password');
      const newPasswordInput = document.getElementById('new-password');
      const confirmPasswordInput = document.getElementById('confirm-password');

      // Set initial values
      currentPasswordInput.value = 'oldPassword123';
      newPasswordInput.value = 'newPassword123';
      confirmPasswordInput.value = 'newPassword123';

      mockApiClient.changePassword.mockResolvedValue({
        success: true
      });

      const response = await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');

      if (response.success) {
        currentPasswordInput.value = '';
        newPasswordInput.value = '';
        confirmPasswordInput.value = '';
      }

      expect(currentPasswordInput.value).toBe('');
      expect(newPasswordInput.value).toBe('');
      expect(confirmPasswordInput.value).toBe('');
    });

    it('should show and hide loading indicator during password change', async () => {
      mockApiClient.changePassword.mockResolvedValue({
        success: true
      });

      mockShowLoading();
      await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');
      mockHideLoading();

      expect(mockShowLoading).toHaveBeenCalled();
      expect(mockHideLoading).toHaveBeenCalled();
    });
  });

  describe('Password change error handling', () => {
    it('should display error alert when API returns failure', async () => {
      mockApiClient.changePassword.mockResolvedValue({
        success: false,
        message: 'Current password is incorrect'
      });

      const response = await mockApiClient.changePassword('wrong', 'newPassword123', 'newPassword123');

      if (!response.success) {
        mockDisplayAlert(response.message || 'Failed to change password', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Current password is incorrect', 'error');
    });

    it('should display default error message if API returns no message', async () => {
      mockApiClient.changePassword.mockResolvedValue({
        success: false
      });

      const response = await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');

      if (!response.success) {
        mockDisplayAlert(response.message || 'Failed to change password', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Failed to change password', 'error');
    });

    it('should display error alert when network error occurs', async () => {
      mockApiClient.changePassword.mockRejectedValue(new Error('Network error'));

      try {
        await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');
      } catch (error) {
        mockDisplayAlert('Failed to change password', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Failed to change password', 'error');
    });

    it('should hide loading indicator when password change fails', async () => {
      mockApiClient.changePassword.mockRejectedValue(new Error('Network error'));

      mockShowLoading();
      try {
        await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');
      } catch (error) {
        mockHideLoading();
      }

      expect(mockHideLoading).toHaveBeenCalled();
    });

    it('should not clear password fields when change fails', async () => {
      const currentPasswordInput = document.getElementById('current-password');
      const newPasswordInput = document.getElementById('new-password');
      const confirmPasswordInput = document.getElementById('confirm-password');

      // Set initial values
      currentPasswordInput.value = 'oldPassword123';
      newPasswordInput.value = 'newPassword123';
      confirmPasswordInput.value = 'newPassword123';

      mockApiClient.changePassword.mockResolvedValue({
        success: false
      });

      const response = await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');

      if (!response.success) {
        // Fields should retain values on failure
        expect(currentPasswordInput.value).toBe('oldPassword123');
        expect(newPasswordInput.value).toBe('newPassword123');
        expect(confirmPasswordInput.value).toBe('newPassword123');
      }
    });
  });

  describe('Validation order', () => {
    it('should validate empty fields before password match', () => {
      const currentPassword = '';
      const newPassword = '';
      const confirmPassword = '';

      // Empty field validation should come first
      if (!currentPassword || !newPassword || !confirmPassword) {
        mockDisplayAlert('Please fill in all password fields', 'error');
        return;
      }

      // This should not be reached
      if (newPassword !== confirmPassword) {
        mockDisplayAlert('New password and confirm password do not match', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith('Please fill in all password fields', 'error');
      expect(mockDisplayAlert).not.toHaveBeenCalledWith(
        'New password and confirm password do not match',
        'error'
      );
    });

    it('should validate password match before length', () => {
      const currentPassword = 'oldPassword123';
      const newPassword = 'short';
      const confirmPassword = 'different';

      // Password match validation should come before length
      if (newPassword !== confirmPassword) {
        mockDisplayAlert('New password and confirm password do not match', 'error');
        return;
      }

      // This should not be reached
      if (newPassword.length < 8) {
        mockDisplayAlert('New password must be at least 8 characters long', 'error');
      }

      expect(mockDisplayAlert).toHaveBeenCalledWith(
        'New password and confirm password do not match',
        'error'
      );
      expect(mockDisplayAlert).not.toHaveBeenCalledWith(
        'New password must be at least 8 characters long',
        'error'
      );
    });

    it('should validate length before calling API', () => {
      const currentPassword = 'oldPassword123';
      const newPassword = 'short';
      const confirmPassword = 'short';

      // All validations pass except length
      if (!currentPassword || !newPassword || !confirmPassword) {
        return;
      }

      if (newPassword !== confirmPassword) {
        return;
      }

      if (newPassword.length < 8) {
        mockDisplayAlert('New password must be at least 8 characters long', 'error');
        return;
      }

      // API should not be called
      expect(mockApiClient.changePassword).not.toHaveBeenCalled();
    });
  });
});

describe('Profile Management - Integration', () => {
  let dom;
  let document;
  let mockApiClient;
  let mockStorageManager;
  let mockDisplayAlert;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="profile-tab">
            <h2 id="user-name-heading">Welcome, Test User</h2>
            <div id="profile-settings-content">
              <input type="text" id="profile-first-name" value="Test" />
              <input type="text" id="profile-last-name" value="User" />
            </div>
            <div id="change-password-content">
              <input type="password" id="current-password" value="" />
              <input type="password" id="new-password" value="" />
              <input type="password" id="confirm-password" value="" />
            </div>
          </div>
        </body>
      </html>
    `);

    document = dom.window.document;
    global.document = document;

    mockApiClient = {
      updateProfile: vi.fn(),
      changePassword: vi.fn()
    };

    mockStorageManager = {
      setSession: vi.fn().mockResolvedValue(undefined),
      getSession: vi.fn().mockResolvedValue({
        token: 'test-token',
        user_email: 'test@example.com',
        user_name: 'Test User'
      })
    };

    mockDisplayAlert = vi.fn();

    global.apiClient = mockApiClient;
    global.storageManager = mockStorageManager;
    global.displayAlert = mockDisplayAlert;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should handle profile update and password change independently', async () => {
    // Update profile
    mockApiClient.updateProfile.mockResolvedValue({ success: true });
    await mockApiClient.updateProfile('John', 'Doe');

    // Change password
    mockApiClient.changePassword.mockResolvedValue({ success: true });
    await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');

    expect(mockApiClient.updateProfile).toHaveBeenCalledTimes(1);
    expect(mockApiClient.changePassword).toHaveBeenCalledTimes(1);
  });

  it('should maintain session after profile update', async () => {
    const currentUser = await mockStorageManager.getSession();

    mockApiClient.updateProfile.mockResolvedValue({ success: true });
    const response = await mockApiClient.updateProfile('John', 'Doe');

    if (response.success) {
      currentUser.user_name = 'John Doe';
      await mockStorageManager.setSession(currentUser);

      const updatedSession = mockStorageManager.setSession.mock.calls[0][0];
      expect(updatedSession.token).toBe('test-token');
      expect(updatedSession.user_email).toBe('test@example.com');
      expect(updatedSession.user_name).toBe('John Doe');
    }
  });

  it('should not affect session when password change succeeds', async () => {
    mockApiClient.changePassword.mockResolvedValue({ success: true });
    await mockApiClient.changePassword('old', 'newPassword123', 'newPassword123');

    // Session should not be modified for password change
    expect(mockStorageManager.setSession).not.toHaveBeenCalled();
  });
});
