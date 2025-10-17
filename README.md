# AI Walkie-Talkie

A macOS application suite for interacting with AnythingLLM through both a menu bar interface and an interactive walkie-talkie-style terminal conversation.

## What It Does

This project provides two ways to interact with your local AnythingLLM instance:

1. **Menu Bar App** (`Menu.app`): A macOS menu bar application that gives you quick access to ask questions to AnythingLLM via a simple dialog interface
   - Ask questions through a popup dialog or **voice recording** 🎤
   - Maintain multi-turn conversations with context
   - Voice responses spoken aloud automatically
   - View and copy previous answers
   - Access debug logs

2. **Walkie-Talkie CLI** (`walkie.sh`): An interactive terminal conversation interface with text-to-speech support
   - Continuous conversation with context
   - Responses are spoken aloud using macOS text-to-speech
   - Command support: `/help`, `/exit`, `/clear`, `/history`

Both interfaces connect to AnythingLLM's OpenAI-compatible API using LangChain. **Voice input** uses OpenAI's Whisper model for speech-to-text transcription (runs locally).

## Requirements

- macOS (for menu bar integration and text-to-speech)
- Python 3.8 or higher
- [AnythingLLM](https://anythingllm.com/) running locally or accessible via network
- **ffmpeg** (required for voice recording): `brew install ffmpeg`
- [Platypus](https://sveinbjorn.org/platypus) (optional, only needed to rebuild the menu bar app)

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd ai-walkie
```

### 2. Create and activate Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install system dependencies

Voice recording requires ffmpeg:

```bash
brew install ffmpeg
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

**Note:** This includes OpenAI Whisper for voice recording features. First-time setup will download the Whisper model (~150MB for base model).

### 5. Configure environment variables

Copy the sample environment file and edit it with your settings:

```bash
cp .env.sample .env
```

Edit `.env` with your preferred editor:

```bash
nano .env  # or vim, code, etc.
```

Required configuration:

- `ANYTHINGLLM_OPENAI_BASE`: Your AnythingLLM OpenAI-compatible API endpoint (default: `http://localhost:3001/api/v1/openai`)
- `ANYTHINGLLM_API_KEY`: API key from AnythingLLM (Settings → API Keys)
- `ANYTHINGLLM_WORKSPACE_SLUG`: The workspace slug to chat with (used as the "model" parameter)

Optional configuration:

- `SYSTEM_PROMPT`: Custom system prompt for the AI assistant
- `TTS_VOICE`: Voice to use for walkie.sh text-to-speech (default: "Lee (Premium)")
  - Run `say -v ?` to see all available voices

### 6. Test the connection

Test that everything is configured correctly:

```bash
source .venv/bin/activate
python scripts/test_anythingllm.py
```

Or test with a custom question:

```bash
python scripts/test_anythingllm.py "What is the meaning of life?"
```

## Usage

### Walkie-Talkie Mode (Terminal Interface)

For an interactive conversation with text-to-speech:

```bash
source .venv/bin/activate
./walkie.sh
```

The walkie-talkie interface supports these commands:
- `/help` - Show available commands
- `/exit`, `/quit`, `/q` - Exit the conversation
- `/clear` - Clear conversation history
- `/history` - Show conversation history

### Menu Bar App

Double-click `Menu.app` to launch the menu bar application. The app will appear in your macOS menu bar.

**First run**: The app will copy `.env.sample` to `~/Library/Application Support/AnythingLLM-Menu/.env` and prompt you to configure it.

Features:
- **Ask…**: Opens a dialog to ask a question (text input)
- **🎤 Voice Ask…**: Record your question with voice and get a spoken response
- **Conversation…**: Continue a multi-turn text conversation
- **🎤 Voice Conversation…**: Continue a conversation using voice input/output
- **Clear Conversation**: Reset conversation history
- **Copy last answer**: Copies the previous answer to clipboard
- **Last: [preview]**: Opens the last answer in TextEdit
- **View Logs**: Opens the debug log in Console.app

**Voice Features**: Click any voice menu item to open Terminal. Press Enter to start recording, speak your question, then press Enter again to stop. The AI's response will be spoken aloud automatically. Terminal is used for interactive recording control and visual feedback.

📖 **Voice Setup**: See [VOICE_SETUP.md](VOICE_SETUP.md) for detailed voice recording setup instructions.

### Command Line Interface

You can also use the CLI directly:

```bash
source .venv/bin/activate
python scripts/ask_anythingllm.py "your question here"
```

Or test the menu script:

```bash
./menu.sh          # Shows menu items
./menu.sh "Ask…"   # Triggers ask dialog
```

## Project Structure

```
ai-walkie/
├── Menu.app/              # Bundled macOS menu bar application (Platypus)
├── menu.sh                # Main bash script for menu bar interface
├── walkie.sh              # Interactive walkie-talkie interface with TTS
├── scripts/
│   ├── langchain_client.py      # LangChain wrapper for AnythingLLM API
│   ├── ask_anythingllm.py       # CLI entry point for single questions
│   ├── converse.py              # Interactive conversation script
│   ├── conversation_manager.py  # Manages conversation history/context
│   ├── conversation_cli.py      # CLI for persistent conversations
│   ├── voice_recorder.py        # Voice recording and Whisper transcription
│   ├── voice_ask.py             # Voice-activated question asking
│   └── test_anythingllm.py      # Connection testing utility
├── .env.sample            # Sample environment configuration
├── requirements.txt       # Python dependencies (includes Whisper)
├── README.md              # This file
├── VOICE_SETUP.md         # Voice recording setup guide
└── WALKIE_README.md       # Walkie-talkie detailed documentation
```

## How It Works

### Architecture

- **LangChain Integration**: Uses LangChain's `ChatOpenAI` class configured with AnythingLLM's OpenAI-compatible endpoint
- **Workspace as Model**: AnythingLLM's API uses the workspace slug as the "model" parameter
- **Menu Bar**: Built with Platypus, which bundles `menu.sh` as a native macOS app
- **State Management**:
  - Menu bar app stores last answer at `~/Library/Application Support/AnythingLLM-Menu/last.txt`
  - Configuration stored at `~/Library/Application Support/AnythingLLM-Menu/.env`
  - Debug logs at `~/Library/Application Support/AnythingLLM-Menu/debug.log`

### Text-to-Speech

The walkie-talkie mode uses macOS's built-in `say` command to speak AI responses. Configure the voice in your `.env` file with the `TTS_VOICE` variable.

## Troubleshooting

### "Connection refused" errors

- Ensure AnythingLLM is running and accessible at the configured `ANYTHINGLLM_OPENAI_BASE`
- Check that the API endpoint includes `/api/v1/openai`

### "Invalid API key" errors

- Verify your API key is correct in `.env`
- Generate a new API key in AnythingLLM (Settings → API Keys)

### Menu bar app doesn't work

- Check the debug log: Click "View Logs" in the menu
- Ensure the virtual environment is set up correctly at `./.venv`
- Verify configuration at `~/Library/Application Support/AnythingLLM-Menu/.env`

### No voice output in walkie.sh

- Test your TTS voice: `say -v "Lee (Premium)" "Hello"`
- List available voices: `say -v ?`
- Update `TTS_VOICE` in your `.env` file

### Python module not found

Make sure you've activated the virtual environment:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Development

### Rebuilding the Menu Bar App

If you modify `menu.sh` and want to rebuild `Menu.app`:

1. Install [Platypus](https://sveinbjorn.org/platypus)
2. Open Platypus and configure:
   - Script: `menu.sh`
   - Interface: Status Menu
   - App Name: Menu
3. Click "Create App"

### Testing Components

Test the LangChain client directly:

```bash
source .venv/bin/activate
python scripts/test_anythingllm.py "test question"
```

Test the ask script:

```bash
source .venv/bin/activate
python scripts/ask_anythingllm.py "test question"
```

Test menu rendering:

```bash
./menu.sh
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
