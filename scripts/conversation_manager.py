# scripts/conversation_manager.py
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


# Load environment variables from config file
# Try the persistent location first, then fallback to project root
config_file = Path.home() / "Library" / "Application Support" / "AnythingLLM-Menu" / ".env"
if config_file.exists():
    load_dotenv(config_file)
else:
    # Fallback to project root .env for development
    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / ".env")

OPENAI_BASE = os.getenv("ANYTHINGLLM_OPENAI_BASE", "http://localhost:3001/api/v1/openai")
API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "")
WORKSPACE_SLUG = os.getenv("ANYTHINGLLM_WORKSPACE_SLUG", "local")


class ConversationManager:
    """Manages multi-turn conversations with AnythingLLM, including history and logging."""

    def __init__(self, system_prompt: Optional[str] = None, log_path: Optional[str] = None):
        """
        Initialize the conversation manager.

        Args:
            system_prompt: Optional system prompt to set conversation context
            log_path: Path to conversation log file. Defaults to ~/Library/Application Support/AnythingLLM-Menu/conversation.log
        """
        self.llm = ChatOpenAI(
            openai_api_key=API_KEY,
            openai_api_base=OPENAI_BASE,
            model=WORKSPACE_SLUG,
            temperature=0.7,
        )

        self.system_prompt = system_prompt or "You are a helpful, concise assistant."
        self.conversation_history: List[Tuple[str, str]] = []

        # Set up logging
        if log_path is None:
            state_dir = os.path.expanduser("~/Library/Application Support/AnythingLLM-Menu")
            os.makedirs(state_dir, exist_ok=True)
            log_path = os.path.join(state_dir, "conversation.log")

        self.log_path = log_path
        self._log(f"=== New conversation session started ===")

    def _log(self, message: str) -> None:
        """Write a timestamped message to the log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def _build_messages(self, user_message: str) -> List[Tuple[str, str]]:
        """Build the full message list including system, history, and new user message."""
        messages = [("system", self.system_prompt)]

        # Add conversation history
        for role, content in self.conversation_history:
            messages.append((role, content))

        # Add new user message
        messages.append(("user", user_message))

        return messages

    def ask(self, user_message: str) -> str:
        """
        Send a message and get a response, maintaining conversation context.

        Args:
            user_message: The user's message

        Returns:
            The assistant's response
        """
        # Log user message
        self._log(f"USER: {user_message}")

        # Build full message history
        messages = self._build_messages(user_message)

        # Get response from LLM
        response = self.llm.invoke(messages)
        assistant_message = (response.content or "").strip()

        # Add to conversation history
        self.conversation_history.append(("user", user_message))
        self.conversation_history.append(("assistant", assistant_message))

        # Log assistant response
        self._log(f"ASSISTANT: {assistant_message}")

        return assistant_message

    def clear_history(self) -> None:
        """Clear the conversation history (keeping system prompt)."""
        self.conversation_history = []
        self._log("=== Conversation history cleared ===")

    def get_history(self) -> List[Tuple[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history.copy()

    def save_conversation(self, filepath: str) -> None:
        """
        Save the current conversation to a text file.

        Args:
            filepath: Path where to save the conversation
        """
        with open(filepath, "w") as f:
            f.write(f"System: {self.system_prompt}\n")
            f.write("=" * 80 + "\n\n")

            for role, content in self.conversation_history:
                f.write(f"{role.upper()}: {content}\n\n")

        self._log(f"=== Conversation saved to {filepath} ===")
