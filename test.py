import os
from dotenv import load_dotenv
from julius_api import Julius

# Load environment variables
load_dotenv()

# Get Julius API token from environment
JULIUS_TOKEN = os.getenv('JULIUS_API_TOKEN')
if not JULIUS_TOKEN:
    raise ValueError("JULIUS_API_TOKEN not found in environment variables. Please check your .env file.")

# Initialize the client
julius = Julius(api_key=JULIUS_TOKEN)

def main():
    file_path = "eval_sets/Titanic.xlsx"
    try:
        uploaded_filename = julius.files.upload(file_path)
        print(f"Successfully uploaded file: {uploaded_filename}")
    except Exception as e:
        print(f"Upload failed: {str(e)}")

    # Now try with chat
    try:
        response = julius.chat.completions.create(
            model="default",
            messages=[
                {"role": "system", "content": "You are a helpful data scientist analyzing ship data."},
                {
                    "role": "user",
                    "content": "Please analyze this file and find me some stats on the most popular demographic on the titanic. Also draw any coorelations you canfind for me.",
                    "file_path": file_path,
                    "advanced_reasoning": True
                }
            ]
        )
        print("\nResponse:")
        print("=" * 50)
        print(response.message.content)
    except Exception as e:
        print(f"Chat failed: {str(e)}")

if __name__ == "__main__":
    main()