# Julius AI API Client
A Python client for interacting with the Julius AI. This client provides a simple and integrateable interface for file operations and chat completions with their various AI models.

## Installation and Setup

### Clone the repository:
```bash
git clone https://github.com/aryanguls/julius-ai-api.git
cd julius-ai-api
```

### Obtaining a Julius Token
1. Go to [Julius AI](https://julius.ai)
2. Sign up or log in to your account
3. Navigate to the chatbot window
4. Right click on the screen and select the inspect option from the dropdown (which should open the Developer console for your browser)
5. Navigate to the Network tab from the options on the top of the developer console window
6. In the Network logs click on any of the logs that is of type 'fetch' (current, status, usage etc etc) and scroll down to the Request Header section.
7. Copy the value of the Authorization key without the 'Bearer' text - this is your Julius token!

### Setting Up Environment
1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your API token:

```env
JULIUS_API_TOKEN=your_api_token_here
```

3. Run the following python command
```python
python3 test.py
```

## Usage 

### Basic Usage
```python
from julius_api import Julius
import os

# Initialize the client
julius = Julius(api_key=os.getenv('JULIUS_API_TOKEN'))

# Upload a file
file_path = ["path/to/your/file"]
uploaded_filename = julius.files.upload(file_path)
print(f"Successfully uploaded: {uploaded_filename}")

# Create a chat completion
response = julius.chat.completions.create(
    model="default",
    messages=[
        {
            "role": "user",
            "content": "Please analyze the uploaded file.",
            "file_paths": file_path,
            "advanced_reasoning": True
        }
    ]
)

print(response.message.content)
```

## Advanced Features

### Advanced Reasoning
Advanced reasoning is a feature that can be enabled for more complex analysis:

```python
# Enable advanced reasoning for a single message
response = julius.chat.completions.create(
    model="default",
    messages=[
        {
            "role": "user",
            "content": "Analyze this data",
            "advanced_reasoning": True
        }
    ]
)

# Advanced reasoning persists for subsequent messages
# To disable it, explicitly set it to False
response = julius.chat.completions.create(
    model="default",
    messages=[
        {
            "role": "user",
            "content": "First analysis",
            "advanced_reasoning": True  # Enables advanced reasoning
        },
        {
            "role": "user",
            "content": "Second analysis"  # Advanced reasoning still enabled
        },
        {
            "role": "user",
            "content": "Third analysis",
            "advanced_reasoning": False  # Explicitly disable advanced reasoning
        }
    ]
)
```

### Working with Multiple Files
You can upload and analyze multiple files in several ways:

```python
# Method 1: Upload files individually
file1 = julius.files.upload("path/to/file1.csv")
file2 = julius.files.upload("path/to/file2.xlsx")

# Method 2: Upload multiple files in a single chat completion
file_paths = [
    "path/to/file1.csv",
    "path/to/file2.xlsx",
    "path/to/file3.pdf"
]

response = julius.chat.completions.create(
    model="default",
    messages=[
        {
            "role": "user",
            "content": "Compare these files",
            "file_paths": file_paths,
            "advanced_reasoning": True
        }
    ]
)

# Method 3: Sequential file analysis
response = julius.chat.completions.create(
    model="default",
    messages=[
        {
            "role": "system",
            "content": "You are analyzing multiple documents."
        },
        {
            "role": "user",
            "content": "Analyze the first dataset",
            "file_paths": ["path/to/file1.csv"]
        },
        {
            "role": "user",
            "content": "Now compare with the second dataset",
            "file_paths": ["path/to/file2.csv"]
        }
    ]
)
```

## Output Handling of Code Interpeter 
By default, the client:
- Creates an `outputs` directory for generated files
- Saves code files as `generated_code_{n}.txt`
- Saves corresponding outputs as `generated_output_{n}.txt`
- Automatically downloads and saves any generated images
- Cleans up the outputs directory between sessions

