## This script will generate `.rst` files for all JavaScript files in the given directory.
## Usage: python generate_js_rst.py --id <js_directory> --od <output_directory>
import os
import glob
import argparse
import logging

logging.basicConfig()

def generate_rst_from_js(js_directory, output_directory):
    """
    Generate `.rst` files for all JavaScript files in the given directory.
    """
    # Find all JavaScript files
    js_files = glob.glob(os.path.join(js_directory, '**/*.js'), recursive=True)
    
    # Loop through each JavaScript file and generate `.rst`
    print("JS Files: ", js_files)
    for js_file in js_files:
        with open(js_file, 'r') as f:
            js_content = f.read()
        
        # Extract the module name (use filename or module name logic)
        module_name = os.path.splitext(os.path.basename(js_file))[0]
        
        # Start building the .rst content
        supp = "=" * len(module_name)
        rst_content = f"{module_name}\n{supp}\n\n.. js:module:: {module_name}\n\n"
        
        # Extract functions from the JSDoc comments
        functions = extract_functions_from_js(js_content)

        print("Functions: ", functions)
        
        for func in functions:
            rst_content += f'.. js:autofunction:: {module_name}.{func["name"]}\n\n'
        
        # Write the generated .rst content to a file
        rst_file = os.path.join(output_directory, f"{module_name}.rst")
        with open(rst_file, 'w') as f:
            f.write(rst_content)
        print(f"Generated {rst_file}")
    


def extract_functions_from_js(js_content):
    """
    Extract function names and their JSDoc comments from a JavaScript file's content.
    """
    functions = []
    lines = js_content.split('\n')

    print("Lines: ", lines)
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('function ') or line.startswith('async function '):
            # Extract function name (assuming it's a simple function declaration)
            functions.append({"name": line.split('function')[1].split('{')[0].strip()})
    
    return functions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to Write RST file from JS file')
    parser.add_argument('--id', metavar='I', help='JS Input Directory', required=True)
    parser.add_argument('--od', metavar='O', help='Output Directory', required=True)
    args = parser.parse_args()
    scan_limit = 300
    if args.id is None or args.od is None:
        print("Please provide input and output directories")
        exit(1)
    js_directory = args.id  # Path to your JavaScript code
    output_directory = args.od  # Where to save the generated .rst files
    print("Input Directory: ", args.id)
    print("Output Directory: ", args.od)
    generate_rst_from_js(js_directory, output_directory)
