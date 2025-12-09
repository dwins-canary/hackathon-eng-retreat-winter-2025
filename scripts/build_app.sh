#!/bin/bash
# Build Voice Typer macOS app using PyInstaller

set -e

cd "$(dirname "$0")/.."

echo "Building Voice Typer.app..."

# Clean previous builds
rm -rf build dist

# Activate the project's virtual environment
if [ -d ".venv" ]; then
    echo "Using project's .venv..."
    source .venv/bin/activate
else
    echo "Warning: No .venv found, using current Python environment"
fi

# Ensure PyInstaller is installed
pip install pyinstaller -q

# Build the app using the spec file
pyinstaller "Voice Typer.spec" --noconfirm

echo ""
echo "Build complete!"
echo "App created at: dist/Voice Typer.app"
echo ""
echo "To install, drag 'Voice Typer.app' to your Applications folder."
