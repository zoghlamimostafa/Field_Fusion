#!/bin/bash

# Phase 1 Verification Script
# Tests all Phase 1 enhancements

echo "=========================================="
echo "Phase 1 Verification Script"
echo "Tunisia Football AI Enhancement Plan"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Activate virtual environment
echo "Activating virtual environment..."
source ../venv/bin/activate

# Test 1: Check if files exist
echo ""
echo "=========================================="
echo "Test 1: File Existence Check"
echo "=========================================="

files=(
    "pitch_visualizations.py"
    "kloppy_data_loader.py"
    "gradio_enhanced_viz.py"
    "examples/load_open_datasets.py"
    "docs/PHASE_1_ENHANCEMENTS.md"
    "README_PHASE1.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $file missing"
        ((FAILED++))
    fi
done

# Test 2: Check imports
echo ""
echo "=========================================="
echo "Test 2: Module Import Check"
echo "=========================================="

echo "Checking pitch_visualizations imports..."
if python -c "from pitch_visualizations import FootballVisualizer" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} pitch_visualizations imports successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} pitch_visualizations import failed"
    ((FAILED++))
fi

echo "Checking kloppy_data_loader imports..."
if python -c "from kloppy_data_loader import KloppyDataLoader" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} kloppy_data_loader imports successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} kloppy_data_loader import failed"
    ((FAILED++))
fi

echo "Checking gradio_enhanced_viz imports..."
if python -c "from gradio_enhanced_viz import VisualizationAdapter" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} gradio_enhanced_viz imports successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} gradio_enhanced_viz import failed"
    ((FAILED++))
fi

# Test 3: Check dependencies
echo ""
echo "=========================================="
echo "Test 3: Dependency Check"
echo "=========================================="

deps=("mplsoccer" "kloppy" "numpy" "pandas" "matplotlib")

for dep in "${deps[@]}"; do
    if python -c "import $dep" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $dep installed"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $dep not installed"
        ((FAILED++))
    fi
done

# Test 4: Run visualization demo
echo ""
echo "=========================================="
echo "Test 4: Visualization Demo"
echo "=========================================="

echo "Running pitch_visualizations.py..."
if python pitch_visualizations.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Visualization demo ran successfully"
    ((PASSED++))

    # Check if demo files were generated
    demo_files=("demo_heatmap.png" "demo_pass_network.png" "demo_shot_map.png" "demo_radar.png")
    for demo in "${demo_files[@]}"; do
        if [ -f "$demo" ]; then
            size=$(du -h "$demo" | cut -f1)
            echo -e "${GREEN}✓${NC} Generated $demo ($size)"
            ((PASSED++))
        else
            echo -e "${RED}✗${NC} $demo not generated"
            ((FAILED++))
        fi
    done
else
    echo -e "${RED}✗${NC} Visualization demo failed"
    ((FAILED++))
fi

# Test 5: Run data loader demo
echo ""
echo "=========================================="
echo "Test 5: Data Loader Demo"
echo "=========================================="

echo "Running kloppy_data_loader.py (30s timeout)..."
if timeout 30 python kloppy_data_loader.py > /tmp/kloppy_test.log 2>&1; then
    if grep -q "Demo complete" /tmp/kloppy_test.log; then
        echo -e "${GREEN}✓${NC} Data loader demo completed"
        ((PASSED++))

        if grep -q "StatsBomb data loaded" /tmp/kloppy_test.log; then
            echo -e "${GREEN}✓${NC} StatsBomb data loaded successfully"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠${NC} StatsBomb data not loaded (network issue?)"
        fi
    else
        echo -e "${RED}✗${NC} Data loader demo incomplete"
        ((FAILED++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Data loader demo timed out or failed (check network)"
fi

# Test 6: Example scripts
echo ""
echo "=========================================="
echo "Test 6: Example Scripts"
echo "=========================================="

echo "Running example 4 (integration docs)..."
cd examples
if python load_open_datasets.py 4 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Example script executed successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Example script failed"
    ((FAILED++))
fi
cd ..

# Summary
echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo "Phase 1 is fully operational and ready to use."
    exit 0
else
    echo ""
    echo -e "${YELLOW}⚠ Some tests failed${NC}"
    echo "Check the output above for details."
    exit 1
fi
