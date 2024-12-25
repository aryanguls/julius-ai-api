import os
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# 1) Paste your fresh Julius token here
#    e.g. "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZC..."
#    Do NOT include "Bearer " in front— we'll add that in code.
JULIUS_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InJoM0dwdVZXd2JMMTJpYnBtamlxWCJ9.eyJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vdXNlcl9lbWFpbCI6ImFyeWFuZ3VsQHN0YW5mb3JkLmVkdSIsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby91c2VyX2lwIjoiMjYwMzo4MDAxOmY4NDA6MWI6Njg5OTo2ZjEwOmJkOWQ6YWNiZCIsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby91c2VyX2NvdW50cnlDb2RlIjoiVVMiLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vdXNlcl9jb250aW5lbnRDb2RlIjoiTkEiLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vZW1haWxfdmVyaWZpZWQiOnRydWUsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby9jcmVhdGVkX2F0IjoiMjAyMy0xMi0wMVQwMzoxNTo0OC45NTRaIiwiaXNzIjoiaHR0cHM6Ly9hdXRoLmp1bGl1cy5haS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDExMDMyMzI1NTU3MTAxNDc4MzY5NyIsImF1ZCI6WyJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8iLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTczNTA4NjYwNCwiZXhwIjoxNzM3Njc4NjA0LCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIG9mZmxpbmVfYWNjZXNzIiwiYXpwIjoiUVhUc1dEbHR5VEkxVnJSSE9RUlJmVHRHMWNmNFlESzgifQ.G-BVjbI7mmAKLkLeWaGvixvq891LSrnYw2KiSk5NXcurN8R9dG_oR02on5sfGM6T2PH7Z2ZVbS0FuacL5wHJXLd0wnF20B5XsdJpElJdmkD8Mvxc7rpHJDPpbM3_e2xVSOSHYLEPq059wLX7iuQiu6hNYa5roTpDA418oORR4JMJZZy9n5gFkfmVk7pMfMn4HMEa9vpMn_XHeNyU9WaEKC5Rl3utr9jCQsUxDP1X7tbFtyAtoxlebEndEwtLkmvVMYO_bQLKJ86yvwA884PnoNwuBgTmEAc3ogEbHc5G9oyJhfCfK40jJKttd0u8X8l6KvaGfh5gv640gI89Bl_3KA"

# 2) Base Julius endpoint
BASE_URL = "https://api.julius.ai"


@app.route("/send", methods=["POST"])
def send_message():
    """
    Receives JSON: { "prompt": "Hello Julius!" }
    1) Starts a new conversation via /api/chat/start
    2) Sends the prompt via /api/chat/message
    3) Returns a JSON with:
       {
         "conversation_id": ...,
         "parsed_chunks": [...],
         "saved_file": "filename.json"
       }
    """

    data = request.json or {}
    user_prompt = data.get("prompt", "")
    if not user_prompt:
        return jsonify({"error": "Please provide a 'prompt'"}), 400

    # Check if token is present
    if not JULIUS_TOKEN or "PASTE_THE_JWT_TOKEN_HERE" in JULIUS_TOKEN:
        return jsonify({
            "error": "Your Julius token is missing or still set to the placeholder. Paste it into the script!"
        }), 401

    # Step 1: Start a new conversation
    conversation_id = start_conversation(JULIUS_TOKEN)
    if not conversation_id:
        return jsonify({"error": "Failed to start conversation."}), 500

    # Step 2: Send the user prompt (which now captures & stores multiple JSON chunks)
    parsed_chunks, output_file, final_output = post_message(conversation_id, user_prompt, JULIUS_TOKEN)

    if not parsed_chunks:
        return jsonify({"error": "Failed to send message or parse chunks."}), 500

    return jsonify({
        "conversation_id": conversation_id,
        "parsed_chunks": parsed_chunks,
        "saved_file": output_file,
        "final_output": final_output
    })


def start_conversation(token: str) -> str:
    """
    Calls Julius's /api/chat/start to create a new conversation.
    Returns the conversation ID (string) or an empty string if it fails.
    """
    url = f"{BASE_URL}/api/chat/start"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "https://julius.ai"
    }
    resp = requests.post(url, headers=headers, json={})
    if resp.status_code == 200:
        data = resp.json()
        # e.g. { "id": "05d3d5e1-a1d9-481a-b658-d2cba143436a", ... }
        conversation_id = data.get("id", "")
        if conversation_id:
            print(f"Started conversation: {conversation_id}")
            return conversation_id

    print("start_conversation error:", resp.status_code, resp.text)
    return ""


def post_message(conversation_id: str, prompt: str, token: str):
    """
    Calls Julius's /api/chat/message to send 'prompt'.
    Because Julius may return multiple JSON objects in a single response,
    we manually parse them line-by-line, store them in a local JSON file,
    and return them as a list.

    Returns a tuple: (list_of_parsed_chunks, json_filename)
    """
    url = f"{BASE_URL}/api/chat/message"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "conversation-id": conversation_id,
        "Origin": "https://julius.ai"
    }
    payload = {
        "message": {
            "content": prompt
        },
        "provider": "default",
        "chat_mode": "auto",
        "client_version": "20240130",
        "theme": "light"
    }

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        print("post_message error:", resp.status_code, resp.text)
        return ([], "", "")

    # Instead of resp.json(), parse multiple JSON objects from resp.text
    resp_text = resp.text
    final_output = ""

    parsed_chunks = []
    for line in resp_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            parsed_chunks.append(data)
        except json.JSONDecodeError:
            # If a line doesn't parse, ignore or log
            print(f"Skipping line that didn't parse as JSON:\n{line}\n")

    # Save all parsed chunks to a file named after the conversation ID.
    # e.g. "julius_response_fb08fe0b-d099-b524.json"
    filename = f"julius_response_{conversation_id}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(parsed_chunks, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(parsed_chunks)} chunk(s) to {filename}")

    final_output = ""
    for chunk in parsed_chunks:
        if chunk.get("role") == "assistant" or chunk.get("role") == "":
            content = chunk.get("content", "")
            if content:
                final_output += content

    return (parsed_chunks, filename, final_output)


if __name__ == "__main__":
    # Run the Flask app locally on port 5000
    app.run(debug=True, port=5000)