"""
Logging Utility Module for Lambda Functions
Provides structured logging with standard fields for all Lambda functions
"""

import json
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from aws_lambda_powertools import Logger


class StructuredLogger:
    """
    Structured logger wrapper that includes standard fields in all log messages
    
    Standard fields included:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level (INFO, ERROR, WARNING)
    - function_name: Lambda function name
    - request_id: AWS request ID from Lambda context
    - user_email: User email (if available)
    - tenant: Tenant ID (if available)
    """
    
    def __init__(self, service_name: str):
        """
        Initialize structured logger
        
        Args:
            service_name: Name of the Lambda service (e.g., 'process', 'auth', 'data')
        """
        self.logger = Logger(service=service_name)
        self.service_name = service_name
        self.context_data: Dict[str, Any] = {}
    
    def set_context(
        self,
        request_id: Optional[str] = None,
        user_email: Optional[str] = None,
        tenant: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Set context data that will be included in all subsequent log messages
        
        Args:
            request_id: AWS Lambda request ID
            user_email: User email address
            tenant: Tenant ID
            **kwargs: Additional context fields
        """
        if request_id:
            self.context_data['request_id'] = request_id
        if user_email:
            self.context_data['user_email'] = user_email
        if tenant:
            self.context_data['tenant'] = tenant
        
        # Add any additional context fields
        self.context_data.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context data"""
        self.context_data = {}
    
    def _build_log_data(self, message: str, **kwargs) -> Dict[str, Any]:
        """
        Build structured log data with standard fields
        
        Args:
            message: Log message
            **kwargs: Additional fields to include
            
        Returns:
            Dict containing structured log data
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': self.service_name
        }
        
        # Add context data
        log_data.update(self.context_data)
        
        # Add additional fields
        log_data.update(kwargs)
        
        return log_data
    
    def log_info(self, message: str, **kwargs) -> None:
        """
        Log informational message with structured fields
        
        Args:
            message: Log message
            **kwargs: Additional fields to include in log
            
        Example:
            logger.log_info("Document processing started", processing_id="123", pages=5)
        """
        log_data = self._build_log_data(message, **kwargs)
        self.logger.info(message, extra=log_data)
    
    def log_error(
        self,
        message: str,
        error: Optional[Exception] = None,
        include_stacktrace: bool = True,
        **kwargs
    ) -> None:
        """
        Log error message with structured fields and optional stack trace
        
        Args:
            message: Error message
            error: Exception object (optional)
            include_stacktrace: Whether to include stack trace in log
            **kwargs: Additional fields to include in log
            
        Example:
            try:
                # some operation
            except Exception as e:
                logger.log_error("Failed to process document", error=e, processing_id="123")
        """
        log_data = self._build_log_data(message, **kwargs)
        log_data['level'] = 'ERROR'
        
        if error:
            log_data['error_type'] = type(error).__name__
            log_data['error_message'] = str(error)
            
            if include_stacktrace:
                log_data['stack_trace'] = traceback.format_exc()
        
        self.logger.error(message, extra=log_data)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """
        Log warning message with structured fields
        
        Args:
            message: Warning message
            **kwargs: Additional fields to include in log
            
        Example:
            logger.log_warning("Document type not found, using default", document_type="Unknown")
        """
        log_data = self._build_log_data(message, **kwargs)
        log_data['level'] = 'WARNING'
        self.logger.warning(message, extra=log_data)
    
    def log_execution_start(self, function_name: str, **kwargs) -> None:
        """
        Log Lambda function execution start
        
        Args:
            function_name: Name of the Lambda function or handler
            **kwargs: Additional context fields
            
        Example:
            logger.log_execution_start("lambda_handler", event_type="process_document")
        """
        self.log_info(
            f"Execution started: {function_name}",
            function_name=function_name,
            execution_stage='start',
            **kwargs
        )
    
    def log_execution_complete(
        self,
        function_name: str,
        duration_ms: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Log Lambda function execution completion
        
        Args:
            function_name: Name of the Lambda function or handler
            duration_ms: Execution duration in milliseconds
            **kwargs: Additional context fields
            
        Example:
            logger.log_execution_complete("lambda_handler", duration_ms=1234, status="success")
        """
        log_data = {
            'function_name': function_name,
            'execution_stage': 'complete'
        }
        
        if duration_ms is not None:
            log_data['duration_ms'] = duration_ms
        
        log_data.update(kwargs)
        
        self.log_info(
            f"Execution completed: {function_name}",
            **log_data
        )
    
    def log_api_call(
        self,
        service: str,
        operation: str,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        **kwargs
    ) -> None:
        """
        Log AWS service API call
        
        Args:
            service: AWS service name (e.g., 'textract', 'bedrock', 'dynamodb')
            operation: Operation name (e.g., 'detect_document_text', 'invoke_model')
            duration_ms: API call duration in milliseconds
            status: Call status ('success', 'failure', 'retry')
            **kwargs: Additional fields
            
        Example:
            logger.log_api_call("textract", "detect_document_text", duration_ms=500, pages=3)
        """
        log_data = {
            'api_service': service,
            'api_operation': operation,
            'api_status': status
        }
        
        if duration_ms is not None:
            log_data['api_duration_ms'] = duration_ms
        
        log_data.update(kwargs)
        
        self.log_info(
            f"API call: {service}.{operation} - {status}",
            **log_data
        )
    
    def log_database_operation(
        self,
        table: str,
        operation: str,
        status: str = 'success',
        **kwargs
    ) -> None:
        """
        Log DynamoDB operation
        
        Args:
            table: DynamoDB table name
            operation: Operation type (e.g., 'put_item', 'query', 'get_item')
            status: Operation status ('success', 'failure')
            **kwargs: Additional fields
            
        Example:
            logger.log_database_operation("idp_metadata", "put_item", processing_id="123")
        """
        log_data = {
            'db_table': table,
            'db_operation': operation,
            'db_status': status
        }
        
        log_data.update(kwargs)
        
        self.log_info(
            f"Database operation: {table}.{operation} - {status}",
            **log_data
        )
    
    def log_processing_stage(
        self,
        stage: str,
        processing_id: str,
        duration_ms: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Log document processing pipeline stage
        
        Args:
            stage: Stage name (e.g., 'digitization', 'classification', 'extraction')
            processing_id: Processing ID
            duration_ms: Stage duration in milliseconds
            **kwargs: Additional fields
            
        Example:
            logger.log_processing_stage("digitization", "123", duration_ms=500, pages=3)
        """
        log_data = {
            'processing_stage': stage,
            'processing_id': processing_id
        }
        
        if duration_ms is not None:
            log_data['stage_duration_ms'] = duration_ms
        
        log_data.update(kwargs)
        
        self.log_info(
            f"Processing stage: {stage}",
            **log_data
        )
    
    def log_authentication_attempt(
        self,
        user_email: str,
        status: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log authentication attempt
        
        Args:
            user_email: User email address
            status: Authentication status ('success', 'failure')
            reason: Failure reason (optional)
            **kwargs: Additional fields
            
        Example:
            logger.log_authentication_attempt("user@example.com", "failure", reason="invalid_password")
        """
        log_data = {
            'auth_status': status,
            'user_email': user_email
        }
        
        if reason:
            log_data['auth_failure_reason'] = reason
        
        log_data.update(kwargs)
        
        self.log_info(
            f"Authentication attempt: {status}",
            **log_data
        )
    
    def get_powertools_logger(self) -> Logger:
        """
        Get the underlying AWS Lambda Powertools logger
        
        Returns:
            Logger instance for advanced usage
        """
        return self.logger


def create_logger(service_name: str) -> StructuredLogger:
    """
    Factory function to create a structured logger instance
    
    Args:
        service_name: Name of the Lambda service
        
    Returns:
        StructuredLogger instance
        
    Example:
        logger = create_logger('process')
        logger.set_context(request_id='abc-123', user_email='user@example.com')
        logger.log_info("Processing started")
    """
    return StructuredLogger(service_name)
