from typing import List, Dict, Optional, Any
import requests
import json
from dataclasses import dataclass
from datetime import datetime

@dataclass
class JuliusMessage:
    role: str
    content: str

@dataclass
class Choice:
    index: int
    message: JuliusMessage
    finish_reason: str = "stop"

@dataclass
class JuliusResponse:
    id: str  # conversation_id
    choices: List[Choice]
    created: int  # timestamp
    model: str = "julius-default"
    
    @property
    def message(self) -> JuliusMessage:
        """Helper to get first message, similar to OpenAI's API."""
        return self.choices[0].message if self.choices else None

class ChatCompletions:
    def __init__(self, client):
        self.client = client

    def create(self, messages: List[Dict[str, str]], **kwargs) -> JuliusResponse:
        """Create a chat completion with Julius."""
        # Start conversation
        conversation_id = self._start_conversation()
        
        # Get the last user message
        last_message = messages[-1]["content"]

        # Send chat request
        try:
            headers = {
                **self.client.headers,
                "conversation-id": conversation_id
            }
            
            payload = {
                "message": {"content": last_message},
                "provider": "default",
                "chat_mode": "auto",
                "client_version": "20240130",
                "theme": "light"
            }

            response = requests.post(
                f"{self.client.base_url}/api/chat/message",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            # Parse chunks and build final response
            content = ""
            chunks = []
            
            for line in response.text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    chunks.append(chunk)
                    if chunk.get("role") in ["assistant", ""]:
                        if chunk_content := chunk.get("content"):
                            content += chunk_content
                except json.JSONDecodeError:
                    continue

            # Create response object
            julius_message = JuliusMessage(
                role="assistant",
                content=content
            )
            
            choice = Choice(
                index=0,
                message=julius_message
            )

            return JuliusResponse(
                id=conversation_id,
                choices=[choice],
                created=int(datetime.now().timestamp())
            )

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error in chat completion: {str(e)}")

    def _start_conversation(self) -> str:
        """Start a new Julius conversation."""
        try:
            response = requests.post(
                f"{self.client.base_url}/api/chat/start",
                headers=self.client.headers,
                json={}
            )
            response.raise_for_status()
            data = json.loads(response.text)
            return data.get("id", "")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error starting conversation: {str(e)}")

class Julius:
    def __init__(self, api_key: str):
        """Initialize Julius API with your API key."""
        self.api_key = api_key
        self.base_url = "https://api.julius.ai"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Origin": "https://julius.ai"
        }
        self.chat = type('Chat', (), {'completions': ChatCompletions(self)})()