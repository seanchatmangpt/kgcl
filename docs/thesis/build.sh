#!/bin/bash
# =============================================================================
# KGCL PhD Thesis Build Script
# Compiles LaTeX to PDF with proper bibliography and cross-references
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

THESIS_NAME="kgcl-phd-thesis"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  KGCL PhD Thesis Build System${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for required tools
check_tool() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "${RED}✗${NC} $1 not found"
        return 1
    fi
}

echo -e "${YELLOW}Checking dependencies...${NC}"
echo ""

# Try different LaTeX distributions
LATEX_CMD=""
if check_tool "pdflatex"; then
    LATEX_CMD="pdflatex"
elif check_tool "xelatex"; then
    LATEX_CMD="xelatex"
elif check_tool "lualatex"; then
    LATEX_CMD="lualatex"
elif check_tool "tectonic"; then
    LATEX_CMD="tectonic"
else
    echo ""
    echo -e "${RED}ERROR: No LaTeX compiler found!${NC}"
    echo ""
    echo "Please install one of the following:"
    echo ""
    echo "  macOS (MacTeX):"
    echo "    brew install --cask mactex"
    echo "    # or smaller version:"
    echo "    brew install --cask basictex"
    echo ""
    echo "  macOS (Tectonic - recommended, fast):"
    echo "    brew install tectonic"
    echo ""
    echo "  Ubuntu/Debian:"
    echo "    sudo apt-get install texlive-full"
    echo "    # or smaller version:"
    echo "    sudo apt-get install texlive-latex-base texlive-latex-extra texlive-fonts-recommended"
    echo ""
    echo "  Fedora/RHEL:"
    echo "    sudo dnf install texlive-scheme-full"
    echo ""
    echo "  Windows:"
    echo "    Download MiKTeX from https://miktex.org/"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}Using LaTeX compiler: ${LATEX_CMD}${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build function
build_pdf() {
    echo -e "${YELLOW}Building PDF...${NC}"
    echo ""

    if [ "$LATEX_CMD" = "tectonic" ]; then
        # Tectonic handles everything in one pass
        echo "Running tectonic (single pass)..."
        tectonic "$THESIS_NAME.tex" -o "$OUTPUT_DIR" --keep-logs
    else
        # Traditional LaTeX: multiple passes for references
        echo "Pass 1/3: Initial compilation..."
        $LATEX_CMD -interaction=nonstopmode -output-directory="$OUTPUT_DIR" "$THESIS_NAME.tex" > /dev/null 2>&1 || true

        # Check if bibtex is needed (we use thebibliography, so skip)
        # echo "Pass 2/3: Processing bibliography..."
        # cd "$OUTPUT_DIR" && bibtex "$THESIS_NAME" > /dev/null 2>&1 || true
        # cd "$SCRIPT_DIR"

        echo "Pass 2/3: Resolving cross-references..."
        $LATEX_CMD -interaction=nonstopmode -output-directory="$OUTPUT_DIR" "$THESIS_NAME.tex" > /dev/null 2>&1 || true

        echo "Pass 3/3: Final compilation..."
        $LATEX_CMD -interaction=nonstopmode -output-directory="$OUTPUT_DIR" "$THESIS_NAME.tex" 2>&1 | tail -20
    fi
}

# Clean function
clean() {
    echo -e "${YELLOW}Cleaning auxiliary files...${NC}"
    rm -f "$OUTPUT_DIR"/*.aux "$OUTPUT_DIR"/*.log "$OUTPUT_DIR"/*.toc
    rm -f "$OUTPUT_DIR"/*.lof "$OUTPUT_DIR"/*.lot "$OUTPUT_DIR"/*.out
    rm -f "$OUTPUT_DIR"/*.bbl "$OUTPUT_DIR"/*.blg "$OUTPUT_DIR"/*.loa
    rm -f "$OUTPUT_DIR"/*.fls "$OUTPUT_DIR"/*.fdb_latexmk
    echo -e "${GREEN}✓ Cleaned${NC}"
}

# Main execution
case "${1:-build}" in
    build)
        build_pdf
        if [ -f "$OUTPUT_DIR/$THESIS_NAME.pdf" ]; then
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}  Build successful!${NC}"
            echo -e "${GREEN}========================================${NC}"
            echo ""
            echo -e "PDF location: ${BLUE}$OUTPUT_DIR/$THESIS_NAME.pdf${NC}"
            echo ""

            # Get PDF info
            if command -v pdfinfo &> /dev/null; then
                PAGES=$(pdfinfo "$OUTPUT_DIR/$THESIS_NAME.pdf" 2>/dev/null | grep "Pages:" | awk '{print $2}')
                SIZE=$(ls -lh "$OUTPUT_DIR/$THESIS_NAME.pdf" | awk '{print $5}')
                echo -e "Pages: ${YELLOW}$PAGES${NC}"
                echo -e "Size:  ${YELLOW}$SIZE${NC}"
            else
                SIZE=$(ls -lh "$OUTPUT_DIR/$THESIS_NAME.pdf" | awk '{print $5}')
                echo -e "Size: ${YELLOW}$SIZE${NC}"
            fi
            echo ""

            # Open PDF on macOS
            if [ "$(uname)" = "Darwin" ]; then
                echo -e "${YELLOW}Opening PDF...${NC}"
                open "$OUTPUT_DIR/$THESIS_NAME.pdf"
            fi
        else
            echo ""
            echo -e "${RED}========================================${NC}"
            echo -e "${RED}  Build failed!${NC}"
            echo -e "${RED}========================================${NC}"
            echo ""
            echo "Check the log file for errors:"
            echo "  $OUTPUT_DIR/$THESIS_NAME.log"
            exit 1
        fi
        ;;
    clean)
        clean
        ;;
    rebuild)
        clean
        build_pdf
        ;;
    watch)
        echo -e "${YELLOW}Watching for changes...${NC}"
        if command -v fswatch &> /dev/null; then
            fswatch -o "$THESIS_NAME.tex" | while read; do
                echo ""
                echo -e "${YELLOW}File changed, rebuilding...${NC}"
                build_pdf
            done
        elif command -v inotifywait &> /dev/null; then
            while inotifywait -e modify "$THESIS_NAME.tex"; do
                echo ""
                echo -e "${YELLOW}File changed, rebuilding...${NC}"
                build_pdf
            done
        else
            echo -e "${RED}ERROR: Install fswatch (macOS) or inotify-tools (Linux) for watch mode${NC}"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {build|clean|rebuild|watch}"
        echo ""
        echo "Commands:"
        echo "  build   - Build the PDF (default)"
        echo "  clean   - Remove auxiliary files"
        echo "  rebuild - Clean and rebuild"
        echo "  watch   - Watch for changes and auto-rebuild"
        exit 1
        ;;
esac
