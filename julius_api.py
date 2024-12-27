# julius_api.py

from typing import List, Dict, Optional, Any, Literal, BinaryIO
import requests
import json
from dataclasses import dataclass
from datetime import datetime
import os
import mimetypes
import time

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

class Files:
    def __init__(self, client):
        self.client = client

    def _normalize_filename(self, filename: str) -> str:
        """Normalize filename to match server's format."""
        return ' '.join(word for word in filename.split() if word)

    def get_signed_url(self, filename: str, mime_type: str) -> Dict:
        """Get signed URL for file upload."""
        try:
            normalized_filename = self._normalize_filename(filename)
            payload = {
                "filename": normalized_filename,
                "mimeType": mime_type
            }
            
            response = requests.post(
                f"{self.client.base_url}/files/signed_url",
                headers=self.client.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            if 'signedUrl' not in data:
                raise Exception(f"No signed URL in response: {data}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error getting signed URL: {str(e)}")
        except Exception as e:
            raise Exception(f"Error in signed URL request: {str(e)}")

    def preprocess_file(self, filename: str) -> Dict:
        """Preprocess uploaded file with response validation."""
        try:
            normalized_filename = self._normalize_filename(filename)
            payload = {
                "filename": normalized_filename,
                "conversationId": None,
                "analyze": True
            }
            
            response = requests.post(
                f"{self.client.base_url}/files/preprocess_file",
                headers=self.client.headers,
                json=payload
            )
            
            response_data = response.json()
            
            if not response_data.get('success'):
                raise Exception("Preprocess response indicates failure")
                
            if not response_data.get('res', {}).get('success'):
                raise Exception("Preprocess result indicates failure")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error preprocessing file: {str(e)}")

    def list_files(self) -> List[Dict]:
        """List all uploaded files."""
        try:
            response = requests.get(
                f"{self.client.base_url}/hub/v2/list_hub_files",
                headers=self.client.headers
            )
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data.get('files'), list):
                raise Exception(f"Invalid response from list files endpoint: {data}")
                
            return data.get('files', [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error listing files: {str(e)}")

    def upload(self, file_path: str) -> str:
        """Upload a file to Julius and return filename."""
        try:
            if not os.path.exists(file_path):
                raise Exception(f"File not found: {file_path}")
                
            original_filename = os.path.basename(file_path)
            normalized_filename = self._normalize_filename(original_filename)
            mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

            signed_url_response = self.get_signed_url(normalized_filename, mime_type)
            upload_url = signed_url_response.get('signedUrl')
            
            if not upload_url:
                raise Exception("No signed URL in response")

            with open(file_path, 'rb') as f:
                upload_response = requests.put(
                    upload_url, 
                    data=f, 
                    headers={'Content-Type': mime_type}
                )
                upload_response.raise_for_status()

            preprocess_response = self.preprocess_file(normalized_filename)
            if not preprocess_response.get('success'):
                raise Exception("File preprocessing failed")
                
            return normalized_filename

        except Exception as e:
            raise Exception(f"Error in file upload process: {str(e)}")

class ChatCompletions:
    def __init__(self, client):
        self.client = client

    def _send_message(self, conversation_id: str, message: Dict[str, Any], model: str, current_reasoning_state: bool):
        """Send a message with support for multiple file attachments."""
        try:
            headers = {
                **self.client.headers,
                "conversation-id": conversation_id
            }

            new_attachments = {}
            if "file_paths" in message:  # Changed from file_path to file_paths
                for file_path in message["file_paths"]:  # Handle multiple files
                    filename = self.client.files.upload(file_path)
                    time.sleep(2)
                    register_response = self._register_file_source(conversation_id, filename)
                    new_attachments[filename] = {
                        "name": filename,
                        "isUploading": False,
                        "percentComplete": 100  # Added as seen in the request
                    }

            payload = {
                "message": {"content": message["content"]},
                "provider": model if model != "default" else "default",
                "chat_mode": "auto",
                "client_version": "20240130",
                "theme": "light",
                "dataframe_format": "json",
                "new_attachments": new_attachments,
                "new_images": [],
                "selectedModels": None  # Added as seen in the request
            }

            if current_reasoning_state:
                payload["advanced_reasoning"] = True

            response = requests.post(
                f"{self.client.base_url}/api/chat/message",
                headers=headers,
                json=payload,
                stream=True
            )
            
            response.raise_for_status()
            return response
            
        except Exception as e:
            raise Exception(f"Error in send_message: {str(e)}")

    def _register_file_source(self, conversation_id: str, filename: str):
        """Register a file as a source for the conversation."""
        try:
            headers = {
                **self.client.headers,
                "conversation-id": conversation_id
            }
            
            payload = {"file_name": filename}
            
            response = requests.post(
                f"{self.client.base_url}/api/chat/sources",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to register file source: {response.text}")
                
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to register file source: {str(e)}")

    def _start_conversation(self, model: str) -> str:
        """Start a new conversation with model preference."""
        try:
            payload = {
                "provider": model if model != "default" else "default",
                "server_type": "CPU",
                "template_id": None,
                "chat_type": None,
                "conversation_plan": None,
                "tool_preferences": {
                    "model": model if model != "default" else None
                }
            }
            
            response = requests.post(
                f"{self.client.base_url}/api/chat/start",
                headers=self.client.headers,
                json=payload
            )
            response.raise_for_status()
            data = json.loads(response.text)
            return data.get("id", "")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error starting conversation: {str(e)}")

    def create(self, messages: List[Dict[str, Any]], model: ModelType = "default", **kwargs) -> JuliusResponse:
        """Create a chat completion."""
        try:
            conversation_id = self._start_conversation(model)
            current_reasoning_state = False
            system_msg = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg
                    if "advanced_reasoning" in msg:
                        current_reasoning_state = msg["advanced_reasoning"]
                        if current_reasoning_state:
                            self.client.set_advanced_reasoning(True)
                elif msg["role"] == "user":
                    user_messages.append(msg)
            
            if system_msg:
                response = self._send_message(conversation_id, system_msg, model, current_reasoning_state)
                for line in response.iter_lines():
                    continue
            
            final_content = ""
            for user_msg in user_messages:
                if "advanced_reasoning" in user_msg:
                    current_reasoning_state = user_msg["advanced_reasoning"]
                    if current_reasoning_state:
                        self.client.set_advanced_reasoning(True)
                    else:
                        self.client.set_advanced_reasoning(False)
                
                response = self._send_message(conversation_id, user_msg, model, current_reasoning_state)
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if chunk.get("role") in ["assistant", ""]:
                            if chunk_content := chunk.get("content", ""):
                                final_content += chunk_content
                    except json.JSONDecodeError:
                        continue

            return JuliusResponse(
                id=conversation_id,
                choices=[Choice(
                    index=0,
                    message=JuliusMessage(
                        role="assistant",
                        content=final_content
                    )
                )],
                created=int(datetime.now().timestamp()),
                model=model
            )

        except Exception as e:
            raise Exception(f"Error in chat completion: {str(e)}")

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
        self.files = Files(self)
        try:
            self.subscription = self._get_subscription()
        except Exception:
            self.subscription = None
        self.chat = type('Chat', (), {'completions': ChatCompletions(self)})()

    def set_advanced_reasoning(self, enabled: bool = True):
        """Set advanced reasoning mode preference."""
        try:
            response = requests.patch(
                f"{self.base_url}/api/user_preferences",
                headers=self.headers,
                json={
                    "preferences": {
                        "advanced_reasoning": enabled
                    }
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to set advanced reasoning: {str(e)}")

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