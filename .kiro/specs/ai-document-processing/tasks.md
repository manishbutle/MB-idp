# Implementation Plan: AI Document Processing Browser Extension

## Overview

This implementation plan breaks down the AI Document Processing browser extension into discrete coding tasks. The system consists of a Chrome/Edge browser extension (JavaScript) frontend and AWS Lambda (Python) backend services. The implementation follows an incremental approach: infrastructure setup, backend services, frontend components, integration, and testing.

## Tasks

- [x] 1. Set up project structure and infrastructure
  - Create browser extension directory structure (manifest.json, popup.html, background scripts, content scripts)
  - Create Lambda functions directory structure (separate folders for auth, process, data, admin, integration)
  - Set up Python virtual environment and install dependencies (boto3, aws-lambda-powertools)
  - Set up JavaScript dependencies (Tailwind CSS, fast-check, PapaParse, SheetJS, smtp.js)
  - Create DynamoDB table definitions (CloudFormation or Terraform)
  - Set up API Gateway configuration (REST API, CORS, routes)
  - Configure IAM roles and policies for Lambda functions
  - _Requirements: 10.1, 10.2, 10.3, 12.1, 17.1, 17.2, 17.3_

- [x] 2. Implement DynamoDB data layer
  - [x] 2.1 Create DynamoDB table schemas and initialization scripts
    - Define table schemas for all 9 tables (idp_users, idp_roles, idp_transactions, idp_history, idp_rates, idp_settings, idp_metadata, idp_datapoints, idp_document_type)
    - Create GSI definitions for query patterns
    - Write initialization script to create tables
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9_

  - [x] 2.2 Write property test for tenant data isolation
    - **Property 14: Tenant Data Isolation**
    - **Validates: Requirements 23.2, 23.3, 23.4, 23.5, 23.6, 23.7**

  - [x] 2.3 Create seed data script for development and testing
    - Generate sample users, roles, document types, prompts, and rates
    - Include multi-tenant test data
    - _Requirements: 12.1, 23.1_


- [x] 3. Implement Auth Lambda function
  - [x] 3.1 Implement user authentication handler
    - Write handle_auth function to validate credentials
    - Implement password hash verification
    - Integrate with Cognito for session token generation
    - Query idp_users table for user lookup
    - _Requirements: 6.2, 6.3, 6.4, 13.1, 13.3, 13.8_

  - [x] 3.2 Implement session management
    - Write create_session function
    - Write destroy_previous_sessions function to enforce single active session
    - Store session records in DynamoDB or Cognito
    - _Requirements: 6.4, 6.5_

  - [x] 3.3 Write property test for single active session per user
    - **Property 6: Single Active Session Per User**
    - **Validates: Requirements 6.4, 6.5**

  - [x] 3.4 Implement password reset flow
    - Write handle_forget_password function to send reset email
    - Write handle_reset_password function to update password
    - Generate secure reset tokens
    - Integrate with SES for email sending
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 3.5 Implement user registration
    - Write handle_sign_up function
    - Validate password confirmation
    - Hash password before storage
    - Create user record in idp_users table
    - _Requirements: 8.6, 8.7, 8.8, 8.9, 8.10, 13.1_

  - [x] 3.6 Write property test for password hash irreversibility
    - **Property 8: Password Hash Irreversibility**
    - **Validates: Requirements 13.1**

  - [x] 3.7 Write unit tests for Auth Lambda
    - Test invalid credentials (401 response)
    - Test duplicate email registration (409 response)
    - Test password reset with invalid token
    - Test session token expiration
    - _Requirements: 6.7, 14.1, 14.7_

- [x] 4. Implement Process Document Lambda function
  - [x] 4.1 Implement Textract integration
    - Write digitize_document function to call Textract API
    - Parse Textract response to extract text and page count
    - Implement retry logic with exponential backoff
    - Handle Textract errors and timeouts
    - _Requirements: 11.1, 11.2, 15.1_

  - [x] 4.2 Implement Bedrock classification
    - Write classify_document function to call Bedrock Agent
    - Parse classification response
    - Query idp_document_type table for document configuration
    - Implement retry logic with exponential backoff
    - _Requirements: 11.3, 11.4_

  - [x] 4.3 Write property test for document type classification consistency
    - **Property 25: Document Type Classification Consistency**
    - **Validates: Requirements 11.3, 11.4**

  - [x] 4.4 Implement Bedrock datapoint extraction
    - Write extract_datapoints function to call Bedrock Agent with prompt
    - Query idp_datapoints table for extraction prompt
    - Parse extraction response into field-value pairs
    - Handle missing or failed datapoint extractions
    - _Requirements: 11.5, 11.6, 11.7_

  - [x] 4.5 Write property test for datapoint extraction completeness
    - **Property 26: Datapoint Extraction Completeness**
    - **Validates: Requirements 11.6, 11.7**

  - [x] 4.6 Implement credit calculation and deduction
    - Write calculate_credit_cost function using idp_rates table
    - Write deduct_credit function to update balance
    - Validate sufficient balance before processing
    - _Requirements: 22.1, 22.2, 22.3_

  - [x] 4.7 Write property test for credit balance calculation
    - **Property 11: Credit Balance Calculation**
    - **Validates: Requirements 22.2, 22.4, 22.5, 22.6**

  - [x] 4.8 Write property test for insufficient balance rejection
    - **Property 12: Insufficient Balance Rejection**
    - **Validates: Requirements 22.3**

  - [x] 4.9 Write property test for credit cost calculation
    - **Property 13: Credit Cost Calculation**
    - **Validates: Requirements 22.1**

  - [x] 4.10 Implement metadata and history storage
    - Write store_metadata function for idp_metadata table
    - Write store_history function for idp_history table
    - Write store_transaction function for idp_transactions table
    - Generate Processing_ID as UUID
    - Capture all required metadata fields
    - _Requirements: 1.7, 1.8, 1.9, 1.10, 1.11, 11.8, 12.3, 12.4, 12.5_

  - [x] 4.11 Write property test for UUID uniqueness
    - **Property 2: UUID Uniqueness**
    - **Validates: Requirements 1.7**

  - [x] 4.12 Write property test for metadata capture completeness
    - **Property 27: Metadata Capture Completeness**
    - **Validates: Requirements 1.8**

  - [x] 4.13 Implement main processing orchestrator
    - Write handle_process_document function to coordinate pipeline
    - Implement transaction rollback on failure
    - Add CloudWatch logging for all stages
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 10.5, 21.1, 21.2, 21.3, 21.5, 21.6_

  - [x] 4.14 Write property test for document processing pipeline completeness
    - **Property 1: Document Processing Pipeline Completeness**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11**

  - [x] 4.15 Write unit tests for Process Lambda
    - Test Textract failure and retry logic
    - Test Bedrock failure and retry logic
    - Test insufficient balance scenario
    - Test transaction rollback on failure
    - Test document type not found (default prompt usage)
    - _Requirements: 14.4, 14.5, 22.3_

- [x] 5. Checkpoint - Ensure backend processing tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 6. Implement Data Lambda function
  - [x] 6.1 Implement datapoints management handlers
    - Write handle_datapoints function to fetch prompts by tenant
    - Write handle_reset_prompts function to reload prompts
    - Apply tenant filtering to all queries
    - _Requirements: 4.1, 4.7, 23.2, 23.3, 23.5_

  - [x] 6.2 Implement history and transaction handlers
    - Write handle_history function with pagination
    - Write handle_mytransactions function with pagination
    - Apply tenant filtering to queries
    - _Requirements: 7.10, 7.11, 15.6, 23.2, 23.6_

  - [x] 6.3 Implement user statistics handlers
    - Write handle_total_document_processed function
    - Write handle_available_balance function to sum transactions
    - _Requirements: 7.3, 7.4, 22.6, 22.7_

  - [x] 6.4 Implement profile management handlers
    - Write handle_profile_change function
    - Write handle_password_change function with validation
    - Write handle_top_up function for credit top-up
    - _Requirements: 7.6, 7.9, 7.13_

  - [x] 6.5 Write property test for transaction history completeness
    - **Property 24: Transaction History Completeness**
    - **Validates: Requirements 22.4, 22.5, 22.8**

  - [x] 6.6 Write unit tests for Data Lambda
    - Test pagination with various page sizes
    - Test balance calculation with mixed transactions
    - Test profile update validation
    - Test password change validation
    - _Requirements: 7.8, 14.7, 14.8_

- [x] 7. Implement Admin Lambda function
  - [x] 7.1 Implement admin credit management
    - Write handle_add_credit function
    - Write validate_system_user function to check role
    - Create admin transaction records with metadata
    - _Requirements: 9.3, 9.4, 9.5, 9.6, 22.8_

  - [x] 7.2 Write property test for role-based access control
    - **Property 10: Role-Based Access Control**
    - **Validates: Requirements 9.1, 9.2, 9.5, 13.6, 13.7**

  - [x] 7.3 Write unit tests for Admin Lambda
    - Test non-System User rejection (403 response)
    - Test invalid credit amount (400 response)
    - Test target user not found (404 response)
    - _Requirements: 9.5, 9.7, 9.8_

- [x] 8. Implement Integration Lambda function
  - [x] 8.1 Implement FTP upload handler
    - Write handle_ftp function to upload files
    - Retrieve FTP credentials from Secrets Manager
    - Handle remote directory configuration
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.7_

  - [x] 8.2 Write property test for FTP upload path correctness
    - **Property 23: FTP Upload Path Correctness**
    - **Validates: Requirements 19.3, 19.4**

  - [x] 8.3 Implement email sending handler
    - Write handle_send_email function using SES
    - Support multiple attachment formats
    - _Requirements: 18.1, 18.3, 18.4, 18.5, 18.6, 18.7_

  - [x] 8.4 Write property test for email attachment format compliance
    - **Property 22: Email Attachment Format Compliance**
    - **Validates: Requirements 18.3, 18.4, 18.5, 18.6, 18.7**

  - [x] 8.5 Write unit tests for Integration Lambda
    - Test FTP connection failure handling
    - Test email sending failure handling
    - Test Secrets Manager credential retrieval
    - _Requirements: 19.5, 19.6, 18.8, 18.9_

- [x] 9. Implement API Gateway routing and validation
  - [x] 9.1 Configure API Gateway endpoints
    - Define all 16 REST API endpoints
    - Configure request/response models
    - Set up CORS for Chrome/Edge extension origins
    - Configure rate limiting (100 req/min per user, 1000 req/min per tenant)
    - _Requirements: 10.1, 10.2, 10.6_

  - [x] 9.2 Implement authentication middleware
    - Create Cognito authorizer for API Gateway
    - Validate session tokens on authenticated endpoints
    - _Requirements: 10.7, 13.3_

  - [x] 9.3 Write property test for API request routing
    - **Property 16: API Request Routing**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

  - [~] 9.4 Write property test for session token validity
    - **Property 7: Session Token Validity**
    - **Validates: Requirements 6.3, 6.6, 10.7, 13.3**

  - [~] 9.5 Write unit tests for API Gateway
    - Test CORS headers on OPTIONS requests
    - Test rate limiting enforcement
    - Test invalid token rejection (401 response)
    - Test request validation (400 response for invalid format)
    - _Requirements: 10.6, 10.7, 14.6, 14.7_

- [x] 10. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 11. Implement browser extension manifest and core structure
  - [x] 11.1 Create manifest.json for Chrome/Edge compatibility
    - Define extension metadata (name, version, description)
    - Declare required permissions (storage, tabs, downloads, clipboardWrite)
    - Configure content security policy
    - Define popup HTML and background scripts
    - _Requirements: 17.1, 17.2, 17.3, 17.7_

  - [x] 11.2 Create popup HTML structure with 5 tabs
    - Create popup.html with tab navigation (Dashboard, Prompts/Datapoints, Settings, Profile, Admin)
    - Apply Tailwind CSS for styling
    - Implement black and white theme for headers/banners
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

  - [x] 11.3 Implement Local Storage utility module
    - Write functions for storing/retrieving data from Chrome storage API
    - Implement encryption/decryption for sensitive credentials
    - _Requirements: 13.2, 17.4_

  - [~] 11.4 Write property test for credential encryption
    - **Property 9: Credential Encryption**
    - **Validates: Requirements 5.3, 13.2**

  - [~] 11.5 Write property test for browser API usage correctness
    - **Property 28: Browser API Usage Correctness**
    - **Validates: Requirements 17.3, 17.4, 17.5, 17.6**

- [x] 12. Implement Dashboard Tab component
  - [x] 12.1 Create Dashboard UI layout
    - Implement "Select Prompt" dropdown
    - Create RESULT section with editable table (Field Name, Value columns)
    - Create METADATA section with collapsible non-editable table
    - Create ACTION section with 7 circular icon buttons
    - Create HISTORY section with collapsible table and pagination
    - _Requirements: 2.1, 2.3, 2.5, 2.7, 2.8_

  - [x] 12.2 Implement document processing workflow
    - Write processDocument function to send document to API
    - Implement confirmation dialog with Yes/No options
    - Display loading indicator during processing
    - Handle process_document API response
    - _Requirements: 1.1, 1.12, 15.2, 15.3_

  - [~] 12.3 Write property test for confirmation dialog precedence
    - **Property 30: Confirmation Dialog Precedence**
    - **Validates: Requirements 1.12**

  - [x] 12.4 Implement result display and editing
    - Write displayResults function to populate RESULT table
    - Implement inline editing for result values
    - Persist edited values in component state
    - Display identified document type in prompt selection area
    - _Requirements: 2.2, 2.3, 2.4, 2.11_

  - [x] 12.5 Implement metadata display
    - Write displayMetadata function to populate METADATA section
    - Display all required fields (Processing ID, Document Name, Prompt Name, Pages, Creation Date, File Type, File Size, Input Tokens, Output Tokens, LLM KPIs)
    - Implement collapsible functionality
    - _Requirements: 2.5, 2.6_

  - [x] 12.6 Implement history display
    - Write loadHistory function to call history API
    - Display latest 20 records with pagination controls
    - Show columns: Timestamp, Processing ID, Document Name, Pages, Values
    - Call history API on extension open
    - _Requirements: 2.8, 2.9, 2.10_

  - [~] 12.7 Write unit tests for Dashboard component
    - Test confirmation dialog display and user interaction
    - Test result table editing
    - Test metadata collapsible toggle
    - Test history pagination
    - _Requirements: 1.12, 2.11, 2.8, 2.9_

- [x] 13. Implement Action Buttons component
  - [x] 13.1 Implement clipboard copy functionality
    - Write copyToClipboard function using browser clipboard API
    - Copy all RESULT data to clipboard
    - Display success/error alert
    - _Requirements: 3.1, 3.8, 3.9_

  - [x] 13.2 Implement CSV export
    - Write exportToCSV function using PapaParse library
    - Generate CSV file from RESULT data
    - Trigger browser download
    - Display success/error alert
    - _Requirements: 3.2, 3.8, 3.9_

  - [x] 13.3 Implement XLSX export
    - Write exportToXLSX function using SheetJS library
    - Generate XLSX file from RESULT data
    - Trigger browser download
    - Display success/error alert
    - _Requirements: 3.3, 3.8, 3.9_

  - [x] 13.4 Implement JSON export
    - Write exportToJSON function
    - Generate JSON file from RESULT data
    - Trigger browser download
    - Display success/error alert
    - _Requirements: 3.4, 3.8, 3.9_

  - [~] 13.5 Write property test for export format round-trip
    - **Property 3: Export Format Round-Trip**
    - **Validates: Requirements 3.2, 3.3, 3.4**

  - [x] 13.6 Implement FTP export
    - Write exportToFTP function
    - Retrieve FTP configuration from Local_Storage
    - Call FTP API endpoint
    - Display success/error alert
    - _Requirements: 3.5, 3.8, 3.9, 19.1, 19.2_

  - [x] 13.7 Implement API submission
    - Write submitToAPI function
    - Retrieve API configuration from Local_Storage
    - Send data to configured endpoint
    - Display success/error alert
    - _Requirements: 3.6, 3.8, 3.9_

  - [x] 13.8 Implement email sending
    - Write sendEmail function
    - Retrieve email configuration from Local_Storage
    - Support both default server (API call) and SMTP (smtp.js)
    - Attach files in selected formats (CSV, XLSX, JSON)
    - Display success/error alert
    - _Requirements: 3.7, 3.8, 3.9, 18.1, 18.2, 18.3, 18.7, 18.8, 18.9_

  - [~] 13.9 Write property test for user feedback consistency
    - **Property 19: User Feedback Consistency**
    - **Validates: Requirements 3.8, 3.9, 14.1, 14.2, 14.3, 14.8**

  - [~] 13.10 Write unit tests for Action Buttons
    - Test clipboard copy with empty data
    - Test file generation failures
    - Test FTP connection failure handling
    - Test SMTP connection failure handling
    - Test external API timeout handling
    - _Requirements: 3.8, 14.6, 14.7_


- [x] 14. Implement Prompts/Datapoints Tab component
  - [x] 14.1 Create Prompts/Datapoints UI layout
    - Create table with columns: Prompt Name, Description, Action buttons
    - Add "Add New" button
    - Add "Reset" button
    - Add "Export to CSV" button
    - Display Edit and Delete buttons for each prompt
    - _Requirements: 4.3, 4.4, 4.5, 4.8_

  - [x] 14.2 Implement prompt loading and caching
    - Write loadPrompts function to call datapoints API
    - Cache prompts in Local_Storage
    - Load from cache on tab open
    - _Requirements: 4.1, 4.2_

  - [x] 14.3 Implement prompt CRUD operations
    - Write addPrompt function to create new prompt
    - Write editPrompt function to update existing prompt
    - Write deletePrompt function to remove prompt
    - Update Local_Storage for all operations
    - _Requirements: 4.5, 4.6, 4.9, 4.10_

  - [~] 14.4 Write property test for Local Storage consistency
    - **Property 4: Local Storage Consistency**
    - **Validates: Requirements 4.2, 4.6, 4.7, 4.9, 4.10**

  - [x] 14.5 Implement reset and export functionality
    - Write resetPrompts function to call reset_prompts API
    - Write exportPromptsToCSV function
    - Refresh Local_Storage cache after reset
    - _Requirements: 4.7, 4.8_

  - [~] 14.6 Write unit tests for Prompts/Datapoints component
    - Test add prompt form validation
    - Test edit prompt updates
    - Test delete prompt confirmation
    - Test cache invalidation on reset
    - _Requirements: 4.5, 4.6, 4.7, 4.9, 4.10_

- [x] 15. Implement Settings Tab component
  - [x] 15.1 Create Settings UI layout
    - Create FTP section with fields (Host Server, Port, Username, Password, Remote Directory)
    - Create Email section with radio buttons (Use Default Server, Use SMTP Server)
    - Create Email fields (Email To, CC, Subject, attachment format checkboxes)
    - Create SMTP fields (SMTP Server, Port, Username, Password, Email From)
    - Create API section with fields (Method dropdown, Endpoint, Header, Body)
    - Add Test Connection buttons for each section
    - Add Save button
    - _Requirements: 5.2, 5.4, 5.5, 5.6, 5.9, 5.12_

  - [x] 15.2 Implement settings loading and saving
    - Write loadSettings function to retrieve from Local_Storage
    - Write saveSettings function to store with encryption
    - Encrypt passwords before storage
    - Decrypt passwords when loading
    - _Requirements: 5.1, 5.3, 5.11, 13.2_

  - [~] 15.3 Write property test for settings persistence round-trip
    - **Property 5: Settings Persistence Round-Trip**
    - **Validates: Requirements 5.1, 5.3, 5.11**

  - [x] 15.4 Implement connection testing
    - Write testFTPConnection function
    - Write testEmailConnection function (API or SMTP based on mode)
    - Write testAPIConnection function
    - Display success/error alerts for test results
    - _Requirements: 5.7, 5.8, 5.10, 5.13, 5.14_

  - [~] 15.5 Write unit tests for Settings component
    - Test password encryption/decryption
    - Test FTP connection test with invalid credentials
    - Test SMTP connection test with invalid server
    - Test API connection test with unreachable endpoint
    - Test form validation
    - _Requirements: 5.3, 5.13, 5.14, 14.8_

- [~] 16. Implement Profile Tab component
  - [x] 16.1 Create Profile UI layout for logged-out state
    - Create login form (Email, Password, Remember Me checkbox, Login button)
    - Add Forget Password link
    - Add Sign-up link
    - _Requirements: 6.1, 6.11, 6.12_

  - [x] 16.2 Create Profile UI layout for logged-in state
    - Display user's full name in H2/H3 heading
    - Create two cards for "Documents Processed" and "Available Balance"
    - Create Profile Setting collapsible section (First Name, Last Name, Save button)
    - Create Change Password collapsible section (Current Password, New Password, Confirm Password)
    - Create Transaction History collapsible table (Timestamp, Processing ID, Pages, Action, Amount, Remaining Balance)
    - Add Top-up button
    - Add Logout link in top left
    - _Requirements: 7.1, 7.2, 7.5, 7.7, 7.10, 7.12, 6.8_

  - [x] 16.3 Implement authentication functions
    - Write login function to call auth API
    - Store session token in Local_Storage
    - Handle Remember Me checkbox for persistence
    - Write logout function to destroy session and clear token
    - Display error alerts for authentication failures
    - _Requirements: 6.2, 6.3, 6.6, 6.7, 6.8, 6.9, 6.10_

  - [~] 16.4 Write property test for password validation consistency
    - **Property 29: Password Validation Consistency**
    - **Validates: Requirements 7.8, 8.7**

  - [x] 16.5 Implement profile statistics display
    - Write loadProfile function to fetch user data
    - Call total_document_processed API for documents count
    - Call available_balance API for balance amount
    - Update cards with fetched data
    - _Requirements: 7.3, 7.4_

  - [x] 16.6 Implement profile management
    - Write updateProfile function to call profile_change API
    - Write changePassword function with validation
    - Validate New Password matches Confirm Password
    - Display success/error alerts
    - _Requirements: 7.6, 7.8, 7.9_

  - [x] 16.7 Implement transaction history display
    - Write loadTransactions function with pagination
    - Call mytransactions API
    - Display transaction records in table
    - _Requirements: 7.10, 7.11_

  - [x] 16.8 Implement top-up functionality
    - Write topUp function to display form (Amount, Remark)
    - Integrate with payment gateway
    - Call top_up API after successful payment
    - Display success/error alerts
    - _Requirements: 7.12, 7.13_

  - [x] 16.9 Implement password recovery flow
    - Write forgetPassword function to call forget_password API
    - Display email input form
    - Handle reset link navigation
    - Write resetPassword function to call reset_password API
    - _Requirements: 6.11, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 16.10 Implement user registration flow
    - Write signUp function to display registration form
    - Validate Password matches Confirm Password
    - Call sign_up API
    - Display success message and redirect to login
    - _Requirements: 6.12, 8.6, 8.7, 8.8, 8.9, 8.10_

  - [~] 16.11 Write unit tests for Profile component
    - Test login with invalid credentials
    - Test Remember Me persistence across browser restart
    - Test logout clears session token
    - Test password change validation
    - Test registration validation
    - Test top-up form validation
    - _Requirements: 6.7, 6.10, 6.9, 7.8, 8.7, 14.8_

- [~] 17. Implement Admin Tab component
  - [x] 17.1 Create Admin UI layout
    - Create form with Email and Credit Amount fields
    - Add Save button
    - Implement role-based visibility (show only for System_User)
    - _Requirements: 9.1, 9.2_

  - [x] 17.2 Implement admin credit management
    - Write addCredit function to call add_credit API
    - Write validateSystemUserRole function
    - Display success/error alerts
    - _Requirements: 9.3, 9.4, 9.7, 9.8_

  - [~] 17.3 Write unit tests for Admin component
    - Test Admin tab hidden for non-System User
    - Test add credit with invalid email
    - Test add credit with negative amount
    - _Requirements: 9.2, 9.7, 9.8_

- [x] 18. Implement shared utilities and error handling
  - [x] 18.1 Create API client module
    - Write generic API call function with authentication headers
    - Implement timeout handling
    - Implement HTTP error status code handling
    - Parse JSON responses
    - _Requirements: 14.6, 14.7, 15.1_

  - [x] 18.2 Implement alert/notification system
    - Write displayAlert function for success/error/warning messages
    - Implement consistent alert styling
    - Auto-dismiss success alerts after 3 seconds
    - _Requirements: 14.1, 14.2, 14.3, 14.8_

  - [x] 18.3 Implement loading indicator component
    - Create reusable loading spinner
    - Write showLoading and hideLoading functions
    - Ensure UI remains responsive during loading
    - _Requirements: 15.2, 15.3, 15.4_

  - [~] 18.4 Write property test for asynchronous UI responsiveness
    - **Property 20: Asynchronous UI Responsiveness**
    - **Validates: Requirements 15.2, 15.3**

  - [~] 18.5 Write property test for cache consistency
    - **Property 21: Cache Consistency**
    - **Validates: Requirements 4.1, 4.2, 15.7**

  - [~] 18.6 Write unit tests for shared utilities
    - Test API client with network timeout
    - Test API client with 500 error response
    - Test alert display and auto-dismiss
    - Test loading indicator show/hide
    - _Requirements: 14.6, 14.7, 15.1_


- [x] 19. Implement CloudWatch logging and monitoring
  - [x] 19.1 Create logging utility module for Lambda functions
    - Write structured logging functions (log_info, log_error, log_warning)
    - Include standard fields (timestamp, level, function name, request ID, user email, tenant)
    - Implement error logging with stack traces
    - _Requirements: 21.1, 21.2, 21.4, 21.7_

  - [x] 19.2 Add logging to all Lambda functions
    - Log execution start and completion for all functions
    - Log processing operations with Processing_ID and duration
    - Log authentication attempts and results
    - Log Textract and Bedrock operations with metrics
    - _Requirements: 21.1, 21.3, 21.5, 21.6, 21.7_

  - [~] 19.3 Write property test for error logging completeness
    - **Property 17: Error Logging Completeness**
    - **Validates: Requirements 10.5, 14.4, 21.2**

  - [~] 19.4 Write property test for success metrics logging
    - **Property 18: Success Metrics Logging**
    - **Validates: Requirements 14.5, 21.1, 21.3**

  - [x] 19.5 Configure CloudWatch metrics and alarms
    - Create custom metrics for business operations (documents processed, credits used)
    - Set up alarms for error rates and processing failures
    - Configure metric filters for log analysis
    - _Requirements: 21.8_

  - [~] 19.6 Write unit tests for logging module
    - Test log format compliance
    - Test error logging includes stack trace
    - Test sensitive data sanitization in logs
    - _Requirements: 21.1, 21.2_

- [x] 20. Implement security and access control
  - [x] 20.1 Configure IAM roles for Lambda functions
    - Create role for Auth Lambda (DynamoDB read/write, Cognito, SES)
    - Create role for Process Lambda (DynamoDB read/write, Textract, Bedrock, Secrets Manager)
    - Create role for Data Lambda (DynamoDB read/write)
    - Create role for Admin Lambda (DynamoDB read/write)
    - Create role for Integration Lambda (Secrets Manager, SES)
    - Apply least-privilege principle
    - _Requirements: 13.4_

  - [x] 20.2 Configure Secrets Manager for credentials
    - Store FTP credentials
    - Store SMTP credentials
    - Store API keys for external services
    - _Requirements: 13.5_

  - [x] 20.3 Implement HTTPS enforcement
    - Configure API Gateway to use HTTPS only
    - Ensure all session token transmission uses HTTPS
    - _Requirements: 13.9_

  - [~] 20.4 Write unit tests for security controls
    - Test IAM role permissions (verify least privilege)
    - Test Secrets Manager credential retrieval
    - Test unauthorized access rejection
    - _Requirements: 13.4, 13.5, 13.6, 13.7_

- [x] 21. Integration and end-to-end wiring
  - [x] 21.1 Wire extension to API Gateway
    - Configure API Gateway base URL in extension
    - Implement authentication header injection
    - Test all 16 API endpoints from extension
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 21.2 Implement error handling across all components
    - Add try-catch blocks to all async functions
    - Implement consistent error response format
    - Add error boundary components for UI
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.9_

  - [x] 21.3 Implement concurrent API call optimization
    - Identify independent API calls that can run concurrently
    - Use Promise.all for parallel execution
    - _Requirements: 15.5_

  - [x] 21.4 Configure extension permissions and CSP
    - Request minimal necessary permissions
    - Configure Content Security Policy
    - Test permission prompts on installation
    - _Requirements: 17.3, 17.7_

  - [~] 21.5 Write integration tests for complete workflows
    - Test complete document processing flow (extension → API → Lambda → AWS services → response)
    - Test authentication flow (login → session → authenticated request)
    - Test export flow (process → display → export to CSV/XLSX/JSON)
    - Test FTP integration flow (configure → test → export)
    - Test email integration flow (configure → test → send)
    - _Requirements: 1.1-1.12, 3.1-3.9, 6.1-6.12_

- [x] 22. Checkpoint - Ensure all integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 23. Implement visual design and styling
  - [x] 23.1 Apply Tailwind CSS styling to all components
    - Style all 5 tabs with consistent formatting
    - Apply black and white theme to banners and headers
    - Style buttons with visual distinction from black/white theme
    - Style tables with consistent formatting
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

  - [x] 23.2 Implement circular icon buttons for ACTION section
    - Create or import icon assets
    - Style buttons as circular icons
    - Add hover effects and tooltips
    - _Requirements: 16.5_

  - [x] 23.3 Implement collapsible sections
    - Add expand/collapse functionality to METADATA section
    - Add expand/collapse functionality to HISTORY section
    - Add expand/collapse functionality to Profile Setting section
    - Add expand/collapse functionality to Change Password section
    - Add expand/collapse functionality to Transaction History section
    - Provide clear visual indicators for expand/collapse state
    - _Requirements: 16.6_

  - [x] 23.4 Apply consistent form styling
    - Style all forms with consistent spacing and alignment
    - Style input fields, dropdowns, checkboxes, and radio buttons
    - Add focus states and validation styling
    - _Requirements: 16.7_

  - [~] 23.5 Write unit tests for UI components
    - Test collapsible section toggle
    - Test form field validation styling
    - Test responsive layout
    - _Requirements: 16.6, 16.7_


- [x] 24. Implement deployment and packaging
  - [x] 24.1 Create Lambda deployment packages
    - Package each Lambda function with dependencies
    - Create deployment scripts for AWS Lambda
    - Configure environment variables for each function
    - _Requirements: 10.3_

  - [x] 24.2 Create extension packaging script
    - Generate manifest.json with correct permissions
    - Package extension files for Chrome Web Store
    - Package extension files for Edge Add-ons store
    - _Requirements: 17.1, 17.2, 17.7_

  - [x] 24.3 Create infrastructure-as-code templates
    - Write CloudFormation or Terraform templates for all AWS resources
    - Include DynamoDB tables, Lambda functions, API Gateway, IAM roles, Cognito
    - Document deployment process
    - _Requirements: 10.1, 10.2, 12.1, 13.4_

  - [~] 24.4 Write deployment validation tests
    - Test Lambda function deployment and invocation
    - Test API Gateway endpoint availability
    - Test DynamoDB table creation and access
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 25. Final checkpoint - Complete system validation
  - Run all unit tests and property tests
  - Verify all 30 correctness properties pass
  - Test complete workflows end-to-end
  - Verify CloudWatch logging is working
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation uses JavaScript for the browser extension and Python for Lambda functions
- Property tests should run minimum 100 iterations each
- All sensitive credentials must be encrypted before storage
- Multi-tenant data isolation must be enforced at the query level
- The system requires AWS services: API Gateway, Lambda, DynamoDB, Textract, Bedrock, Cognito, Secrets Manager, CloudWatch, SES
- External libraries required: Tailwind CSS, fast-check, PapaParse, SheetJS, smtp.js (extension); boto3, hypothesis (Lambda)
