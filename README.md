# Auto API Doc Documentation

# ChangeLog

| Sr. No. | Section name | Author | Date |
| --- | --- | --- | --- |
| 1. | Overview, Set Up, Future Scope | Aksh Patel and Tirth Shah | 27-01-2025 |

---

# Overview

- It is a software package that enables developers (and users) to view executable API endpoints to leverage functionality of API documentation.
    
    ## What it does?
    
    - It has a script (written in Python → [utilities/utilities/generate_openapi_spec.py](https://github.com/TirthS24/Sphinx_Doc/blob/main/utilities/generate_openapi_spec.py)). More on it in this section.
    - Auto generation of web (HTML) interface for executable API documentation from `.rst` markdown files using Sphinx Python package.
        - Executable REST API endpoints doc from OpenAPI(or Swagger) specification file.
        - Executable GraphQL IDE (playground) from GraphQL endpoint.
    
    ## Purpose
    
    - It is used to provide ease to Front-End devs in following ways:
        - Able to execute REST and GraphQL APIs without the help of Back-End devs.
        - Able to identify and respond to the endpoints’ Request and Response body.
        - Able to make custom GraphQL queries based on required fields.
        - Able to quickly access the APIs once developed and documented by Back End devs.
    - It is useful to Back-End devs in following ways:
        - It provides a script to generate OpenAPI specification for REST endpoints without manually writing it down, just a command to generate the file.
        - Easy to maintain and test the API documentation, can avoid the use of applications to test and configure endpoints such as Postman, etc.

---

# Set Up

Following are the steps to set-up this Repository in local system.

1. Clone the repository by running the following command in new directory:

```bash
git clone https://github.com/TirthS24/Sphinx_Doc
cd Sphinx_Doc
```

2. Install Python in your system if not.
3. Create a virtual environment by running the following command:

```bash
python -m venv .venv
```

4. Enable the virtual environment by running following command:

```bash
# For Mac/Linux
source .venv/bin/activate

 # For Windows
.\.venv\Scripts\activate     
```

5. Install the requirements specified in requirements.txt file by running the following command:

```bash
pip install -r requirements.txt
```

6. Run the following command to build static web application on API Documentation using Sphinx:

```bash
sphinx-build -b html <path_to_docs_folder> <path_to_docs/_build_folder>
```

> Note: `<path_to_docs_folder>` `<path_to_docs/_build_folder>` and denotes the path of docs folder and path of docs/_build folder respectively relative to where you are running the command in terminal.
> 
7. Run a [localhost](http://localhost) server (using extensions like Live Server in VSCode) and open the index.html file created in docs/_build/index.html
8. In case you need to modify any of the following files:
- any .rst files
- any files under template directory
- change in [config.py](http://config.py) file
You need to perform following steps:
- Delete the existing /docs/_build folder
- Re run the command in step 6.

---

## Project Structure

```bash
.
├── docs
│   ├── Makefile
│   ├── _build
│   │   ├── doctrees
│   │   └── html
│   ├── apidoc.rst
│   ├── conf.py
│   ├── graphql.rst
│   ├── index.rst
│   ├── make.bat
│   └── templates
│       └── auth.html
├── requirements.txt
├── src
│   ├── comment_spec.yaml
│   └── petstore.json
└── utilities
    ├── __init__.py
    ├── auth_server.py
    ├── generate_openapi_spec.py
    └── input_script_spec.txt
```

## Important Files

### 1. docs/conf.py

It is used for following:

- Configure Project and Author details
- Configure extensions of Sphinx if you are importing new

### 2. docs/index.rst

It is used for following:

- Markdown file acting as a home page for our web application.
- Determine the names of other `.rst` files (only names) in the `.. toctree::` section to navigate to pages.

### 3. docs/graphql.rst

It is used for following:

- Specifies the GraphQL endpoint where the queries will be requested and performed

### 4. docs/apidoc.rst

It is used for following:

- Specify the following parameters:
    - spec_url - URL of the OpenAPI specification file hosted on a server
    - theme - light/dark based on your preference
    - render-style - view/read/focused based on your preference

### 5. utilities/auth_server.py

It is used for following:

- Implements a FastAPI Python server to serve Authorization Token for AWS based auth.
- It supports following Auth Type:
    - API KEY based
    - COGNITO based (Bearer JWT Token)
- Returns Authorization header to include in REST and GraphQL endpoints to execute.
- Execution:
    
    ```bash
    python auth_server.py
    ```
    
- Limitations:
    - Currently supports only two authentication methods.

### 6. utilities/generate_openapi_spec.py

- This script read all lambda function code (integrated with specific API gateway endpoint) provided in the argument and look for the docstring of endpoint (@app.route) method and extracts endpoint specifications such as summary, description, http-method, response structure etc.
- Execution:

```python
python generate_openapi_spec.py lambda_path1 lambda_path2 ... lambda_pathN
```

- Limitations:
    - it will not detect if the doc-string is written under a function without @app.route directive.
    
    Also it is limited to Python language only.
    
    - We are trying to identify docstring for other language files as well.

### 7. utilities/input_script_spec.txt

It is used for following:

- Enlists the path of files (Python or JS) where the endpoints Docstring are written for a particular group of endpoints having same base URL.
- If there are multiple base URL endpoints, write a separate list with a new-line sperator. (In the below code, first three lines are associated to Post endpoints and after double new-line are associated to Comment endpoints.)
    
    ```
    post/index.py
    post/post_mods.py
    post/analytics.py
    
    comment/index.py
    comment/comment_mods.py
    comment/analytics.py
    ```
    

---

# Future Scope

### 1. CI/CD Workflow

We do have plans to write a workflow file for GitHub Actions to perform all the above set-up steps and modify the Documentation every time the specs are changed in the target branch.

### 2. Spec generation script

We are aiming to extend support for following:
- Various programming languages namely Javascript(TypeScript) and C# to identify doc-string

---

# Requriements

- Python version 3.9 and above is required to install add dependencies.
- Remember to turn on the `auth_server.py` Server to obtain Authentication token, else it will result in error.
