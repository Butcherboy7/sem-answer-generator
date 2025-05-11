#!/bin/bash

# This script generates requirements.txt for Render deployment

# Extract dependencies from pyproject.toml
python -c '
import toml
import re

with open("pyproject.toml") as f:
    data = toml.load(f)

deps = data["project"]["dependencies"]
processed_deps = []

for dep in deps:
    # Remove version specifiers
    name = re.sub(r">=.*", "", dep)
    # Skip paddleocr and paddlepaddle as they are problematic on Render
    if "paddle" not in name:
        processed_deps.append(name)

print("\n".join(processed_deps))
' > requirements.txt

# Add gunicorn explicitly
echo "gunicorn" >> requirements.txt

echo "Requirements file generated successfully!"