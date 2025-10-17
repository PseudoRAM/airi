# AI Walkie-Talkie

A conversational interface to AnythingLLM with text-to-speech capabilities.

## Features

- **Multi-turn conversations** - Maintains conversation context across messages
- **Text-to-speech** - Speaks responses using macOS `say` command with "Lee (Premium)" voice
- **Conversation logging** - All conversations logged with timestamps to file
- **Interactive commands** - Built-in commands for managing conversation history

## Quick Start

1. **Install dependencies** (if not already done):
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure settings** (if not already done):
   - Copy `.env.sample` to `.env`
   - Set your AnythingLLM API key and workspace slug

3. **Start the walkie-talkie**:
   ```bash
   ./walkie.sh
   ```

## Usage

Once started, you can:
- Type messages and press Enter to chat with the AI
- Hear responses spoken aloud in the "Lee (Premium)" voice
- Use special commands (see below)

### Commands

- `/exit`, `/quit`, `/q` - Exit the conversation
- `/clear` - Clear conversation history (start fresh)
- `/history` - Display the full conversation history
- `/save [filepath]` - Save conversation to a file (defaults to timestamped file in `~/Library/Application Support/AnythingLLM-Menu/`)
- `/help` - Show available commands

## Conversation Logs

All conversations are automatically logged to:
```
~/Library/Application Support/AnythingLLM-Menu/conversation.log
```

Log format:
```
[2025-10-17 11:30:00] === New conversation session started ===
[2025-10-17 11:30:05] USER: What is Python?
[2025-10-17 11:30:06] ASSISTANT: Python is a high-level programming language...
[2025-10-17 11:30:15] USER: Tell me more
[2025-10-17 11:30:16] ASSISTANT: Python was created by Guido van Rossum...
```

## Configuration

### Custom Voice

To use a different voice, set the `TTS_VOICE` environment variable in your `.env` file:
```bash
TTS_VOICE="Samantha"
```

To see available voices:
```bash
say -v ?
```

### System Prompt

Customize the AI's behavior by setting `SYSTEM_PROMPT` in your `.env`:
```bash
SYSTEM_PROMPT="You are a helpful assistant who speaks like a pirate."
```

## Python-Only Mode (No TTS)

If you want to use the conversation interface without text-to-speech:
```bash
source .venv/bin/activate
python scripts/converse.py
```

## Architecture

- **`scripts/conversation_manager.py`** - Manages conversation state and history
- **`scripts/converse.py`** - Interactive CLI interface
- **`walkie.sh`** - Bash wrapper that adds text-to-speech functionality

## Troubleshooting

**No sound?**
- Check your system volume
- Verify the voice is installed: `say -v "Lee (Premium)" "test"`
- Try a different voice by setting `TTS_VOICE`

**Can't connect to AnythingLLM?**
- Verify AnythingLLM is running
- Check your `.env` configuration
- Test connection: `python scripts/test_anythingllm.py`

**Python errors?**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
