from abc import ABC, abstractmethod
import ast
import re
import json
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
import os
import logging
from datetime import datetime

def setup_logging():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, f'spec_gen_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

@dataclass
class EndpointInfo:
    """Data class to store endpoint information."""
    path: str
    methods: List[str]
    summary: str
    description: str
    parameters: List[Dict[str, Any]]
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]
    content_types: List[str]
    security: List[Dict[str, Any]]

class DocstringParser:
    """Parser for extracting endpoint information from docstrings."""
    
    @staticmethod
    def parse_docstring(docstring: str) -> Optional[EndpointInfo]:
        """
        Parse endpoint information from docstring.
        
        Args:
            docstring: Function or module docstring
            
        Returns:
            EndpointInfo if valid endpoint documentation is found, None otherwise
        """
        if not docstring:
            return None
            
        # Initialize default values
        info = {
            "path": "",
            "methods": [],
            "summary": "",
            "description": "",
            "parameters": [],
            "request_schema": {"type": "object", "properties": {}},
            "response_schema": {"type": "object", "properties": {}},
            "content_types": ["application/json"],
            "security": []
        }
        
        # Split docstring into lines and clean
        lines = [line.strip() for line in docstring.split('\n')]
        current_section = None
        response_json_started = False
        response_json_content = []
        
        for line in lines:
            if not line:
                continue
                
            # Check for main endpoint information
            if line.lower().startswith('endpoint:'):
                info['path'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('method:'):
                methods = line.split(':', 1)[1].strip()
                info['methods'] = [m.strip() for m in methods.split(',')]
            elif line.lower().startswith('description:'):
                info['description'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('summary:'):
                info['summary'] = line.split(':', 1)[1].strip()
            
            # Handle parameters section
            elif line.lower() == 'parameters:' or line.lower() == 'request:':
                current_section = 'parameters'
                continue
            elif line.lower() == 'response:':
                current_section = 'response'
                continue
            elif line.lower() == 'security:':
                current_section = 'security'
                continue
            
            # Process sections
            elif current_section == 'parameters' and line.startswith('-'):
                # Parse parameter
                param_line = line[1:].strip()
                if ':' in param_line:
                    param_name, param_desc = param_line.split(':', 1)
                    param = {
                        "name": param_name.strip(),
                        "in": "query",  # default to query, can be overridden
                        "description": param_desc.strip(),
                        "required": True,  # default to required
                        "schema": {"type": "string"}  # default to string
                    }
                    info['parameters'].append(param)
                    
                    # Add to request schema as well
                    info['request_schema']['properties'][param_name.strip()] = {
                        "type": "string",
                        "description": param_desc.strip()
                    }
            
            # Handle response schema
            elif current_section == 'response':
                if line.startswith('{'):
                    response_json_started = True
                    response_json_content = [line]
                elif response_json_started:
                    response_json_content.append(line)
                    if line.strip().endswith('}'):
                        # Try to parse complete JSON response
                        try:
                            response_text = ' '.join(response_json_content)
                            # Convert the pseudo-JSON format to proper JSON
                            response_text = re.sub(r'(\w+):', r'"\1":', response_text)
                            response_schema = json.loads(response_text)
                            info['response_schema'] = {
                                "type": "object",
                                "properties": {
                                    k: {"type": "string", "description": str(v)}
                                    for k, v in response_schema.items()
                                }
                            }
                        except json.JSONDecodeError:
                            pass
                        response_json_started = False
            
            # Handle security requirements
            elif current_section == 'security' and line.startswith('-'):
                security_req = line[1:].strip()
                if ':' in security_req:
                    sec_type, sec_desc = security_req.split(':', 1)
                    info['security'].append({
                        "type": sec_type.strip(),
                        "description": sec_desc.strip()
                    })
        
        # Only create EndpointInfo if we found an endpoint path
        if info['path']:
            # Default to GET if no method specified
            if not info['methods']:
                info['methods'] = ['GET']
            
            return EndpointInfo(**info)
        
        return None

class EndpointDetectorStrategy(ABC):
    """Abstract base class for endpoint detection strategies."""
    
    def __init__(self):
        self.docstring_parser = DocstringParser()
    
    @abstractmethod
    def detect_endpoints(self, file_content: str) -> List[EndpointInfo]:
        """
        Detect endpoints from the file content.
        
        Args:
            file_content: Source code content
            
        Returns:
            List of detected endpoints
        """
        pass
    
    def _extract_endpoints_from_docstrings(self, content: str) -> List[EndpointInfo]:
        """
        Extract endpoints directly from docstrings in the content.
        
        Args:
            content: Source code content
            
        Returns:
            List of endpoints found in docstrings
        """
        endpoints = []
        
        # Find all docstring-like patterns
        python_docstrings = re.finditer(r'"""(.*?)"""', content, re.DOTALL)
        js_docstrings = re.finditer(r'/\*(.*?)\*/', content, re.DOTALL)
        
        # Process Python-style docstrings
        for match in python_docstrings:
            docstring = match.group(1)
            endpoint_info = self.docstring_parser.parse_docstring(docstring)
            if endpoint_info:
                endpoints.append(endpoint_info)
        
        # Process JavaScript-style docstrings
        for match in js_docstrings:
            docstring = match.group(1)
            endpoint_info = self.docstring_parser.parse_docstring(docstring)
            if endpoint_info:
                endpoints.append(endpoint_info)
        
        return endpoints
    
class PythonVanillaDetector(EndpointDetectorStrategy):
    """Strategy for detecting endpoints in Python using app.route() and docstrings."""
    
    def detect_endpoints(self, file_content: str) -> List[EndpointInfo]:
        """
        Detect endpoints from Python source code using both route decorators and docstrings.
        
        Args:
            file_content: Python source code
            
        Returns:
            List of detected endpoints
        """
        endpoints: List[EndpointInfo] = []
        tree = ast.parse(file_content)
        
        # First try to find endpoints through app.route() decorators
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and 
                isinstance(node.func, ast.Attribute) and 
                node.func.attr == 'route'):
                
                # Find the corresponding function definition
                func_def = next(
                    (n for n in ast.walk(tree) 
                     if isinstance(n, ast.FunctionDef) and 
                     n.lineno > node.lineno),
                    None
                )
                
                if func_def:
                    route_info = self._parse_route_decorator(node)
                    docstring = ast.get_docstring(func_def) or ""
                    
                    # Try to get endpoint info from docstring first
                    endpoint_info = self.docstring_parser.parse_docstring(docstring)
                    
                    if endpoint_info:
                        # Update with route information if not in docstring
                        if route_info:
                            if not endpoint_info.path:
                                endpoint_info.path = route_info["path"]
                            if not endpoint_info.methods:
                                endpoint_info.methods = route_info["methods"]
                            endpoint_info.content_types = route_info["content_types"]
                    else:
                        # Create endpoint info from route decorator if no docstring info
                        endpoint_info = EndpointInfo(
                            path=route_info["path"],
                            methods=route_info["methods"],
                            summary=f"Endpoint for {func_def.name}",
                            description=docstring,
                            parameters=[],
                            request_schema={"type": "object", "properties": {}},
                            response_schema={"type": "object", "properties": {}},
                            content_types=route_info["content_types"],
                            security=[]
                        )
                    
                    endpoints.append(endpoint_info)
        
        # Then look for endpoints defined only in docstrings
        docstring_endpoints = self._extract_endpoints_from_docstrings(file_content)
        
        # Merge endpoints, avoiding duplicates
        seen_paths = {endpoint.path for endpoint in endpoints}
        for endpoint in docstring_endpoints:
            if endpoint.path not in seen_paths:
                endpoints.append(endpoint)
                seen_paths.add(endpoint.path)
        
        return endpoints
    
    def _parse_route_decorator(self, node: ast.Call) -> Dict[str, Any]:
        """
        Extract route details from the @app.route() decorator.
        
        Args:
            node: AST node representing the route decorator
            
        Returns:
            Dictionary containing route details
        """
        route_details = {
            "path": "",
            "methods": ["GET"],
            "content_types": ["application/json"]
        }
        
        # Extract path from first positional argument
        if node.args:
            route_details["path"] = node.args[0].value
        
        # Extract additional parameters from keywords
        for keyword in node.keywords:
            if keyword.arg == "methods":
                route_details["methods"] = [
                    method.value for method in keyword.value.elts
                ]
            elif keyword.arg == "content_types":
                route_details["content_types"] = [
                    content_type.value for content_type in keyword.value.elts
                ]
        
        return route_details

class PythonFlaskDetector(EndpointDetectorStrategy):
    """Strategy for detecting Flask endpoints in Python."""
    
    def detect_endpoints(self, file_content: str) -> List[EndpointInfo]:
        """
        Detect Flask endpoints from Python source code.
        
        Args:
            file_content: Python source code
            
        Returns:
            List of detected endpoints
        """
        endpoints = []
        tree = ast.parse(file_content)
        
        # First try to find routes with decorators
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and 
                isinstance(node.func, ast.Attribute) and 
                node.func.attr == 'route'):
                
                func_def = next(
                    (n for n in ast.walk(tree) 
                     if isinstance(n, ast.FunctionDef) and 
                     n.lineno > node.lineno),
                    None
                )
                
                if func_def:
                    docstring = ast.get_docstring(func_def) or ""
                    endpoint_info = self.docstring_parser.parse_docstring(docstring)
                    
                    if endpoint_info:
                        # Update path and methods from decorator if not in docstring
                        route_info = self._parse_flask_route(node)
                        if route_info:
                            if not endpoint_info.path:
                                endpoint_info.path = route_info["path"]
                            if not endpoint_info.methods:
                                endpoint_info.methods = route_info["methods"]
                        endpoints.append(endpoint_info)
        
        # Then look for endpoints defined only in docstrings
        docstring_endpoints = self._extract_endpoints_from_docstrings(file_content)
        
        # Merge endpoints, avoiding duplicates
        seen_paths = {endpoint.path for endpoint in endpoints}
        for endpoint in docstring_endpoints:
            if endpoint.path not in seen_paths:
                endpoints.append(endpoint)
                seen_paths.add(endpoint.path)
        
        return endpoints
    
    def _parse_flask_route(self, node: ast.Call) -> Optional[Dict[str, Any]]:
        """
        Parse Flask route decorator attributes.
        
        Args:
            node: AST node representing the route decorator
            
        Returns:
            Dictionary containing route details or None if invalid
        """
        route_info: Dict[str, Any] = {
            "path": "",
            "methods": ["GET"],
            "content_types": ["application/json"]
        }
        
        try:
            # Extract path from first argument
            if node.args:
                route_info["path"] = node.args[0].value
            
            # Extract other parameters from keywords
            for keyword in node.keywords:
                if keyword.arg == "methods":
                    route_info["methods"] = [m.value for m in keyword.value.elts]
                elif keyword.arg == "content_types":
                    route_info["content_types"] = [ct.value for ct in keyword.value.elts]
            
            return route_info
        except AttributeError:
            return None


class PythonFastAPIDetector(EndpointDetectorStrategy):
    """Strategy for detecting FastAPI endpoints in Python."""
    
    def detect_endpoints(self, file_content: str) -> List[EndpointInfo]:
        """
        Detect FastAPI endpoints from Python source code.
        
        Args:
            file_content: Python source code
            
        Returns:
            List of detected endpoints
        """
        endpoints: List[EndpointInfo] = []
        tree = ast.parse(file_content)
        
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and 
                isinstance(node.func, ast.Name) and 
                node.func.id in ['get', 'post', 'put', 'delete']):
                
                func_def = next(
                    (n for n in ast.walk(tree) 
                     if isinstance(n, ast.FunctionDef) and 
                     n.lineno > node.lineno),
                    None
                )
                
                if func_def:
                    method = node.func.id.upper()
                    path = node.args[0].value if node.args else "/"
                    
                    docstring = ast.get_docstring(func_def) or ""
                    doc_info = self._parse_fastapi_docs(docstring)
                    
                    endpoints.append(EndpointInfo(
                        path=path,
                        methods=[method],
                        summary=doc_info["summary"],
                        description=doc_info["description"],
                        request_schema=doc_info["request_schema"],
                        response_schema=doc_info["response_schema"],
                        content_types=["application/json"]
                    ))
        
        return endpoints
    
    def _parse_fastapi_docs(self, docstring: str) -> Dict[str, Any]:
        """Similar to Flask docstring parsing but adapted for FastAPI conventions."""
        # Implementation similar to Flask's _parse_docstring
        pass



class TypeScriptExpressDetector(EndpointDetectorStrategy):
    """Strategy for detecting Express.js endpoints in TypeScript/JavaScript."""
    
    def detect_endpoints(self, file_content: str) -> List[EndpointInfo]:
        """
        Detect Express.js endpoints from TypeScript/JavaScript source code.
        
        Args:
            file_content: TypeScript/JavaScript source code
            
        Returns:
            List of detected endpoints
        """
        endpoints = []
        
        # First try to find Express.js routes
        route_pattern = r'(app|router)\.(get|post|put|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]'
        
        for match in re.finditer(route_pattern, file_content):
            # Find associated docstring
            docstring_match = re.search(r'/\*(.*?)\*/', file_content[:match.start()], re.DOTALL)
            
            if docstring_match:
                endpoint_info = self.docstring_parser.parse_docstring(docstring_match.group(1))
                if endpoint_info:
                    # Update with route information if not in docstring
                    if not endpoint_info.path:
                        endpoint_info.path = match.group(3)
                    if not endpoint_info.methods:
                        endpoint_info.methods = [match.group(2).upper()]
                    endpoints.append(endpoint_info)
        
        # Then look for endpoints defined only in docstrings
        docstring_endpoints = self._extract_endpoints_from_docstrings(file_content)
        
        # Merge endpoints, avoiding duplicates
        seen_paths = {endpoint.path for endpoint in endpoints}
        for endpoint in docstring_endpoints:
            if endpoint.path not in seen_paths:
                endpoints.append(endpoint)
                seen_paths.add(endpoint.path)
        
        return endpoints
    

class OpenAPISpecGenerator:
    """Main class for generating OpenAPI specifications from various sources."""
    
    def __init__(self, file_paths: List[str]):
        """Initialize with file paths."""
        self.file_paths = file_paths
        self.strategies: Dict[str, Type[EndpointDetectorStrategy]] = {
            ".py": {
                "flask": PythonFlaskDetector,
                "fastapi": PythonFastAPIDetector,
                "vanilla": PythonVanillaDetector
            },
            ".ts": {
                "express": TypeScriptExpressDetector
            }
        }
    
    def generate_specification(self) -> Dict[str, Any]:
        """Generate OpenAPI specification from all source files."""
        spec = {
            "openapi": "3.0.1",
            "info": {
                "title": "API Specification",
                "version": "1.0.0"
            },
            "paths": {}
        }
        
        for file_path in self.file_paths:
            detector, content = self._detect_language_and_framework(file_path)
            if detector:
                endpoints = detector.detect_endpoints(content)
                
                for endpoint in endpoints:
                    if endpoint.path not in spec["paths"]:
                        spec["paths"][endpoint.path] = {}
                    
                    for method in endpoint.methods:
                        operation = {
                            "summary": endpoint.summary,
                            "description": endpoint.description,
                            "parameters": endpoint.parameters,
                            "responses": {
                                "200": {
                                    "description": "Successful response",
                                    "content": {
                                        ct: {"schema": endpoint.response_schema}
                                        for ct in endpoint.content_types
                                    }
                                }
                            }
                        }
                        
                        if endpoint.security:
                            operation["security"] = endpoint.security
                        
                        spec["paths"][endpoint.path][method.lower()] = operation
        
        return spec
    
    def _detect_language_and_framework(self, file_path: str) -> tuple[Optional[EndpointDetectorStrategy], str]:
        """
        Detect the programming language and framework from file content.
        
        Args:
            file_path: Path to source code file
            
        Returns:
            Tuple of (detector strategy, file content)
        """
        extension = os.path.splitext(file_path)[1]
        
        with open(file_path, 'r') as file:
            content = file.read()
        
        if extension == '.py':
            if 'fastapi' in content.lower():
                return self.strategies['.py']['fastapi'](), content
            if 'flask' in content.lower():
                return self.strategies['.py']['flask'](), content
            return self.strategies['.py']['vanilla'](), content
        elif extension == '.ts' or extension == '.js':
            return self.strategies['.ts']['express'](), content
        
        return None, content
    
    def save_specification(self, output_path: str = "openapi_spec.json") -> None:
        """
        Save the generated specification to a file.
        
        Args:
            output_path: Path to save the specification file
        """
        spec = self.generate_specification()
        with open(output_path, 'w') as spec_file:
            json.dump(spec, spec_file, indent=2)
        print(f"OpenAPI specification saved to {output_path}")

def main() -> None:
    """Main entry point for the script."""
    # if len(sys.argv) < 2:
    #     logger.error("Usage: python smart_openapi_generator.py <source_file1> [<source_file2> ...]")
    #     sys.exit(1)
    
    # Collect all lambda file paths from command-line arguments
    file_paths = []
    with open("input_script_spec.txt", "r") as file:
        for path in file:
            if path and path != "":
                file_paths.append(path.strip())
    
    # Validate file paths
    for path in file_paths:
        if not os.path.isfile(path):
            print(f"Error: File not found - {path}")
            sys.exit(1)
    
    generator = OpenAPISpecGenerator(file_paths)
    generator.save_specification("../src/openapi_spec.json")

if __name__ == "__main__":
    import sys
    main()