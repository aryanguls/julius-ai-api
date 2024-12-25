from typing import List, Dict, Optional, Any, Literal
import requests
import json
from dataclasses import dataclass
from datetime import datetime

# Actual model names from Julius
ModelType = Literal["default", "GPT-4o", "gpt-4o-mini", "o1-mini", "claude-3-5-sonnet", "o1", "gemini", "cohere"]

@dataclass
class JuliusSubscription:
    plan: str
    status: str
    billing_cycle: str
    percent_off: int
    expires_at: int
    next_tier_name: Optional[str]

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
    id: str
    choices: List[Choice]
    created: int
    model: str

    @property
    def message(self) -> JuliusMessage:
        return self.choices[0].message if self.choices else None

class ChatCompletions:
    def __init__(self, client):
        self.client = client

    def create(self, 
           messages: List[Dict[str, str]], 
           model: ModelType = "default",
           **kwargs) -> JuliusResponse:
        """
        Create a chat completion with Julius using sequential messaging.
        
        First sends system prompt to establish conversation, then sends
        user messages one by one in order to maintain conversation flow.
        """
        try:
            # Separate system and user messages
            system_msg = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] == "user":
                    user_messages.append(msg["content"])
            
            # Start conversation with system prompt
            conversation_id = self._start_conversation()
            
            if system_msg:
                # Send system prompt first
                headers = {
                    **self.client.headers,
                    "conversation-id": conversation_id
                }
                
                system_payload = {
                    "message": {"content": system_msg},
                    "provider": model if model != "default" else "default",
                    "chat_mode": "auto",
                    "client_version": "20240130",
                    "theme": "light"
                }
                
                response = requests.post(
                    f"{self.client.base_url}/api/chat/message",
                    headers=headers,
                    json=system_payload
                )
                response.raise_for_status()
            
            # Now send each user message in sequence
            final_content = ""
            for user_msg in user_messages:
                headers = {
                    **self.client.headers,
                    "conversation-id": conversation_id
                }
                
                user_payload = {
                    "message": {"content": user_msg},
                    "provider": model if model != "default" else "default",
                    "chat_mode": "auto",
                    "client_version": "20240130",
                    "theme": "light"
                }
                
                response = requests.post(
                    f"{self.client.base_url}/api/chat/message",
                    headers=headers,
                    json=user_payload
                )
                response.raise_for_status()
                
                # Parse response chunks
                for line in response.text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if chunk.get("role") in ["assistant", ""]:
                            if chunk_content := chunk.get("content"):
                                final_content += chunk_content
                    except json.JSONDecodeError:
                        continue

            # Create final response object
            julius_message = JuliusMessage(
                role="assistant",
                content=final_content
            )
            
            choice = Choice(
                index=0,
                message=julius_message
            )
            
            return JuliusResponse(
                id=conversation_id,
                choices=[choice],
                created=int(datetime.now().timestamp()),
                model=model
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
        try:
            self.subscription = self._get_subscription()
        except Exception:
            self.subscription = None
        self.chat = type('Chat', (), {'completions': ChatCompletions(self)})()

    def _get_subscription(self) -> JuliusSubscription:
        """Get current subscription details."""
        try:
            response = requests.get(
                f"{self.base_url}/api/user/subscription",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            return JuliusSubscription(
                plan=data.get('plan', 'Free'),
                status=data.get('status', 'inactive'),
                billing_cycle=data.get('billing_cycle', ''),
                percent_off=data.get('percent_off', 0),
                expires_at=data.get('expires_at', 0),
                next_tier_name=data.get('next_tier_name')
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error getting subscription: {str(e)}")

    def set_model_preference(self, model: str):
        """Set the preferred model."""
        try:
            response = requests.patch(
                f"{self.base_url}/api/user_preferences",
                headers=self.headers,
                json={
                    "preferences": {
                        "model": model
                    }
                }
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error setting model preference: {str(e)}")