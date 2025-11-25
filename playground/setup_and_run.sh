#!/bin/bash

# Setup and run playground examples
# This script builds the package and runs playground examples

set -e

echo "======================================================================"
echo "Chicago TDD Tools - Playground Setup & Execution"
echo "======================================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Please run from project root."
    exit 1
fi

# Step 1: Create virtual environment (if it doesn't exist)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Step 2: Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Step 3: Install the package from source (build)
echo ""
echo "Building and installing chicago-tdd-tools package..."
pip install --upgrade pip setuptools wheel
pip install -e .
echo "✓ Package installed from build"

# Step 4: Verify installation
echo ""
echo "Verifying installation..."
python -c "import chicago_tdd_tools; print(f'✓ chicago-tdd-tools version: {chicago_tdd_tools.__version__}')"

# Step 5: Run playground examples
echo ""
echo "======================================================================"
echo "Running Playground Examples"
echo "======================================================================"

cd playground

echo ""
echo "--- Running Basic Usage Examples ---"
python basic_usage.py

echo ""
echo "--- Running Advanced Workflow Examples ---"
python advanced_workflows.py

echo ""
echo "======================================================================"
echo "✓ All playground examples completed!"
echo "======================================================================"
echo ""
echo "To run individual examples later:"
echo "  source venv/bin/activate"
echo "  cd playground"
echo "  python basic_usage.py"
echo "  python advanced_workflows.py"
echo ""
