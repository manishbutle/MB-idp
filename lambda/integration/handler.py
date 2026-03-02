"""
Integration Lambda Function
Handles FTP uploads and email sending
"""

import json
import time
import boto3
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from logger_util import create_logger

logger = create_logger('integration')
tracer = Tracer()

ses = boto3.client('ses')
secrets_manager = boto3.client('secretsmanager')


@tracer.capture_method
def get_ftp_credentials(secret_name: str = 'idp/ftp/credentials') -> dict:
    """
    Retrieve FTP credentials from AWS Secrets Manager
    
    Args:
        secret_name: Name of the secret in Secrets Manager
        
    Returns:
        Dictionary containing FTP credentials
        
    Raises:
        Exception: If credentials cannot be retrieved
    """
    try:
        logger.log_info(f"Retrieving FTP credentials from Secrets Manager: {secret_name}")
        response = secrets_manager.get_secret_value(SecretId=secret_name)
        credentials = json.loads(response['SecretString'])
        logger.log_info("FTP credentials retrieved successfully")
        return credentials
    except Exception as e:
        logger.log_error(f"Failed to retrieve FTP credentials: {str(e)}")
        raise


@tracer.capture_method
def handle_ftp(event, context):
    """
    Handle FTP upload
    
    Expected event body:
    {
        "file_name": "document.csv",
        "file_content": "base64_encoded_content",
        "remote_directory": "/uploads" (optional),
        "secret_name": "idp/ftp/credentials" (optional)
    }
    
    Requirements: 19.1, 19.2, 19.3, 19.4, 19.7
    """
    logger.log_info("FTP upload request received")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        file_name = body.get('file_name')
        file_content = body.get('file_content')
        remote_directory = body.get('remote_directory', '')
        secret_name = body.get('secret_name', 'idp/ftp/credentials')
        
        # Validate required fields
        if not file_name:
            logger.log_warning("Missing file_name in request")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'file_name is required'
                })
            }
        
        if not file_content:
            logger.log_warning("Missing file_content in request")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'file_content is required'
                })
            }
        
        # Retrieve FTP credentials from Secrets Manager
        try:
            credentials = get_ftp_credentials(secret_name)
        except Exception as e:
            logger.log_error(f"Failed to retrieve FTP credentials: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'Failed to retrieve FTP credentials'
                })
            }
        
        # Extract FTP configuration
        host = credentials.get('host')
        port = credentials.get('port', 21)
        username = credentials.get('username')
        password = credentials.get('password')
        
        # Validate credentials
        if not all([host, username, password]):
            logger.log_error("Incomplete FTP credentials in Secrets Manager")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Configuration Error',
                    'message': 'Incomplete FTP credentials'
                })
            }
        
        # Import ftplib for FTP operations
        import ftplib
        import base64
        from io import BytesIO
        
        # Decode file content from base64
        try:
            file_data = base64.b64decode(file_content)
        except Exception as e:
            logger.log_error(f"Failed to decode file content: {str(e)}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Invalid file_content encoding'
                })
            }
        
        # Connect to FTP server
        try:
            logger.log_info(f"Connecting to FTP server: {host}:{port}")
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=30)
            ftp.login(username, password)
            logger.log_info("FTP connection established")
            
            # Change to remote directory if specified (Requirement 19.3)
            if remote_directory:
                try:
                    logger.log_info(f"Changing to remote directory: {remote_directory}")
                    ftp.cwd(remote_directory)
                except ftplib.error_perm as e:
                    logger.log_warning(f"Remote directory does not exist, attempting to create: {remote_directory}")
                    # Try to create the directory
                    try:
                        ftp.mkd(remote_directory)
                        ftp.cwd(remote_directory)
                    except Exception as create_error:
                        logger.log_error(f"Failed to create remote directory: {str(create_error)}")
                        ftp.quit()
                        return {
                            'statusCode': 400,
                            'body': json.dumps({
                                'error': 'Bad Request',
                                'message': f'Remote directory does not exist and cannot be created: {remote_directory}'
                            })
                        }
            
            # Upload file (Requirement 19.4)
            logger.log_info(f"Uploading file: {file_name}")
            file_obj = BytesIO(file_data)
            ftp.storbinary(f'STOR {file_name}', file_obj)
            
            # Close connection
            ftp.quit()
            logger.log_info(f"File uploaded successfully: {file_name}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'File uploaded successfully',
                    'file_name': file_name,
                    'remote_directory': remote_directory if remote_directory else 'default'
                })
            }
            
        except ftplib.error_perm as e:
            logger.log_error(f"FTP permission error: {str(e)}")
            return {
                'statusCode': 503,
                'body': json.dumps({
                    'error': 'Service Unavailable',
                    'message': f'FTP permission error: {str(e)}'
                })
            }
        except ftplib.error_temp as e:
            logger.log_error(f"FTP temporary error: {str(e)}")
            return {
                'statusCode': 503,
                'body': json.dumps({
                    'error': 'Service Unavailable',
                    'message': f'FTP temporary error: {str(e)}'
                })
            }
        except Exception as e:
            logger.log_error(f"FTP connection failed: {str(e)}")
            return {
                'statusCode': 503,
                'body': json.dumps({
                    'error': 'Service Unavailable',
                    'message': f'FTP connection failed: {str(e)}'
                })
            }
            
    except Exception as e:
        logger.log_error(f"Unexpected error in FTP handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_method
def handle_send_email(event, context):
    """
    Handle email sending using AWS SES
    
    Expected event body:
    {
        "to": "recipient@example.com",
        "cc": "cc@example.com" (optional),
        "subject": "Email subject",
        "body": "Email body text",
        "attachments": [
            {
                "filename": "data.csv",
                "content": "base64_encoded_content",
                "content_type": "text/csv"
            }
        ] (optional)
    }
    
    Requirements: 18.1, 18.3, 18.4, 18.5, 18.6, 18.7
    """
    logger.log_info("Send email request received")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        to_address = body.get('to')
        cc_address = body.get('cc')
        subject = body.get('subject')
        email_body = body.get('body')
        attachments = body.get('attachments', [])
        
        # Validate required fields
        if not to_address:
            logger.log_warning("Missing 'to' address in request")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'to address is required'
                })
            }
        
        if not subject:
            logger.log_warning("Missing subject in request")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'subject is required'
                })
            }
        
        if not email_body:
            logger.log_warning("Missing body in request")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'body is required'
                })
            }
        
        # Build recipient list
        destinations = {
            'ToAddresses': [to_address]
        }
        
        if cc_address:
            destinations['CcAddresses'] = [cc_address]
        
        # Get sender email from environment variable or use default
        import os
        sender = os.environ.get('SES_SENDER_EMAIL', 'noreply@example.com')
        
        # Send email without attachments (simple email)
        if not attachments:
            logger.log_info(f"Sending simple email to {to_address}")
            try:
                response = ses.send_email(
                    Source=sender,
                    Destination=destinations,
                    Message={
                        'Subject': {
                            'Data': subject,
                            'Charset': 'UTF-8'
                        },
                        'Body': {
                            'Text': {
                                'Data': email_body,
                                'Charset': 'UTF-8'
                            }
                        }
                    }
                )
                
                logger.log_info(f"Email sent successfully. MessageId: {response['MessageId']}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Email sent successfully',
                        'message_id': response['MessageId']
                    })
                }
                
            except Exception as e:
                logger.log_error(f"Failed to send email: {str(e)}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Internal Server Error',
                        'message': f'Failed to send email: {str(e)}'
                    })
                }
        
        # Send email with attachments (raw email with MIME)
        else:
            logger.log_info(f"Sending email with {len(attachments)} attachment(s) to {to_address}")
            
            # Import email libraries for MIME construction
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.application import MIMEApplication
            import base64
            
            # Create MIME message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = to_address
            
            if cc_address:
                msg['Cc'] = cc_address
            
            # Add body text
            msg.attach(MIMEText(email_body, 'plain', 'UTF-8'))
            
            # Add attachments (Requirements 18.3, 18.4, 18.5, 18.6, 18.7)
            for attachment in attachments:
                filename = attachment.get('filename')
                content = attachment.get('content')
                content_type = attachment.get('content_type', 'application/octet-stream')
                
                if not filename or not content:
                    logger.log_warning(f"Skipping invalid attachment: {attachment}")
                    continue
                
                try:
                    # Decode base64 content
                    file_data = base64.b64decode(content)
                    
                    # Create attachment part
                    part = MIMEApplication(file_data)
                    part.add_header('Content-Disposition', 'attachment', filename=filename)
                    
                    # Set content type based on file format
                    if content_type:
                        part.set_type(content_type)
                    
                    msg.attach(part)
                    logger.log_info(f"Attached file: {filename} ({content_type})")
                    
                except Exception as e:
                    logger.log_error(f"Failed to attach file {filename}: {str(e)}")
                    # Continue with other attachments
            
            # Send raw email
            try:
                response = ses.send_raw_email(
                    Source=sender,
                    Destinations=[to_address] + ([cc_address] if cc_address else []),
                    RawMessage={
                        'Data': msg.as_string()
                    }
                )
                
                logger.log_info(f"Email with attachments sent successfully. MessageId: {response['MessageId']}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Email sent successfully',
                        'message_id': response['MessageId'],
                        'attachments_count': len(attachments)
                    })
                }
                
            except Exception as e:
                logger.log_error(f"Failed to send email with attachments: {str(e)}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Internal Server Error',
                        'message': f'Failed to send email: {str(e)}'
                    })
                }
    
    except json.JSONDecodeError as e:
        logger.log_error(f"Invalid JSON in request body: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        logger.log_error(f"Unexpected error in email handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Main Lambda handler"""
    start_time = time.time()
    path = event.get('path', '')
    
    # Set initial context
    logger.set_context(
        request_id=context.request_id if hasattr(context, 'request_id') else 'unknown'
    )
    
    logger.log_execution_start("lambda_handler", path=path, http_method=event.get('httpMethod', ''))
    
    try:
        if path == '/ftp':
            result = handle_ftp(event, context)
        elif path == '/send_email':
            result = handle_send_email(event, context)
        else:
            result = {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_execution_complete("lambda_handler", duration_ms=duration_ms, status_code=result.get('statusCode'))
        
        return result
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_error("Unexpected error in lambda_handler", error=e, duration_ms=duration_ms)
        logger.log_execution_complete("lambda_handler", duration_ms=duration_ms, status="error")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error'})
        }
    finally:
        logger.clear_context()


