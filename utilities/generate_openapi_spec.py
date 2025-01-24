import ast
import re
import json
from typing import Dict, List, Optional, Any
import sys
import os

class OpenAPISpecGenerator:
    """
    A class to generate OpenAPI 3.0.1 specification from multiple AWS Lambda integration functions.
    
    This generator extracts route information and specification details 
    directly from method docstrings, providing flexibility for developers.
    """
    
    def __init__(self, lambda_file_paths: List[str]):
        """
        Initialize the OpenAPI specification generator with multiple lambda files.
        
        Args:
            lambda_file_paths (List[str]): List of full paths to Lambda function Python files
        """
        self.lambda_file_paths = lambda_file_paths
        self.spec: Dict[str, Any] = {
            "openapi": "3.0.1",
            "info": {
                "title": "Lambda API Specification",
                "version": "1.0.0"
            },
            "paths": {}
        }
    
    def _extract_route_details(self, node: ast.Call) -> Dict[str, Any]:
        """
        Extract route details from the @app.route() decorator.
        
        Args:
            node (ast.Call): AST node representing the route decorator
        
        Returns:
            Dict containing route details like path, methods, cors
        """
        route_details = {
            "path": "",
            "methods": ["GET"],
            "cors": False,
            "content_types": ["application/json"]
        }
        
        for keyword in node.keywords:
            if keyword.arg == "methods":
                route_details["methods"] = [
                    method.value for method in keyword.value.elts
                ]
            elif keyword.arg == "cors":
                route_details["cors"] = keyword.value.value
            elif keyword.arg == "content_types":
                route_details["content_types"] = [
                    content_type.value for content_type in keyword.value.elts
                ]
        
        # Extract path from first positional argument
        if node.args:
            route_details["path"] = node.args[0].value
        
        return route_details
    
    def _parse_docstring_specification(self, docstring: str) -> Dict[str, Any]:
        """
        Parse the docstring to extract OpenAPI specification details.
        
        Args:
            docstring (str): Full docstring of the route method
        
        Returns:
            Dict containing parsed specification details
        """
        # Default specification structure
        spec = {
            "summary": "",
            "description": docstring,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                }
            }
        }
        
        # Split docstring into lines and process
        lines = [line.strip() for line in docstring.split('\n')]
        
        # Extract key details
        for line in lines:
            # Try to extract summary
            summary_match = re.match(r'^Summary:\s*(.+)$', line, re.IGNORECASE)
            if summary_match:
                spec['summary'] = str(summary_match.group(1))
            
            # Try to extract method
            method_match = re.match(r'^Method:\s*(.+)$', line, re.IGNORECASE)
            if method_match:
                spec['method'] = method_match.group(1)
            
            # Try to extract description
            description_match = re.match(r'^Description:\s*(.+)$', line, re.IGNORECASE)
            if description_match:
                spec['description'] = description_match.group(1)
        
        # Try to parse request and response details
        try:
            request_start = lines.index("Request:")
            response_start = lines.index("Response:")
            
            # Extract request details
            request_details = lines[request_start+1:response_start]
            request_schema = {"type": "object", "properties": {}}
            
            for detail in request_details:
                if ':' in detail:
                    param, description = detail.split(':', 1)
                    request_schema["properties"][param.strip()] = {
                        "type": "string",
                        "description": description.strip()
                    }
            
            # Extract response details
            response_details = lines[response_start+1:]
            response_schema = {"type": "object", "properties": {}}
            
            for detail in response_details:
                if ':' in detail:
                    param, description = detail.split(':', 1)
                    response_schema["properties"][param.strip()] = {
                        "type": "string", 
                        "description": description.strip()
                    }
            
            # Update responses in spec
            spec['responses']['200']['content']['application/json']['schema'] = response_schema
            
        except ValueError:
            # If no explicit Request/Response sections found, keep defaults
            pass
        
        return spec
    
    def generate_specification(self) -> Dict[str, Any]:
        """
        Generate the complete OpenAPI specification by parsing multiple Lambda functions.
        
        Returns:
            Dict containing the complete OpenAPI specification
        """
        # Process each lambda file
        for lambda_file_path in self.lambda_file_paths:
            with open(lambda_file_path, 'r') as file:
                file_content = file.read()
                tree = ast.parse(file_content)
            
            for node in ast.walk(tree):
                # Look for route decorators
                if (isinstance(node, ast.Call) and 
                    isinstance(node.func, ast.Attribute) and 
                    node.func.attr == 'route'):
                    
                    # Find the corresponding function definition
                    func_node = next(
                        (parent for parent in ast.iter_child_nodes(tree) 
                         if isinstance(parent, ast.FunctionDef) and 
                         parent.lineno > node.lineno), 
                        None
                    )
                    
                    if func_node:
                        route_details = self._extract_route_details(node)
                        
                        # Extract docstring
                        docstring = ast.get_docstring(func_node) or ""
                        
                        # Parse docstring for specification details
                        parsed_spec = self._parse_docstring_specification(docstring)
                        
                        # Construct operation object for each method
                        for method in route_details["methods"]:
                            operation = {
                                "summary": parsed_spec.get('summary', f"Endpoint for {func_node.name}"),
                                "description": parsed_spec.get('description', docstring),
                                "responses": parsed_spec.get('responses', {
                                    "200": {
                                        "description": "Successful response",
                                        "content": {
                                            content_type: {
                                                "schema": {"type": "object"}
                                            } for content_type in route_details["content_types"]
                                        }
                                    }
                                })
                            }
                            
                            # Add to paths, handling potential path conflicts
                            if route_details["path"] in self.spec["paths"]:
                                # If path exists, update or merge methods
                                self.spec["paths"][route_details["path"]][method.lower()] = operation
                            else:
                                # Add new path entry
                                self.spec["paths"][route_details["path"]] = {
                                    method.lower(): operation
                                }
        
        return self.spec
    
    def save_specification(self, output_path: str = "openapi_spec.json"):
        """
        Save the generated specification to a file.
        
        Args:
            output_path (str, optional): Path to save the specification file. 
                                         Defaults to "openapi_spec.json".
        """
        with open(output_path, 'w') as spec_file:
            json.dump(self.spec, spec_file, indent=2)
        
        print(f"OpenAPI specification saved to {output_path}")

def main():
    """
    Main function to run the OpenAPI specification generator.
    
    Expects multiple Lambda function file paths as command-line arguments.
    """
    if len(sys.argv) < 2:
        print("Usage: python openapi_spec_generator.py <path_to_lambda_function1> [<path_to_lambda_function2> ...]")
        sys.exit(1)
    
    # Collect all lambda file paths from command-line arguments
    lambda_file_paths = sys.argv[1:]
    
    # Validate file paths
    for path in lambda_file_paths:
        if not os.path.isfile(path):
            print(f"Error: File not found - {path}")
            sys.exit(1)
    
    generator = OpenAPISpecGenerator(lambda_file_paths)
    spec = generator.generate_specification()
    generator.save_specification("../src/openapi_spec.json")

if __name__ == "__main__":
    main()