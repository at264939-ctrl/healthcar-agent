#!/bin/bash

# ============================================================================
# Healthcare Agent - Professional Startup Script
# ============================================================================
# Colors for status output
# ============================================================================

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color
BOLD='\033[1m'
DIM='\033[2m'

# Status symbols
SUCCESS="✓"
WARNING="⚠"
ERROR="✗"
INFO="ℹ"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           🏥  HEALTHCARE AGENT SYSTEM                     ║"
    echo "║           AI-Powered Medical Triage & Routing             ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success")
            echo -e "${GREEN}${SUCCESS}${NC} ${message}"
            ;;
        "warning")
            echo -e "${YELLOW}${WARNING}${NC} ${message}"
            ;;
        "error")
            echo -e "${RED}${ERROR}${NC} ${message}"
            ;;
        "info")
            echo -e "${BLUE}${INFO}${NC} ${message}"
            ;;
        *)
            echo -e "${WHITE}${INFO}${NC} ${message}"
            ;;
    esac
}

check_dependency() {
    local dep=$1
    local cmd=$2
    
    if command -v $cmd &> /dev/null; then
        print_status "success" "$dep is installed ($(command -v $cmd))"
        return 0
    else
        print_status "error" "$dep is not installed"
        return 1
    fi
}

check_env_variable() {
    local var_name=$1
    local var_value="${!var_name}"
    
    if [ -n "$var_value" ] && [ "$var_value" != "your_"* ]; then
        # Mask the value for security
        local masked_value="${var_value:0:4}...${var_value: -4}"
        print_status "success" "$var_name is configured ($masked_value)"
        return 0
    else
        print_status "warning" "$var_name is not configured"
        return 1
    fi
}

# ============================================================================
# Main Script
# ============================================================================

print_header

# ============================================================================
# Step 1: Check Python Installation
# ============================================================================
print_section "📋 Checking Python Environment"

if check_dependency "Python 3" "python3"; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_status "info" "Version: $PYTHON_VERSION"
else
    print_status "error" "Python 3 is required but not installed"
    exit 1
fi

# ============================================================================
# Step 2: Check Virtual Environment
# ============================================================================
print_section "📦 Checking Virtual Environment"

if [ -d "venv" ]; then
    print_status "success" "Virtual environment found"
    source venv/bin/activate
    print_status "info" "Activated: $(which python)"
else
    print_status "warning" "Virtual environment not found"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    print_status "success" "Virtual environment created and activated"
fi

# ============================================================================
# Step 3: Check Dependencies
# ============================================================================
print_section "📚 Checking Python Dependencies"

if [ -f "requirements.txt" ]; then
    print_status "info" "Installing/verifying dependencies..."
    pip install -q -r requirements.txt
    
    if [ $? -eq 0 ]; then
        print_status "success" "All dependencies installed"
    else
        print_status "error" "Failed to install dependencies"
        exit 1
    fi
else
    print_status "error" "requirements.txt not found"
    exit 1
fi

# ============================================================================
# Step 4: Check Environment Configuration
# ============================================================================
print_section "⚙️  Checking Environment Configuration"

if [ -f ".env" ]; then
    print_status "success" ".env file found"
    source .env
else
    print_status "warning" ".env file not found"
    
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
        print_status "info" "Please edit .env and add your API keys"
        print_status "warning" "Service will start but may not function properly without valid credentials"
        source .env
    else
        print_status "error" ".env.example not found"
        exit 1
    fi
fi

# Check critical environment variables
ENV_OK=true

check_env_variable "GROQ_API_KEY" || ENV_OK=false
check_env_variable "TWILIO_ACCOUNT_SID" || ENV_OK=false
check_env_variable "TWILIO_AUTH_TOKEN" || ENV_OK=false
check_env_variable "TWILIO_PHONE_NUMBER" || ENV_OK=false

if [ "$ENV_OK" = false ]; then
    echo ""
    print_status "warning" "Some environment variables are not configured"
    print_status "info" "The service will start but some features may not work"
    echo -e "${DIM}Edit .env file to configure your API keys${NC}"
fi

# ============================================================================
# Step 5: Check Directory Structure
# ============================================================================
print_section "📁 Checking Project Structure"

REQUIRED_FILES=("app.py" "medical_database.py" "triage_analyzer.py" "emergency_notifier.py")

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_status "success" "$file exists"
    else
        print_status "error" "$file not found"
        exit 1
    fi
done

# ============================================================================
# Step 6: Create Required Directories
# ============================================================================
print_section "🗂️  Setting Up Directories"

if [ ! -d "chroma_db" ]; then
    mkdir -p chroma_db
    print_status "success" "Created chroma_db directory"
else
    print_status "info" "chroma_db directory exists"
fi

if [ ! -d "logs" ]; then
    mkdir -p logs
    print_status "success" "Created logs directory"
else
    print_status "info" "logs directory exists"
fi

# ============================================================================
# Step 7: System Health Check
# ============================================================================
print_section "🏥 System Health Check"

echo -e "${DIM}Testing component initialization...${NC}"

# Quick Python import test
python3 -c "
import sys
try:
    from medical_database import MedicalDatabase
    print('✓ Medical Database module OK')
except Exception as e:
    print(f'✗ Medical Database module ERROR: {e}')
    sys.exit(1)

try:
    from triage_analyzer import TriageAnalyzer
    print('✓ Triage Analyzer module OK')
except Exception as e:
    print(f'✗ Triage Analyzer module ERROR: {e}')
    sys.exit(1)

try:
    from emergency_notifier import EmergencyNotifier
    print('✓ Emergency Notifier module OK')
except Exception as e:
    print(f'✗ Emergency Notifier module ERROR: {e}')
    sys.exit(1)

print('All modules imported successfully')
" 2>&1 | while read line; do
    if [[ $line == ✓* ]]; then
        print_status "success" "${line#✓ }"
    elif [[ $line == ✗* ]]; then
        print_status "error" "${line#✗ }"
    else
        print_status "info" "$line"
    fi
done

# ============================================================================
# Step 8: Start Server
# ============================================================================
print_section "🚀 Starting Healthcare Agent Server"

HOST="${FLASK_HOST:-0.0.0.0}"
PORT="${FLASK_PORT:-5000}"

echo ""
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}                    SERVICE STARTING                      ${NC}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${WHITE}Server Address:${NC} http://$HOST:$PORT"
echo -e "${WHITE}Mode:${NC} Development (Debug enabled)"
echo -e "${WHITE}Time:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo -e "${DIM}Press Ctrl+C to stop the server${NC}"
echo ""

# Export environment variables for Flask
export FLASK_APP=app.py
export FLASK_ENV=development

# Start the server
python3 app.py

# ============================================================================
# Cleanup (if server stops)
# ============================================================================
print_section "🛑 Server Stopped"

print_status "info" "Healthcare Agent has been stopped"
echo -e "${CYAN}Thank you for using Healthcare Agent!${NC}"
echo ""
