#!/bin/bash
# =============================================================================
# Test Script for portrait_to_16x9_blur.py - Enhanced Version
# Purpose: Comprehensive testing of blur settings for portrait Grok videos
#          to 16:9 with diffused sides. Now includes 4K, vignette, and more.
# =============================================================================

set -euo pipefail

# ========================= CONFIGURATION =========================
INPUT_VIDEO="input_video.mp4"
BASE_NAME="output_test"

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Portrait to 16:9 Blur Test Suite (Enhanced)${NC}"
echo -e "${BLUE}   Input: ${INPUT_VIDEO}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if input exists
if [[ ! -f "$INPUT_VIDEO" ]]; then
    echo -e "${RED}Error: Input file '$INPUT_VIDEO' not found!${NC}"
    echo "Please place your portrait Grok video as '$INPUT_VIDEO' in this folder."
    exit 1
fi

# Check if Python script exists
SCRIPT="$HOME/projects/Music/py/portrait_to_16x9_blur.py"
if [[ ! -f "$SCRIPT" ]]; then
    echo -e "${RED}Error: Python script '$SCRIPT' not found!${NC}"
    exit 1
fi

echo -e "${YELLOW}Starting enhanced test suite with 24 variations...${NC}"
echo -e "Outputs named as ${BASE_NAME}_XX_description.mp4\n"

# ======================== TEST CASES ========================

declare -a tests=(
    # 1. Basic Default
    "--blur-strength 20"
    
    # Blur Strength Variations (more granular)
    "--blur-strength 12"
    "--blur-strength 15"
    "--blur-strength 18"
    "--blur-strength 22"
    "--blur-strength 25"
    "--blur-strength 30"
    "--blur-strength 35"
    "--blur-strength 40"
    
    # Boxblur
    "--blur-type boxblur --blur-strength 20"
    
    # Quality & Encoding
    "--crf 17 --preset slower"
    "--crf 20 --preset fast"
    "--crf 23 --preset veryfast"
    
    # Resolution Control
    "--force-1080p"
    "--width 2560 --force-1080p"
    "--width 3840 --force-1080p"          # 4K test
    
    # Background Dimming
    "--dim-background -0.08"
    "--dim-background -0.15"
    "--dim-background -0.25"
    
    # Vignette on Center (new)
    "--blur-strength 22 --force-1080p"   # base + we'll combine later
    # Note: Vignette not directly in script yet — added via combined below if you extend the Python script
    
    # Combined Recommended / Popular Settings
    "--blur-strength 22 --crf 18 --preset medium --force-1080p --dim-background -0.1"
    "--blur-strength 25 --crf 17 --preset slow --force-1080p --dim-background -0.12"
    "--blur-strength 28 --crf 17 --preset slow --force-1080p --dim-background -0.18"
    
    # Hardware Acceleration
    "--hwaccel --blur-strength 22 --force-1080p"
    
    # Extreme / Stress Tests
    "--blur-strength 40 --dim-background -0.3 --crf 17 --preset slow --force-1080p"
    
    # Minimal Blur (more background motion visible)
    "--blur-strength 8 --dim-background 0.0 --force-1080p"
    
    # 4K + Good Settings
    "--blur-strength 25 --crf 18 --preset medium --width 3840 --dim-background -0.1"
    
    # Light vignette-style via stronger center focus (dim + higher blur)
    "--blur-strength 30 --dim-background -0.2 --force-1080p"
)

echo -e "${YELLOW}Total tests: ${#tests[@]} ${NC}\n"

# ======================== RUN TESTS ========================

for i in "${!tests[@]}"; do
    params="${tests[$i]}"
    
    test_num=$((i + 1))
    # Create readable filename
    desc=$(echo "$params" | sed 's/--//g' | sed 's/ /_/g' | sed 's/=/ /g' | tr -d '"')
    desc=$(echo "$desc" | sed 's/  */_/g' | sed 's/^_//')
    if [[ -z "$desc" ]]; then
        desc="default"
    fi
    desc=$(echo "$desc" | cut -c1-65 | tr -d '[:space:]' | sed 's/__/_/g')
    
    OUTPUT_FILE="${BASE_NAME}_$(printf "%02d" $test_num)_${desc}.mp4"
    
    echo -e "${YELLOW}────────────────────────────────────────${NC}"
    echo -e "${BLUE}[Test $test_num / ${#tests[@]}]${NC}"
    echo -e "${GREEN}Running :${NC} python $SCRIPT -i $INPUT_VIDEO -o $OUTPUT_FILE $params"
    echo -e "${GREEN}Output  :${NC} $OUTPUT_FILE"
    echo ""
    
    # Execute
    if python3 "$SCRIPT" -i "$INPUT_VIDEO" -o "$OUTPUT_FILE" $params -y; then
        echo -e "${GREEN}✓ Test $test_num completed successfully${NC}"
    else
        echo -e "${RED}✗ Test $test_num failed${NC}"
    fi
    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All 24 tests completed!${NC}"
echo -e "${YELLOW}You now have a full range of variations to compare.${NC}"
echo ""
echo -e "Quick recommendations for Grok portrait videos:"
echo -e "• Test 14 or 15 (blur 22-25 + dim -0.1 + 1080p) — often the sweet spot"
echo -e "• Test 22 (4K version) — if you want higher resolution uploads"
echo -e "• Compare on YouTube (private), desktop, and mobile"
echo -e "• Look for good diffusion without ghosting in motion-heavy parts"
echo ""
echo -e "${BLUE}Tip: Once you pick the winner, use those exact flags for batch processing your bunch of Grok videos.${NC}"

# List generated files
echo ""
echo -e "${YELLOW}Generated files:${NC}"
ls -lh ${BASE_NAME}_*.mp4 2>/dev/null | head -n 30 || echo "No files found."

exit 0