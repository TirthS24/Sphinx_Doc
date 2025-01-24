Authentication Page
===================

This page provides a web interface for generating various types of authentication tokens.

.. raw:: html
   :file: templates/auth.html


Usage
-----

The Auth Token Generator provides a web interface for generating different types of authentication tokens:

1. **IAM Authentication**
   - Requires: access key, secret key, region, API URL, and method
   - Returns: AWS SigV4 signature

2. **Cognito Authentication**
   - Requires: username, password, user pool ID, client ID, region, API URL, and method
   - Returns: Cognito JWT token

3. **API Key Authentication**
   - Requires: API key, API URL, and method
   - Returns: API key token

4. **Lambda Authentication**
   - Requires: Lambda function name, region, access key, secret key, API URL, and method
   - Returns: Custom Lambda-generated token


API Reference
-------------

The interface interacts with the following endpoint:

Generates an authentication token based on the provided credentials.

**Example request**:

.. code-block:: http

    POST /getToken HTTP/1.1
    Host: localhost:8000
    Content-Type: application/json

    {
        "auth_type": "IAM",
        "access_key": "your_access_key",
        "secret_key": "your_secret_key",
        "region": "us-west-2",
        "api_url": "https://api.example.com",
        "method": "GET"
    }

**Example response**:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "authorization_header": "AWS4-HMAC-SHA256...",
        "token_type": "AWS_IAM_SIGV4"
    }

Notes
-----

- Ensure the FastAPI server is running before using the interface
- All sensitive information is transmitted securely
- The interface is responsive and works on both desktop and mobile devices