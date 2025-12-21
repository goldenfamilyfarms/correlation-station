#!/usr/bin/env python
"""
Parse pip-compile output and extract unique packages with versions.

This script helps identify which packages need to be added to requirements_python38.txt
and which ones might already exist.
"""

import re
import sys

def parse_pip_compile_output(content):
    """Parse pip-compile output and extract packages."""
    packages = {}
    comments = {}
    
    lines = content.split('\n')
    current_package = None
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Match package with version: package==version
        match = re.match(r'^([a-zA-Z0-9_-]+)==([0-9.]+[a-z0-9]*)', line)
        if match:
            package_name = match.group(1)
            version = match.group(2)
            packages[package_name] = version
            current_package = package_name
            comments[package_name] = []
        
        # Match "via" comments
        elif line.startswith('# via'):
            if current_package:
                comments[current_package].append(line)
    
    return packages, comments

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python parse_pip_compile.py <pip-compile-output-file>")
        print("\nExample:")
        print("  python parse_pip_compile.py pip_compile_output.txt")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    try:
        with open(filename, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    
    packages, comments = parse_pip_compile_output(content)
    
    print("=" * 60)
    print("Packages to Add to requirements_python38.txt")
    print("=" * 60)
    print()
    
    # Sort packages alphabetically
    for package in sorted(packages.keys()):
        version = packages[package]
        print(f"{package}=={version}")
    
    print()
    print("=" * 60)
    print(f"Total packages: {len(packages)}")
    print("=" * 60)
    
    # Show packages with "via -r requirements_otel.txt" (directly requested)
    print()
    print("=" * 60)
    print("Directly Requested Packages (from requirements_otel.txt)")
    print("=" * 60)
    print()
    
    direct_packages = []
    for package, comment_list in comments.items():
        for comment in comment_list:
            if 'via -r requirements_otel.txt' in comment:
                direct_packages.append(package)
                break
    
    for package in sorted(direct_packages):
        version = packages[package]
        print(f"{package}=={version}")
    
    print()
    print(f"Total directly requested: {len(direct_packages)}")

if __name__ == "__main__":
    main()

