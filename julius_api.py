from typing import List, Dict, Optional, Any, Literal, BinaryIO
import requests
import json
from dataclasses import dataclass
from datetime import datetime
import os
import mimetypes

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

    def get_signed_url(self, filename: str, mime_type: str) -> Dict:
        """Get signed URL for file upload."""
        try:
            payload = {
                "filename": filename,
                "mimeType": mime_type
            }
            
            response = requests.post(
                f"{self.client.base_url}/files/signed_url",
                headers=self.client.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            if 'signedUrl' not in data:  # Changed from 'url' to 'signedUrl'
                raise Exception(f"No signed URL in response: {data}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error getting signed URL: {str(e)}")
        except Exception as e:
            raise Exception(f"Error in signed URL request: {str(e)}")

    def preprocess_file(self, filename: str) -> Dict:
        """Preprocess uploaded file."""
        try:
            payload = {
                "filename": filename,
                "conversationId": None,
                "analyze": True
            }
            
            response = requests.post(
                f"{self.client.base_url}/files/preprocess_file",
                headers=self.client.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
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
                
            filename = os.path.basename(file_path)
            mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

            # Get signed URL with better error handling
            try:
                signed_url_response = self.get_signed_url(filename, mime_type)
                upload_url = signed_url_response.get('signedUrl')  # Changed from 'url' to 'signedUrl'
                
                if not upload_url:
                    raise Exception("No signed URL in response")
                    
            except Exception as e:
                raise Exception(f"Failed to get signed URL: {str(e)}")

            # Upload file to signed URL
            try:
                with open(file_path, 'rb') as f:
                    upload_response = requests.put(
                        upload_url, 
                        data=f, 
                        headers={'Content-Type': mime_type}
                    )
                    upload_response.raise_for_status()
            except Exception as e:
                raise Exception(f"Failed to upload file: {str(e)}")

            # Preprocess file
            try:
                self.preprocess_file(filename)
            except Exception as e:
                raise Exception(f"Failed to preprocess file: {str(e)}")
            
            return filename

        except Exception as e:
            print(f"Debug - Full error: {str(e)}")  # Added debug print
            raise Exception(f"Error in file upload process: {str(e)}")

class ChatCompletions:
    def __init__(self, client):
        self.client = client

    def create(self, 
            messages: List[Dict[str, Any]], 
            model: ModelType = "default",
            **kwargs) -> JuliusResponse:
        """
        Create a chat completion with Julius using sequential messaging.
        
        Args:
            messages: List of message dictionaries with 'role', 'content', and optionally 'file_path'
            model: Model to use
            **kwargs: Additional arguments
        """
        try:
            # 1. Start conversation first
            conversation_id = self._start_conversation(model)
            
            # Separate messages
            system_msg = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] == "user":
                    user_messages.append(msg)
            
            # 2. Send system message if present
            if system_msg:
                headers = {
                    **self.client.headers,
                    "conversation-id": conversation_id
                }
                
                system_payload = {
                    "message": {"content": system_msg},
                    "provider": model if model != "default" else "default",
                    "chat_mode": "auto",
                    "client_version": "20240130",
                    "theme": "light",
                    "dataframe_format": "json"
                }
                
                response = requests.post(
                    f"{self.client.base_url}/api/chat/message",
                    headers=headers,
                    json=system_payload,
                    stream=True
                )
                response.raise_for_status()
                
                # Clear any system message response
                for line in response.iter_lines():
                    continue
            
            # 3. Send user messages sequentially
            final_content = ""
            for user_msg in user_messages:
                headers = {
                    **self.client.headers,
                    "conversation-id": conversation_id
                }
                
                # Handle file if present
                new_attachments = {}
                if "file_path" in user_msg:
                    # Upload file
                    filename = self.client.files.upload(user_msg["file_path"])
                    
                    # Register as source
                    self._register_file_source(conversation_id, filename)
                    
                    # Add to attachments
                    new_attachments = {
                        filename: {
                            "name": filename,
                            "isUploading": False
                        }
                    }

                # Prepare message payload
                user_payload = {
                    "message": {"content": user_msg["content"]},
                    "provider": model if model != "default" else "default",
                    "chat_mode": "auto",
                    "client_version": "20240130",
                    "theme": "light",
                    "dataframe_format": "json",
                    "new_attachments": new_attachments,
                    "new_images": []
                }
                
                # Send message with streaming
                response = requests.post(
                    f"{self.client.base_url}/api/chat/message",
                    headers=headers,
                    json=user_payload,
                    stream=True
                )
                response.raise_for_status()
                
                # Process streaming response
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

            # Create final response
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

    def _register_file_source(self, conversation_id: str, filename: str):
        """Register a file as a source for the conversation."""
        try:
            headers = {
                **self.client.headers,
                "conversation-id": conversation_id
            }
            
            response = requests.post(
                f"{self.client.base_url}/api/chat/sources",
                headers=headers,
                json={"file_name": filename}
            )
            response.raise_for_status()
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