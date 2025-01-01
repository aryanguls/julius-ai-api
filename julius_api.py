# julius_api.py

from typing import List, Dict, Optional, Any, Literal, BinaryIO
import requests
import json
from dataclasses import dataclass
from datetime import datetime
import os
import mimetypes
import time
from PIL import Image
from io import BytesIO
import sys

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
        self.code_counter = 0  # Global counter for code files

    def _save_code_and_output(self, code: str, outputs: list) -> tuple[str, str]:
        """Save code and its corresponding outputs to separate files and return their filenames."""
        folder_path = "./outputs"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
                
        self.code_counter += 1
        
        # Save code file - code already comes with python key wrapping
        code_filename = f"outputs/generated_code_{self.code_counter}.txt"
        with open(code_filename, 'w') as f:
            f.write(code)  # Write the code as-is since it's already wrapped
        
        # Process and deduplicate outputs
        processed_outputs = []
        seen_outputs = set()
        for output in outputs:
            # Convert output to string for deduplication
            output_str = json.dumps(output) if isinstance(output, dict) else str(output)
            if output_str not in seen_outputs:
                seen_outputs.add(output_str)
                # Only include actual outputs, skip file saving messages
                if not any(skip in output_str for skip in ['Saved image as', 'Error saving']):
                    processed_outputs.append(output)
        
        # Save output file
        output_filename = f"outputs/generated_output_{self.code_counter}.txt"
        with open(output_filename, 'w') as f:
            f.write(json.dumps({"output": processed_outputs}, indent=2))
                
        return code_filename, output_filename
    
    def _cleanup_outputs_directory(self):
        """Clean up the outputs directory by removing and recreating it."""
        import shutil
        output_dir = "./outputs"
        
        # Remove the directory and its contents if it exists
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
            except Exception as e:
                raise Exception(f"Failed to clean outputs directory: {str(e)}")
        
        # Create fresh outputs directory
        try:
            os.makedirs(output_dir)
        except Exception as e:
            raise Exception(f"Failed to create outputs directory: {str(e)}")
        
        # Reset the code counter since we're starting fresh
        self.code_counter = 0

    def _format_terminal_output(self, content: str, code_blocks: list) -> str:
        """Format the terminal output to be clean and readable."""
        # Clean up any literal \n strings and get the main content
        final_content = content.replace('\\n', '\n')
        
        # Add file notifications
        if code_blocks:
            for code_filename, _, output_filename, _ in code_blocks:
                final_content += f"\n\nCode Generated: {code_filename}"
                final_content += f"\nOutput Generated: {output_filename}"
        
        return final_content

    def _process_stream_chunk(self, chunk: Dict[str, Any]) -> tuple[str, Optional[str], Optional[Dict], List]:
        """Process a chunk from the stream and return content, function call, images, and outputs."""
        content = chunk.get('content', '')
        function_call = chunk.get('function_call', '')
        outputs = chunk.get('outputs', [])
        
        # Extract any image URLs from the chunk
        images = {}
        if 'image_urls_dict' in chunk:
            images = chunk['image_urls_dict']
        elif 'image_urls' in chunk:
            for i, url in enumerate(chunk['image_urls']):
                images[f"image_{i}"] = url
        elif isinstance(function_call, dict) and 'arguments' in function_call:
            try:
                args = json.loads(function_call['arguments']) if isinstance(function_call['arguments'], str) else function_call['arguments']
                if isinstance(args, dict) and 'url' in args:
                    images[f"image_{len(images)}"] = args['url']
            except json.JSONDecodeError:
                pass
                
        return content, function_call, images, outputs

    def _handle_stream_response(self, response: requests.Response, max_retries: int = 3) -> tuple[str, List, str, List]:
        """Handle streaming response with retry logic and better error handling."""
        current_content = ""
        accumulated_function = ""
        accumulated_outputs = []
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        content, function_call, images, outputs = self._process_stream_chunk(chunk)
                        
                        # Handle outputs
                        if outputs:
                            accumulated_outputs.extend(outputs)
                        
                        # Accumulate content 
                        if content:
                            current_content += content
                            
                        # Handle function calls
                        if function_call:
                            if isinstance(function_call, dict) and function_call.get('arguments'):
                                if '"python":' in function_call['arguments']:
                                    accumulated_function += function_call['arguments']
                        
                        # Handle images by just storing their URLs
                        if images:
                            image_info = {"image_urls": images}
                            accumulated_outputs.append(image_info)
                            
                            # Save images silently
                            os.makedirs("outputs", exist_ok=True)
                            for img_id, url in images.items():
                                try:
                                    img_response = requests.get(url)
                                    if img_response.status_code == 200:
                                        img = Image.open(BytesIO(img_response.content))
                                        save_path = os.path.join("outputs", f"output_{img_id}.png")
                                        img.save(save_path)
                                except Exception:
                                    pass
                                    
                    except json.JSONDecodeError:
                        continue
                        
                # If we get here, processing was successful
                break
                
            except (requests.exceptions.ChunkedEncodingError, 
                    requests.exceptions.ConnectionError, 
                    requests.exceptions.StreamConsumedError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise Exception(f"Failed to process stream after {max_retries} attempts: {str(e)}")
                time.sleep(1)  # Wait before retrying
                
        return current_content, accumulated_outputs, accumulated_function, []
    
    def _sanitize_code(self, code: str) -> str:
        """Remove any double python key wrapping."""
        try:
            while isinstance(code, str) and code.startswith('{"python":'):
                code = json.loads(code)["python"]
        except json.JSONDecodeError:
            pass
        return code

    def _send_message(self, conversation_id: str, message: Dict[str, Any], model: str, current_reasoning_state: bool) -> Dict[str, Any]:
        """Enhanced send_message with cleaner output handling."""
        try:
            headers = {
                **self.client.headers,
                "conversation-id": conversation_id
            }

            # Handle file attachments
            new_attachments = {}
            if "file_paths" in message:
                for file_path in message["file_paths"]:
                    filename = self.client.files.upload(file_path)
                    self._register_file_source(conversation_id, filename)
                    new_attachments[filename] = {
                        "name": filename,
                        "isUploading": False,
                        "percentComplete": 100
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
                "selectedModels": None
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
            
            current_content = ""
            code_blocks = []
            accumulated_function = ""
            accumulated_outputs = []
            
            for line in response.iter_lines():
                if not line:
                    continue
                    
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    content, function_call, images, outputs = self._process_stream_chunk(chunk)
                    
                    # Handle outputs
                    if outputs:
                        accumulated_outputs.extend(outputs)
                    
                    # Accumulate content 
                    if content:
                        current_content += content
                        
                    # Handle function calls
                    if function_call:
                        if isinstance(function_call, dict) and function_call.get('arguments'):
                            if '"python":' in function_call['arguments']:
                                accumulated_function += function_call['arguments']
                    
                    # Handle images
                    if images:
                        image_info = {"image_urls": images}
                        accumulated_outputs.append(image_info)
                        
                        # Save images to outputs directory
                        os.makedirs("outputs", exist_ok=True)
                        for img_id, url in images.items():
                            try:
                                response = requests.get(url)
                                if response.status_code == 200:
                                    img = Image.open(BytesIO(response.content))
                                    save_path = os.path.join("outputs", f"output_{img_id}.png")
                                    img.save(save_path)
                                    accumulated_outputs.append(f"Saved image as {save_path}")
                            except Exception as e:
                                accumulated_outputs.append(f"Error saving image: {str(e)}")
                                
                except json.JSONDecodeError:
                    continue
            
            # Process accumulated code and outputs at the end
            if accumulated_function:
                try:
                    code_filename, output_filename = self._save_code_and_output(
                        accumulated_function, 
                        accumulated_outputs
                    )
                    # current_content += f"\nCode saved to: {code_filename}\n"
                    # current_content += f"Output saved to: {output_filename}\n"
                    code_blocks.append((code_filename, accumulated_function, output_filename, accumulated_outputs))
                except Exception as e:
                    current_content += f"\nError saving code/output: {str(e)}\n"

            # Format the content before returning
            formatted_content = self._format_terminal_output(current_content, code_blocks)
                    
            return {
                'content': formatted_content,
                'code_blocks': code_blocks,
                'metadata': {
                    'conversation_id': conversation_id,
                    'model': model,
                    'timestamp': datetime.now().timestamp()
                }
            }
            
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
            # Clean up outputs directory at the start of each chat session
            self._cleanup_outputs_directory()

            conversation_id = self._start_conversation(model)
            current_reasoning_state = False
            system_msg = None
            user_messages = []
            final_content = ""
            
            # Sort messages by type
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg
                    if "advanced_reasoning" in msg:
                        current_reasoning_state = msg["advanced_reasoning"]
                        if current_reasoning_state:
                            self.client.set_advanced_reasoning(True)
                elif msg["role"] == "user":
                    user_messages.append(msg)
            
            # Process system message if present
            if system_msg:
                response_data = self._send_message(conversation_id, system_msg, model, current_reasoning_state)
                final_content += response_data['content']
            
            # Process user messages
            for user_msg in user_messages:
                if "advanced_reasoning" in user_msg:
                    current_reasoning_state = user_msg["advanced_reasoning"]
                    if current_reasoning_state:
                        self.client.set_advanced_reasoning(True)
                    else:
                        self.client.set_advanced_reasoning(False)
                
                response_data = self._send_message(conversation_id, user_msg, model, current_reasoning_state)
                final_content += response_data['content']

            # Create and return the final response
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