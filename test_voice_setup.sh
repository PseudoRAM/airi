#!/usr/bin/env bash
# test_voice_setup.sh - Test voice recording setup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "   Voice Recording Setup Test"
echo "=========================================="
echo ""

# Check virtual environment
echo "✓ Checking virtual environment..."
if [[ ! -d .venv ]]; then
    echo "❌ Virtual environment not found at .venv"
    echo "   Run: python3 -m venv .venv"
    exit 1
fi
echo "  ✓ Virtual environment found"

# Activate virtual environment
if [[ -f .venv/bin/activate ]]; then
    source .venv/bin/activate
else
    echo "❌ Cannot activate virtual environment"
    exit 1
fi

# Check Python version
echo ""
echo "✓ Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "  ✓ Python $PYTHON_VERSION"

# Check required packages
echo ""
echo "✓ Checking required packages..."

check_package() {
    if python -c "import $1" 2>/dev/null; then
        echo "  ✓ $1 installed"
        return 0
    else
        echo "  ❌ $1 NOT installed"
        return 1
    fi
}

ALL_INSTALLED=true

check_package "whisper" || ALL_INSTALLED=false
check_package "pyaudio" || ALL_INSTALLED=false
check_package "langchain" || ALL_INSTALLED=false
check_package "langchain_openai" || ALL_INSTALLED=false
check_package "dotenv" || ALL_INSTALLED=false

if [ "$ALL_INSTALLED" = false ]; then
    echo ""
    echo "❌ Missing packages. Install with:"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check for ffmpeg
echo ""
echo "✓ Checking ffmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n 1 | awk '{print $3}')
    echo "  ✓ ffmpeg $FFMPEG_VERSION installed"
else
    echo "  ❌ ffmpeg NOT installed"
    echo "     Whisper requires ffmpeg to process audio"
    echo "     Install with: brew install ffmpeg"
    ALL_INSTALLED=false
fi

# Check for configuration
echo ""
echo "✓ Checking configuration..."
CONFIG_FILE="$HOME/Library/Application Support/AnythingLLM-Menu/.env"
if [[ -f "$CONFIG_FILE" ]] || [[ -f .env ]]; then
    echo "  ✓ Configuration file found"
else
    echo "  ⚠️  No configuration file found"
    echo "     Create .env from .env.sample and configure it"
fi

# Check scripts exist
echo ""
echo "✓ Checking voice scripts..."
if [[ -f scripts/voice_recorder.py ]]; then
    echo "  ✓ voice_recorder.py found"
else
    echo "  ❌ voice_recorder.py NOT found"
    exit 1
fi

if [[ -f scripts/voice_ask.py ]]; then
    echo "  ✓ voice_ask.py found"
else
    echo "  ❌ voice_ask.py NOT found"
    exit 1
fi

# Check microphone permissions hint
echo ""
echo "✓ Microphone permissions..."
echo "  ℹ️  Ensure microphone access is granted for Terminal/Python"
echo "     Settings → Privacy & Security → Microphone"

# Test voice import
echo ""
echo "✓ Testing voice module imports..."
if python -c "from scripts.voice_recorder import VoiceRecorder; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo "  ✓ Voice modules load successfully"
else
    echo "  ❌ Error loading voice modules"
    python -c "from scripts.voice_recorder import VoiceRecorder" 2>&1
    exit 1
fi

# Summary
echo ""
echo "=========================================="
echo "✅ Setup verification complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Grant microphone permissions (System Settings)"
echo "2. Test voice recording:"
echo "   python scripts/voice_recorder.py"
echo ""
echo "3. Test voice with AnythingLLM:"
echo "   python scripts/voice_ask.py"
echo ""
echo "4. Use from menu bar:"
echo "   Open Menu.app and select '🎤 Voice Ask…'"
echo ""
echo "See VOICE_SETUP.md for detailed documentation."
echo ""

