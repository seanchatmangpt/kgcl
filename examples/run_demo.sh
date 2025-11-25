#!/bin/bash
# Quick demo runner for KGC OS Graph Agent Pipeline
#
# Usage:
#   ./run_demo.sh              # Run with defaults
#   ./run_demo.sh --verbose    # Run with verbose output
#   ./run_demo.sh --days 7     # Generate a full week

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}KGC OS Graph Agent Pipeline Demo${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if we're in the examples directory
if [ ! -f "full_pipeline_demo.py" ]; then
    echo -e "${YELLOW}Error: Must run from examples directory${NC}"
    echo "Run: cd examples && ./run_demo.sh"
    exit 1
fi

# Check Python dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
python -c "import kgcl" 2>/dev/null || {
    echo -e "${YELLOW}Installing package...${NC}"
    cd ..
    pip install -e . > /dev/null
    cd examples
}

# Run the demo
echo -e "${GREEN}Running pipeline demo...${NC}"
echo ""
python full_pipeline_demo.py "$@"

echo ""
echo -e "${GREEN}✓ Demo completed successfully!${NC}"
echo ""
echo -e "${BLUE}Output files generated in:${NC}"
echo "  sample_outputs/"
echo ""
echo -e "${BLUE}View results:${NC}"
echo "  cat sample_outputs/daily_brief.md"
echo "  cat sample_outputs/weekly_retro.md"
echo "  cat sample_outputs/feature_values.json"
echo ""
echo -e "${BLUE}Run tests:${NC}"
echo "  pytest test_full_example.py -v"
echo ""
