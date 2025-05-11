
#!/bin/bash

# Render Build Script - This script will be run by Render during the build phase

# Add Python and pip to PATH
export PATH="/usr/local/bin:$PATH"

# Upgrade pip first to avoid dependency resolution issues
python3 -m pip install --upgrade pip

# Install Python dependencies (using singular requirement.txt)
python3 -m pip install -r requirements.txt

# Create necessary directories for file storage
mkdir -p uploads output temp

# Make directories writable for file operations
chmod -R 777 uploads output temp

echo "Build completed successfully!"
