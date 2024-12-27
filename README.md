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