from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json
import base64

app = FastAPI(title="AWS Auth Token Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TokenRequest(BaseModel):
    auth_type: Literal["COGNITO", "API_KEY"]
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    # Cognito specific fields
    client_id: Optional[str] = None
    region: Optional[str] = None
    # Target API details
    api_url: Optional[str] = None
    method: str = "POST"
    

class TokenResponse(BaseModel):
    authorization_header: str
    token_type: str
    additional_headers: Optional[Dict[str, str]] = None


# def generate_sigv4_auth_header(credentials, url, method, region, service='execute-api'):
#     """Generate AWS SigV4 signature for API Gateway"""
#     request = AWSRequest(
#         method=method,
#         url=url,
#         data=''
#     )
    
#     sigv4 = SigV4Auth(credentials, service, region)
#     sigv4.add_auth(request)
    
#     return request.headers['Authorization']


def get_cognito_token(username: str, password: str, client_id: str, region: str) -> str:
    """Get Cognito authentication token using user credentials"""
    client = boto3.client('cognito-idp', region_name=region)
    
    try:
        response = client.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            },
            ClientId=client_id
        )
        
        return response['AuthenticationResult']['IdToken']
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# def get_lambda_token(lambda_function_name: str, payload: Dict[str, Any], 
#                     region: str, credentials) -> Dict[str, str]:
#     """Invoke Lambda authorizer and get token/headers"""
#     try:
#         lambda_client = boto3.client(
#             'lambda',
#             region_name=region,
#             aws_access_key_id=credentials.get('access_key'),
#             aws_secret_access_key=credentials.get('secret_key'),
#             aws_session_token=credentials.get('session_token')
#         )

#         # Prepare the event payload for the Lambda authorizer
#         event = {
#             "type": "TOKEN",
#             "methodArn": "arn:aws:execute-api:region:account-id:api-id/stage/method/resourcepath",
#             "authorizationToken": base64.b64encode(json.dumps(payload).encode()).decode(),
#             "resource": "/",
#             "path": "/",
#             "httpMethod": "POST"
#         }

#         response = lambda_client.invoke(
#             FunctionName=lambda_function_name,
#             InvocationType='RequestResponse',
#             Payload=json.dumps(event)
#         )
        
#         # Parse Lambda response
#         response_payload = json.loads(response['Payload'].read())
        
#         if response_payload.get('statusCode', 200) != 200:
#             raise HTTPException(
#                 status_code=401,
#                 detail=f"Lambda authorizer denied access: {response_payload.get('body', 'No details provided')}"
#             )

#         # Extract authorization information from Lambda response
#         context = response_payload.get('context', {})
        
#         headers = {
#             'Authorization': context.get('authorizationToken', ''),
#         }
        
#         # Add any additional custom headers from Lambda response
#         for key, value in context.items():
#             if key != 'authorizationToken':
#                 headers[f'X-Lambda-{key}'] = str(value)

#         return headers
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Lambda authorization failed: {str(e)}"
#         )


@app.post("/getToken", response_model=TokenResponse)
async def get_token(request: TokenRequest):
    try:
        # if request.auth_type == "IAM":
        #     if not all([request.access_key, request.secret_key, request.region]):
        #         raise HTTPException(
        #             status_code=400,
        #             detail="access_key, secret_key, and region are required for IAM authentication"
        #         )
            
        #     credentials = boto3.Session(
        #         aws_access_key_id=request.access_key,
        #         aws_secret_access_key=request.secret_key,
        #         aws_session_token=request.session_token
        #     ).get_credentials()
            
        #     auth_header = generate_sigv4_auth_header(
        #         credentials,
        #         request.api_url,
        #         request.method,
        #         request.region
        #     )
            
        #     return TokenResponse(
        #         authorization_header=auth_header,
        #         token_type="AWS_IAM_SIGV4"
        #     )
            
        if request.auth_type == "COGNITO":
            if not all([request.username, request.password, request.client_id, request.region]):
                raise HTTPException(
                    status_code=400,
                    detail="username, password, client_id, and region are required for Cognito authentication"
                )
            
            token = get_cognito_token(
                request.username,
                request.password,
                request.client_id,
                request.region
            )
            
            return TokenResponse(
                authorization_header=f"Bearer {token}",
                token_type="COGNITO_JWT"
            )
            
        elif request.auth_type == "API_KEY":
            if not request.api_key:
                raise HTTPException(
                    status_code=400,
                    detail="api_key is required for API_KEY authentication"
                )
                            
            return TokenResponse(
                authorization_header=request.api_key,
                token_type="API_KEY"
            )

        # elif request.auth_type == "LAMBDA":
        #     if not all([request.lambda_function_name, request.lambda_payload, request.region]):
        #         raise HTTPException(
        #             status_code=400,
        #             detail="lambda_function_name, lambda_payload, and region are required for Lambda authentication"
        #         )

        #     credentials = {
        #         'access_key': request.access_key,
        #         'secret_key': request.secret_key,
        #         'session_token': request.session_token
        #     }
            
        #     headers = get_lambda_token(
        #         request.lambda_function_name,
        #         request.lambda_payload,
        #         request.region,
        #         credentials
        #     )
            
        #     return TokenResponse(
        #         authorization_header=headers.pop('Authorization'),
        #         token_type="LAMBDA_CUSTOM",
        #         additional_headers=headers
        #     )
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported auth_type: {request.auth_type}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)