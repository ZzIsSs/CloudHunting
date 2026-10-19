#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Building frontend application..."
cd frontend/cloud-hunting-app
npm install
npm run build
cd ../..

echo "Build complete!"
