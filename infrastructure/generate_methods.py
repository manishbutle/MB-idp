#!/usr/bin/env python3
"""
Generate API Gateway method configurations for all 16 endpoints.
This script creates the YAML configuration for POST/GET methods and OPTIONS (CORS).
"""

# Endpoint configuration: (path, method, lambda_function, requires_auth)
ENDPOINTS = [
    # Auth Lambda - No authentication required
    ('auth', 'POST', 'AuthLambda', False),
    ('forget_password', 'POST', 'AuthLambda', False),
    ('reset_password', 'POST', 'AuthLambda', False),
    ('sign_up', 'POST', 'AuthLambda', False),
    
    # Process Lambda - Authentication required
    ('process_document', 'POST', 'ProcessLambda', True),
    
    # Data Lambda - Authentication required
    ('datapoints', 'GET', 'DataLambda', True),
    ('reset_prompts', 'POST', 'DataLambda', True),
    ('history', 'GET', 'DataLambda', True),
    ('mytransactions', 'GET', 'DataLambda', True),
    ('total_document_processed', 'GET', 'DataLambda', True),
    ('available_balance', 'GET', 'DataLambda', True),
    ('profile_change', 'POST', 'DataLambda', True),
    ('password_change', 'POST', 'DataLambda', True),
    ('top_up', 'POST', 'DataLambda', True),
    
    # Admin Lambda - Authentication required (System User role)
    ('add_credit', 'POST', 'AdminLambda', True),
    
    # Integration Lambda - Authentication required
    ('ftp', 'POST', 'IntegrationLambda', True),
    ('send_email', 'POST', 'IntegrationLambda', True),
]

def to_pascal_case(snake_str):
    """Convert snake_case to PascalCase"""
    return ''.join(word.capitalize() for word in snake_str.split('_'))

def generate_method_config(path, http_method, lambda_func, requires_auth):
    """Generate CloudFormation YAML for a single method"""
    resource_name = to_pascal_case(path) + 'Resource'
    method_name = to_pascal_case(path) + http_method.capitalize() + 'Method'
    lambda_arn = f'${{{lambda_func}Arn}}'
    
    auth_type = 'COGNITO_USER_POOLS' if requires_auth else 'NONE'
    authorizer_id = '!Ref CognitoAuthorizer' if requires_auth else ''
    
    config = f"""
  # {http_method} /{path}
  {method_name}:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref IdpRestApi
      ResourceId: !Ref {resource_name}
      HttpMethod: {http_method}
      AuthorizationType: {auth_type}"""
    
    if requires_auth:
        config += f"""
      AuthorizerId: {authorizer_id}"""
    
    config += f"""
      RequestValidatorId: !Ref RequestValidator
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub 'arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
      MethodResponses:
        - StatusCode: 200
          ResponseParameters:
            method.response.header.Access-Control-Allow-Origin: true
        - StatusCode: 400
          ResponseParameters:
            method.response.header.Access-Control-Allow-Origin: true
        - StatusCode: 401
          ResponseParameters:
            method.response.header.Access-Control-Allow-Origin: true
        - StatusCode: 500
          ResponseParameters:
            method.response.header.Access-Control-Allow-Origin: true
"""
    return config

def generate_options_method(path):
    """Generate CORS OPTIONS method for a resource"""
    resource_name = to_pascal_case(path) + 'Resource'
    method_name = to_pascal_case(path) + 'OptionsMethod'
    
    return f"""
  # OPTIONS /{path} (CORS)
  {method_name}:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref IdpRestApi
      ResourceId: !Ref {resource_name}
      HttpMethod: OPTIONS
      AuthorizationType: NONE
      Integration:
        Type: MOCK
        IntegrationResponses:
          - StatusCode: 200
            ResponseParameters:
              method.response.header.Access-Control-Allow-Headers: "'Content-Type,Authorization'"
              method.response.header.Access-Control-Allow-Methods: "'GET,POST,OPTIONS'"
              method.response.header.Access-Control-Allow-Origin: "'*'"
            ResponseTemplates:
              application/json: ''
        RequestTemplates:
          application/json: '{{"statusCode": 200}}'
      MethodResponses:
        - StatusCode: 200
          ResponseParameters:
            method.response.header.Access-Control-Allow-Headers: true
            method.response.header.Access-Control-Allow-Methods: true
            method.response.header.Access-Control-Allow-Origin: true
"""

def main():
    """Generate all method configurations"""
    output = []
    
    # Add request validator
    output.append("""
  # Request Validator
  RequestValidator:
    Type: AWS::ApiGateway::RequestValidator
    Properties:
      RestApiId: !Ref IdpRestApi
      Name: RequestBodyValidator
      ValidateRequestBody: true
      ValidateRequestParameters: false
""")
    
    # Generate methods for each endpoint
    for path, method, lambda_func, requires_auth in ENDPOINTS:
        output.append(generate_method_config(path, method, lambda_func, requires_auth))
        output.append(generate_options_method(path))
    
    return '\n'.join(output)

if __name__ == '__main__':
    print(main())
