"""
python generate_graphql_rst.py \
    --env development \
    --auth_type [API_KEY, IAM, COGNITO_USER_POOLS, OPENID_CONNECT] \
    --endpoint https://<api-id>.appsync-api.<region>.amazonaws.com/graphql \
    --region AWS_Region \
    --api_key API_Key \
    --aws_access_key AWS_Access_Key \
    --aws_secret_key AWS_Secret_Key \
    --auth_token AWS_Authorization_Token \
    --id_token OPENID_Authorization_Token
    --user_pool_id Cognito_User_Pool_Id \
    --client_id Cognito_Client_Id
"""

import os
import argparse
from typing import Optional
import boto3
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth
import json
import requests


class CognitoAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = f"Bearer {self.token}"
        return r


def get_cognito_id_token(cognito_client, username: str, password: str, client_id: str):
    try:
        response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        # Get the ID Token (JWT)
        id_token = response['AuthenticationResult']['IdToken']
        return id_token
    except cognito_client.exceptions.NotAuthorizedException:
        print("The username or password is incorrect.")
        return None
    except ValueError:
        print("Credentials not found.")
        return None


def generate_headers(auth_type: str, region: str, endpoint: str, auth_details: dict):
    """
    Generate headers for AWS AppSync GraphQL queries based on the authentication type.
    
    :param auth_type: The authentication type (API_KEY, COGNITO_USER_POOLS, IAM, OPENID_CONNECT).
    :type auth_type: str
    :param region: AWS region of the AppSync service.
    :type region: str
    :param endpoint: The AppSync GraphQL endpoint.
    :type endpoint: str
    :param auth_details: Authentication details, such as API Key, Cognito credentials, etc.
    :type auth_details: dict

    :return: A dictionary of headers.
    :rtype: dict
    """
    headers = {
        "Content-Type": "application/json"
    }

    if auth_type == "API_KEY":
        # API Key Authentication
        if not auth_details.get("api_key"):
            raise ValueError("API Key is required for API_KEY authentication.")
        headers["x-api-key"] = auth_details["api_key"]

    elif auth_type == "IAM":
        
        if not auth_details.get("access_key") or not auth_details.get("secret_key"):
            credentials = boto3.Session().get_credentials()
            if not credentials:
                raise ValueError("AWS credentials not found. Please provide access_key and secret_key.")
            auth_details["access_key"] = credentials.access_key
            auth_details["secret_key"] = credentials.secret_key

        else:
            session = boto3.Session(
                aws_access_key_id=auth_details["access_key"],
                aws_secret_access_key=auth_details["secret_key"],
                region_name=region
            )
            credentials = session.get_credentials().get_frozen_credentials()


        query = """
        query fuzzySearchGammas ($title: String!, $organizationID: String!, $limit: Int, $nextToken: String) {
            fuzzySearchGammas (title: $title, organizationID: $organizationID, limit: $limit, nextToken: $nextToken) {
                nextToken
                total
            }
        }
        """ 
        variables = {
            "title": "right",
            "organizationID": "0856184c-c3f8-43ec-8361-7f62ba6a6a51"
        }

        body = json.dumps({
            "query": query,
            "variables": variables
        })

        aws_request = AWSRequest(
            method="POST",
            url=endpoint,
            data=body,
            headers=headers,
        )

        # Sign the request
        SigV4Auth(credentials, "appsync", region).add_auth(aws_request)

        # Send the signed request
        response = requests.request(
            method="POST",
            url=aws_request.url,
            headers=dict(aws_request.headers),
            data=body
        )
        if response.status_code == 200:
            print("Response: ", response.text)
        headers.update(aws_request.headers)
    
    elif auth_type == "COGNITO_USER_POOLS":
        if not auth_details["user_pool_id"] or not auth_details["client_id"]:
            raise ValueError("UserPool ID and Client ID is not provided!")
        username = str(input("Enter your Username: "))
        password = str(input("Enter your Password: "))

        cognito_client = boto3.client('cognito-idp', region_name=region)
        id_token = get_cognito_id_token(cognito_client, username, password, auth_details["client_id"])
        if id_token:
            query = """
            query fuzzySearchGammas ($title: String!, $organizationID: String!, $limit: Int, $nextToken: String) {
                fuzzySearchGammas (title: $title, organizationID: $organizationID, limit: $limit, nextToken: $nextToken) {
                    nextToken
                    total
                }
            }
            """ 
            variables = {
                "title": "right",
                "organizationID": "0856184c-c3f8-43ec-8361-7f62ba6a6a51"
            }

            body = json.dumps({
                "query": query,
                "variables": variables
            })

            auth = CognitoAuth(id_token)

            response = requests.post(
                endpoint,
                headers=headers,
                data=body,
                auth=auth
            )

            if response.status_code == 200:
                print("Response: ", response.text)
                headers.update({"Authorization": f"Bearer {id_token}"})

    elif auth_type == "OPENID_CONNECT":
        # OpenID Connect Authentication
        # Assume auth_details contains an id_token
        headers["Authorization"] = auth_details["id_token"]

    else:
        raise ValueError("Invalid authentication type. Supported types: API_KEY, COGNITO_USER_POOLS, IAM, OPENID_CONNECT.")

    return headers


def generate_graphql_rst(
    build_env: str,
    auth_type: str,
    endpoint: str,
    region: Optional[str] = None,
    api_key: Optional[str] = None,
    aws_access_key: Optional[str] = None,
    aws_secret_key: Optional[str] = None,
    auth_token: Optional[str] = None,
    id_token: Optional[str] = None,
    user_pool_id: Optional[str] = None,
    client_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> None:
    """
    Generates a graphql.rst file based on BUILD_ENV and authorization method.

    :param build_env: Environment in which the application is being built.
    :type build_env: str
    :param auth_type: Authorization method, either 'API_KEY' or 'IAM'.
    :type auth_type: str
    :param endpoint: GraphQL API endpoint.
    :type endpoint: str
    :param api_key: API Key for authorization (required if auth_type is 'API_KEY').
    :type api_key: Optional[str] or None
    :param aws_access_key: AWS Access Key (required if auth_type is 'IAM').
    :type aws_access_key: Optional[str] or None
    :param aws_secret_key: AWS Secret Key (required if auth_type is 'IAM').
    :type aws_secret_key: Optional[str] or None
    :param aws_secret_token: AWS Secret Token (required if auth_type is 'IAM').
    :type aws_secret_token: Optional[str] or None
    :param auth_token: AWS Authorization Token (required if auth_type is 'IAM').
    :type auth_token: Optional[str] or None
    :param id_token: OpenID Connect Authorization Token (required if auth_type is 'OPENID_CONNECT').
    :type id_token: Optional[str] or None
    :param user_pool_id: Cognito User Pool ID (required if auth_type is 'COGNITO_USER_POOLS').
    :type user_pool_id: Optional[str] or None
    :param client_id: Cognito Client ID (required if auth_type is 'COGNITO_USER_POOLS').
    :type client_id: Optional[str] or None
    :param username: Username of the authorized user (required if auth_type is 'COGNITO_USER_POOLS').
    :type username: Optional[str] or None
    :param password: Password of the authorized user (required if auth_type is 'COGNITO_USER_POOLS').
    :type password: Optional[str] or None

    :returns: N/A
    :rtype: None

    :raises: ValueError: If required parameters are missing or invalid.

    """
    file_path: str = "../docs/graphql.rst"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    auth_details: dict = {
        "api_key": api_key,
        "id_token": id_token,
        "access_key": aws_access_key,
        "secret_key": aws_secret_key,
        "auth_token": auth_token,
        "user_pool_id": user_pool_id,
        "client_id": client_id,
        "username": username,
        "password": password
    }
    # Generate headers based on authorization type
    headers: dict = generate_headers(auth_type=auth_type, region=region, endpoint=endpoint, auth_details=auth_details)


    with open(file_path, "w") as file:
        file.write("GraphQL API Documentation\n")
        file.write("==========================\n\n")

        # Write environment-specific content
        file.write(".. graphiql::\n")
        file.write(f"    :endpoint: {endpoint}\n")
        file.write(f"    :headers: {json.dumps(headers)}\n")

    print(f"`graphql.rst` file generated successfully at {file_path}.")


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Generate graphql.rst file for GraphQL API documentation."
    )
    parser.add_argument(
        "--env",
        required=True,
        help="Build environment.",
        type=str
    )
    parser.add_argument(
        "--auth_type",
        required=True,
        choices=["API_KEY", "IAM", "COGNITO_USER_POOLS", "OPENID_CONNECT"],
        help="Authorization type.",
        type=str
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="GraphQL endpoint.",
        type=str
    )
    parser.add_argument(
        "--api_key",
        help="API Key (required if auth_type is 'API_KEY').",
        type=str
    )
    parser.add_argument(
        "--region",
        help="AWS Region",
        required=True,
        type=str
    )
    parser.add_argument(
        "--aws_access_key",
        help="AWS Access Key",
        type=str
    )
    parser.add_argument(
        "--aws_secret_key",
        help="AWS Secret Key",
        type=str
    )
    parser.add_argument(
        "--auth_token",
        help="AWS Authentication Token",
        type=str
    )
    parser.add_argument(
        "--id_token",
        help="OPENID Authentication Token",
        type=str
    )
    parser.add_argument(
        "--user_pool_id",
        help="Cognito User Pool ID",
        type=str
    )
    parser.add_argument(
        "--client_id",
        help="Cognito Client ID",
        type=str
    )
    parser.add_argument(
        "--username",
        help="Username of the authorized user",
        type=str
    )
    parser.add_argument(
        "--password",
        help="Password of the authorized user",
        type=str
    )

    args: argparse.Namespace = parser.parse_args()

    generate_graphql_rst(
        build_env=args.env,
        auth_type=args.auth_type,
        endpoint=args.endpoint,
        region=args.region,
        api_key=args.api_key,
        aws_access_key=args.aws_access_key,
        aws_secret_key=args.aws_secret_key,
        auth_token=args.auth_token,
        id_token=args.id_token,
        user_pool_id=args.user_pool_id,
        client_id=args.client_id,
        username=args.username,
        password=args.password
    )


if __name__ == "__main__":
    main()