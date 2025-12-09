#!/bin/bash
#
# Bootstrap Script - Clone Sense Apps from GitLab
# Run this if you have access to the actual Sense app repositories
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Sense Apps Bootstrap Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Configuration
GITLAB_BASE_URL="${GITLAB_BASE_URL:-https://gitlab.com/your-org}"
SENSE_APPS_DIR="sense-apps"

# Check if we're in the right directory
if [ ! -d "$SENSE_APPS_DIR" ]; then
    echo -e "${RED}ERROR: sense-apps directory not found${NC}"
    echo "Please run this script from the repository root"
    exit 1
fi

cd "$SENSE_APPS_DIR"

echo -e "${YELLOW}This script will clone the actual Sense app repositories from GitLab${NC}"
echo ""
echo "Repository URLs:"
echo "  Beorn:    ${GITLAB_BASE_URL}/beorn.git"
echo "  Palantir: ${GITLAB_BASE_URL}/palantir.git"
echo "  Arda:     ${GITLAB_BASE_URL}/arda.git"
echo ""

# Check if GitLab credentials are configured
if ! git config --get user.email > /dev/null; then
    echo -e "${YELLOW}Git user not configured. Please configure Git first:${NC}"
    echo "  git config --global user.name 'Your Name'"
    echo "  git config --global user.email 'your.email@example.com'"
    echo ""
fi

# Ask for confirmation
read -p "Do you want to clone the repositories? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Bootstrap cancelled"
    exit 0
fi

# ============================================
# Clone Beorn
# ============================================
echo ""
echo -e "${GREEN}Cloning Beorn...${NC}"

if [ -d "beorn-prod" ]; then
    echo "beorn-prod directory already exists, skipping..."
else
    git clone "${GITLAB_BASE_URL}/beorn.git" beorn-prod || {
        echo -e "${RED}Failed to clone Beorn${NC}"
        echo "Using stub implementation instead"
    }
fi

# ============================================
# Clone Palantir
# ============================================
echo ""
echo -e "${GREEN}Cloning Palantir...${NC}"

if [ -d "palantir-prod" ]; then
    echo "palantir-prod directory already exists, skipping..."
else
    git clone "${GITLAB_BASE_URL}/palantir.git" palantir-prod || {
        echo -e "${RED}Failed to clone Palantir${NC}"
        echo "Using stub implementation instead"
    }
fi

# ============================================
# Clone Arda
# ============================================
echo ""
echo -e "${GREEN}Cloning Arda...${NC}"

if [ -d "arda-prod" ]; then
    echo "arda-prod directory already exists, skipping..."
else
    git clone "${GITLAB_BASE_URL}/arda.git" arda-prod || {
        echo -e "${RED}Failed to clone Arda${NC}"
        echo "Using stub implementation instead"
    }
fi

# ============================================
# Setup Instructions
# ============================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Bootstrap Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ -d "beorn-prod" ] || [ -d "palantir-prod" ] || [ -d "arda-prod" ]; then
    echo -e "${YELLOW}Repositories cloned successfully!${NC}"
    echo ""
    echo "Next steps for each app:"
    echo ""
    echo "1. Navigate to the app directory:"
    echo "   cd beorn-prod  # or palantir-prod or arda-prod"
    echo ""
    echo "2. Create virtual environment:"
    echo "   python3.11 -m venv venv"
    echo "   source venv/bin/activate"
    echo ""
    echo "3. Install dependencies:"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "4. Initialize submodules (if any):"
    echo "   git submodule update --init --recursive"
    echo ""
    echo "5. Install pre-commit hooks:"
    echo "   pre-commit install"
    echo ""
    echo "6. Copy and configure .env:"
    echo "   cp .env.example .env"
    echo "   vim .env  # Add your credentials"
    echo ""
    echo "7. Run the app:"
    echo "   # For Flask apps (Beorn, Palantir):"
    echo "   export FLASK_APP=app.py"
    echo "   export FLASK_ENV=development"
    echo "   flask run --port 5001"
    echo ""
    echo "   # For FastAPI apps (Arda):"
    echo "   uvicorn app:app --host 0.0.0.0 --port 5003 --reload"
    echo ""
else
    echo -e "${YELLOW}No repositories were cloned.${NC}"
    echo ""
    echo "Using stub implementations in:"
    echo "  - sense-apps/beorn/"
    echo "  - sense-apps/palantir/"
    echo "  - sense-apps/arda/"
    echo ""
    echo "These stub apps have full OTel instrumentation and can be used for testing."
fi

echo ""
echo -e "${GREEN}For more information, see sense-apps/README.md${NC}"
echo ""