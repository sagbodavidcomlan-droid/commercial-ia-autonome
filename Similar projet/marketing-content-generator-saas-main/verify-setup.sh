#!/bin/bash

# Marketing Content Generator - Setup Verification Script
# This script checks if your environment is ready to run the application

set -e

echo "🔍 Marketing Content Generator - Setup Verification"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is missing"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is missing"
        return 1
    fi
}

# Track errors
ERRORS=0

echo "1️⃣  Checking Required Software"
echo "--------------------------------"
check_command docker || ERRORS=$((ERRORS+1))
check_command docker-compose || check_command "docker compose" || ERRORS=$((ERRORS+1))
echo ""

echo "2️⃣  Checking Project Structure"
echo "--------------------------------"
check_file ".env" || echo -e "${YELLOW}⚠${NC}  .env file missing - run 'cp .env.example .env' and configure it"
check_file "docker-compose.yml" || ERRORS=$((ERRORS+1))
check_dir "backend" || ERRORS=$((ERRORS+1))
check_dir "frontend" || ERRORS=$((ERRORS+1))
check_file "backend/requirements.txt" || ERRORS=$((ERRORS+1))
check_file "frontend/package.json" || ERRORS=$((ERRORS+1))
echo ""

echo "3️⃣  Checking Environment Configuration"
echo "----------------------------------------"
if [ -f ".env" ]; then
    if grep -q "your-secret-key" .env || grep -q "your-anthropic-api-key" .env; then
        echo -e "${RED}✗${NC} .env file needs to be configured with real values"
        echo "   - Generate SECRET_KEY: openssl rand -hex 32"
        echo "   - Get ANTHROPIC_API_KEY from: https://console.anthropic.com/"
        ERRORS=$((ERRORS+1))
    else
        echo -e "${GREEN}✓${NC} .env file is configured"
    fi
else
    echo -e "${YELLOW}⚠${NC}  .env file not found"
    echo "   Run: cp .env.example .env"
    echo "   Then edit .env with your API keys"
fi
echo ""

echo "4️⃣  Docker Status"
echo "--------------------------------"
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker is running"
else
    echo -e "${RED}✗${NC} Docker is not running"
    echo "   Please start Docker Desktop"
    ERRORS=$((ERRORS+1))
fi
echo ""

echo "5️⃣  Port Availability"
echo "--------------------------------"
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}✗${NC} Port $1 is already in use"
        echo "   Process using it: $(lsof -Pi :$1 -sTCP:LISTEN | tail -n +2)"
        return 1
    else
        echo -e "${GREEN}✓${NC} Port $1 is available"
        return 0
    fi
}

check_port 3000 || ERRORS=$((ERRORS+1))
check_port 8000 || ERRORS=$((ERRORS+1))
check_port 5432 || ERRORS=$((ERRORS+1))
echo ""

echo "=================================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! You're ready to start.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. If .env is not configured, edit it with your API keys"
    echo "  2. Run: make dev"
    echo "  3. Open: http://localhost:3000"
    echo ""
else
    echo -e "${RED}❌ Found $ERRORS issue(s). Please fix them before starting.${NC}"
    echo ""
    echo "Need help? Check:"
    echo "  - README.md for detailed documentation"
    echo "  - QUICKSTART.md for setup instructions"
    echo ""
    exit 1
fi
