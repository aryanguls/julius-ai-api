from julius_api import Julius

# Your actual Julius token from before
JULIUS_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InJoM0dwdVZXd2JMMTJpYnBtamlxWCJ9.eyJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vdXNlcl9lbWFpbCI6ImFyeWFuZ3VsQHN0YW5mb3JkLmVkdSIsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby91c2VyX2lwIjoiMjYwMzo4MDAxOmY4NDA6MWI6Njg5OTo2ZjEwOmJkOWQ6YWNiZCIsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby91c2VyX2NvdW50cnlDb2RlIjoiVVMiLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vdXNlcl9jb250aW5lbnRDb2RlIjoiTkEiLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8vZW1haWxfdmVyaWZpZWQiOnRydWUsImh0dHBzOi8vY2hhdHdpdGh5b3VyZGF0YS5pby9jcmVhdGVkX2F0IjoiMjAyMy0xMi0wMVQwMzoxNTo0OC45NTRaIiwiaXNzIjoiaHR0cHM6Ly9hdXRoLmp1bGl1cy5haS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDExMDMyMzI1NTU3MTAxNDc4MzY5NyIsImF1ZCI6WyJodHRwczovL2NoYXR3aXRoeW91cmRhdGEuaW8iLCJodHRwczovL2NoYXR3aXRoeW91cmRhdGEudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTczNTA4NjYwNCwiZXhwIjoxNzM3Njc4NjA0LCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIG9mZmxpbmVfYWNjZXNzIiwiYXpwIjoiUVhUc1dEbHR5VEkxVnJSSE9RUlJmVHRHMWNmNFlESzgifQ.G-BVjbI7mmAKLkLeWaGvixvq891LSrnYw2KiSk5NXcurN8R9dG_oR02on5sfGM6T2PH7Z2ZVbS0FuacL5wHJXLd0wnF20B5XsdJpElJdmkD8Mvxc7rpHJDPpbM3_e2xVSOSHYLEPq059wLX7iuQiu6hNYa5roTpDA418oORR4JMJZZy9n5gFkfmVk7pMfMn4HMEa9vpMn_XHeNyU9WaEKC5Rl3utr9jCQsUxDP1X7tbFtyAtoxlebEndEwtLkmvVMYO_bQLKJ86yvwA884PnoNwuBgTmEAc3ogEbHc5G9oyJhfCfK40jJKttd0u8X8l6KvaGfh5gv640gI89Bl_3KA"

# Initialize the client
julius = Julius(api_key=JULIUS_TOKEN)

# Send a message to Julius (try with a non-default model)
response = julius.chat.completions.create(
    model="cohere",  # It will automatically fall back to default if needed
    messages=[
        {"role": "system", "content": "You are a helpful data scientist."},
        {"role": "user", "content": "List down the conditions for Overfitting and Underfitting."}
    ]
)

# Print response
print("\nResponse:")
print("=" * 50)
print(response.message.content)

# Print metadata
print("\nMetadata:")
print("=" * 50)
print(f"Conversation ID: {response.id}")
print(f"Model: {response.model}")