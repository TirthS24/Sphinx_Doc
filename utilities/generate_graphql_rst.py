"""
python generate_graphql_rst.py \
    --env development \
    --auth_type [API_KEY, IAM] \
    --endpoint https://<api-id>.appsync-api.<region>.amazonaws.com/graphql \
    --region AWS_Region \
    --api_key API_Key \
    --ak AWS_Access_Key \
    --sk AWS_Secret_Key \
    --st AWS_Secret_Token
"""

import os
import argparse
from typing import Optional
import boto3
from datetime import datetime, timezone
import hmac
import hashlib
import json

def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


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

    elif auth_type == "COGNITO_USER_POOLS" or auth_type == "IAM":
        
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

        # sts_client = boto3.client(
        #     "sts",
        #     aws_access_key_id=auth_details["access_key"],
        #     aws_secret_access_key=auth_details["secret_key"],
        # )
        # sts_credentials = sts_client.get_session_token(DurationSeconds=3000)
        # print("Credentials: ", sts_credentials)
        # headers["Authorization"] = sts_credentials["Credentials"]["SessionToken"]

        # Generate SigV4 headers
        method = "POST"
        service = "appsync"
        host = endpoint.split("://")[1]
        canonical_uri = "/graphql"
        canonical_querystring = ""
        amz_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        
        # Step 1: Create Canonical Request
        payload = '{"query":"query MyQuery { listGammas(limit: 1) { items { UserVotes id friendlyId title rank } } }"}'

        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        print("Computed Payload Hash: ", payload_hash)
        canonical_headers = f"host:{host}\nx-amz-date:{amz_date}\n"
        signed_headers = "host;x-amz-date"
        canonical_request = (
            f"{method}\n{canonical_uri}\n{canonical_querystring}\n"
            f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )
        
        # Step 2: Create String to Sign
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )
        
        # Step 3: Calculate Signature
        k_secret = f"AWS4{auth_details['secret_key']}".encode("utf-8")
        k_date = sign(k_secret, date_stamp)
        k_region = sign(k_date, region)
        k_service = sign(k_region, service)
        k_signing = sign(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # Step 4: Add Signing Information to Headers
        authorization_header = (
            f"AWS4-HMAC-SHA256 Credential={auth_details['access_key']}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        
        headers["Authorization"] = authorization_header
        headers["x-amz-date"] = amz_date

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
        "auth_token": auth_token
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
        id_token=args.id_token
    )


if __name__ == "__main__":
    main()