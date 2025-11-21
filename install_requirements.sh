#!/bin/bash
# Install all required dependencies

echo "Installing Python requirements..."
pip install -r requirements.txt

echo "Installing Playwright browsers..."
playwright install chromium

echo "Installation complete!"