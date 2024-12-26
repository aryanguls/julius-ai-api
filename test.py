from julius_api import Julius

# Your actual Julius token here
JULIUS_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InJoM0dwdVZXd2JMMTJpYnBtamlxWCJ9.eyJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vdXNlcl9lbWFpbCI6ImFyeWFuZ3VsQHN0YW5mb3JkLmVkdSIsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby91c2VyX2lwIjoiMjYwMzo4MDAxOmY4NDA6MWI6Njg5OTo2ZjEwOmJkOWQ6YWNiZCIsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby91c2VyX2NvdW50cnlDb2RlIjoiVVMiLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vdXNlcl9jb250aW5lbnRDb2RlIjoiTkEiLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vZW1haWxfdmVyaWZpZWQiOnRydWUsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby9zdWJzY3JpcHRpb25fc3RhdHVzIjoiYWN0aXZlIiwiaHR0cHM6Ly9jaGF0d2l0aHlvdXJkYXRhLmlvL3Byb2R1Y3QiOiJwcm9kX083UXV1N2VKVnpxcTVOIiwiaHR0cHM6Ly9jaGF0d2l0aHlvdXJkYXRhLmlvL2NyZWF0ZWRfYXQiOiIyMDIzLTEyLTAxVDAzOjE1OjQ4Ljk1NFoiLCJpc3MiOiJodHRwczovL2F1dGguanVsaXVzLmFpLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTEwMzIzMjU1NTcxMDE0NzgzNjk3IiwiYXVkIjpbImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pbyIsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS51cy5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzM1MTU2ODIwLCJleHAiOjE3Mzc3NDg4MjAsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhenAiOiJRWFRzV0RsdHlUSTFWclJIT1FSUmZUdEcxY2Y0WURLOCJ9.1dSGHumaIiTwIh6D3KkfeUWMyhR4YthjlCnvkM1DFprPTwYQwtnYYI2lCpaJzCW_Z2o0JWVX2706SUpUOlBbOHEeBnVzsGEe4YM8M1VzDzZ5O-mztjdfesSIxCZjVxfdyAYAC-5NCG_gBxL3O75MpfeVf3KY7dDd37gYZFaiZGAol_X2kW7VcMDGq0sAxMHzeMvGOactj9Rm6F6iurgUlUu5FOUwC55vsDproAB2uyqhMy8h07p-srT5w9xvTcGDQBaOcIlfHbWqNzAWYhpW_uwmrgivnA2J_af_yF_ghgVMghuxbT4Bwni8uEkVdTD4OuiCG-q12_BUlbOcwtQJlQ"

# Initialize the client
julius = Julius(api_key=JULIUS_TOKEN)

# Test file upload first
file_path = "julius_response_27f6d748-33a6-4e86-9499-e1d6e426d08c.json"
try:
    uploaded_filename = julius.files.upload(file_path)
    print(f"Successfully uploaded file: {uploaded_filename}")
except Exception as e:
    print(f"Upload failed: {str(e)}")

# Now try with chat
try:
    response = julius.chat.completions.create(
        model="o1-mini",
        messages=[
            {"role": "system", "content": "You are a helpful data scientist."},
            {
                "role": "user",
                "content": "Please analyze this JSON file and find me the number of conversation ID's.",
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