#!/bin/bash

# Phase 2 Verification Script
# Tunisia Football AI - Advanced Physical Analytics
#
# This script verifies that all Phase 2 components are properly installed
# and working correctly.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

echo "=========================================="
echo "Phase 2 Verification Script"
echo "Tunisia Football AI - Advanced Analytics"
echo "=========================================="
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source ../venv/bin/activate

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Failed to activate virtual environment"
    exit 1
fi

echo ""
echo "=========================================="
echo "Test 1: File Existence Check"
echo "=========================================="

files=(
    "metabolic_power_analyzer.py"
    "space_control_analyzer.py"
    "action_valuation.py"
    "tests/test_metabolic_power.py"
    "tests/test_space_control.py"
    "examples/phase2_demos.py"
    "README_PHASE2.md"
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

echo ""
echo "=========================================="
echo "Test 2: Module Import Check"
echo "=========================================="

echo "Checking metabolic_power_analyzer imports..."
python3 -c "import metabolic_power_analyzer" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} metabolic_power_analyzer imports successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} metabolic_power_analyzer import failed"
    ((FAILED++))
fi

echo "Checking space_control_analyzer imports..."
python3 -c "import space_control_analyzer" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} space_control_analyzer imports successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} space_control_analyzer import failed"
    ((FAILED++))
fi

echo "Checking action_valuation imports..."
python3 -c "import action_valuation" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} action_valuation imports successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} action_valuation import failed"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Test 3: Dependency Check"
echo "=========================================="

dependencies=(
    "numpy"
    "scipy"
    "pandas"
    "matplotlib"
)

for dep in "${dependencies[@]}"; do
    python3 -c "import $dep" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $dep installed"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $dep not installed"
        ((FAILED++))
    fi
done

echo ""
echo "=========================================="
echo "Test 4: Metabolic Power Tests"
echo "=========================================="

python3 tests/test_metabolic_power.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All metabolic power tests passed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Metabolic power tests failed"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Test 5: Space Control Tests"
echo "=========================================="

python3 tests/test_space_control.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All space control tests passed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Space control tests failed"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Test 6: Demo Execution"
echo "=========================================="

timeout 60 python3 examples/phase2_demos.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Phase 2 demos ran successfully"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Phase 2 demos failed"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Test 7: Module Functionality"
echo "=========================================="

echo "Testing metabolic power calculation..."
python3 -c "
from metabolic_power_analyzer import MetabolicPowerAnalyzer
import numpy as np
analyzer = MetabolicPowerAnalyzer()
velocities = [5.0] * 100
accelerations = [0.5] * 100
power = analyzer.calculate_metabolic_power(np.array(velocities), np.array(accelerations))
assert len(power) == 100
assert all(p >= 0 for p in power)
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Metabolic power calculation works"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Metabolic power calculation failed"
    ((FAILED++))
fi

echo "Testing space control calculation..."
python3 -c "
from space_control_analyzer import SpaceControlAnalyzer
analyzer = SpaceControlAnalyzer()
positions = {1: (30, 30, 1), 2: (30, 40, 1), 3: (70, 30, 2), 4: (70, 40, 2)}
metrics = analyzer.calculate_space_control(positions)
assert metrics is not None
assert 0 <= metrics.team_1_control_percent <= 100
assert 0 <= metrics.team_2_control_percent <= 100
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Space control calculation works"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Space control calculation failed"
    ((FAILED++))
fi

echo "Testing action valuation..."
python3 -c "
from action_valuation import ActionValuationAnalyzer, Action, ActionType
analyzer = ActionValuationAnalyzer()
action = Action(1, player_id=10, team_id=1, action_type=ActionType.SHOT, start_x=90, start_y=34)
value = analyzer.value_action(action)
assert value.total_value > 0
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Action valuation works"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Action valuation failed"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Test 8: Output Format Validation"
echo "=========================================="

echo "Testing JSON export formats..."
python3 -c "
from metabolic_power_analyzer import MetabolicPowerAnalyzer
from space_control_analyzer import SpaceControlAnalyzer
from action_valuation import ActionValuationAnalyzer, Action, ActionType
import numpy as np

# Test metabolic power export
mp_analyzer = MetabolicPowerAnalyzer()
metrics = mp_analyzer.analyze_player([5.0]*100, [0.5]*100, 10, 1)
export = mp_analyzer.export_metrics(metrics)
assert 'player_id' in export
assert 'energy_metrics' in export

# Test space control export
sc_analyzer = SpaceControlAnalyzer()
positions = {1: (30, 30, 1), 2: (70, 30, 2), 3: (30, 40, 1), 4: (70, 40, 2)}
sc_metrics = sc_analyzer.calculate_space_control(positions)
sc_export = sc_analyzer.export_metrics(sc_metrics)
assert 'team_control' in sc_export
assert 'zonal_control' in sc_export

# Test action valuation export
av_analyzer = ActionValuationAnalyzer()
action = Action(1, 10, 1, ActionType.SHOT, 90, 34)
av = av_analyzer.value_action(action)
av_export = av_analyzer.export_action_value(av)
assert 'values' in av_export
assert 'context' in av_export
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All export formats valid"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Export format validation failed"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo "Phase 2 is fully operational and ready to use."
    echo ""
    echo "Available modules:"
    echo "  - metabolic_power_analyzer: Energy expenditure analysis"
    echo "  - space_control_analyzer: Voronoi territorial control"
    echo "  - action_valuation: VAEP-style action ratings"
    echo ""
    echo "Run 'python examples/phase2_demos.py' to see them in action!"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo "Please check the errors above and fix any issues."
    exit 1
fi
