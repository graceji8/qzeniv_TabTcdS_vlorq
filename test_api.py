import os
import requests

prompt = (
    "Generate a list of 20 of the most famous and recognizable CURRENTLY ALIVE top world leaders for the year 2026. "
    "Include potential or incoming leaders like Mark Carney from Canada, alongside extremely well-known figures like Donald Trump, Emmanuel Macron, etc. "
    "DO NOT include anyone who is deceased. "
    "Provide a famous quote and the gender ('male' or 'female') for each person. Format each line exactly as 'Name|Quote|Gender'. "
    "Do not include numbering, bullet points, or any other text."
)

github_token = os.environ.get("GH_MODELS_TOKEN") or os.environ.get("GIT_MODEL_TOKEN") or os.environ.get("GITHUB_TOKEN")
if github_token:
    print(f"DEBUG: github_token detected (length: {len(github_token)})")
    response = requests.post(
        "https://models.inference.ai.azure.com/chat/completions",
        headers={"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9
        },
        timeout=30
    )
    if response.status_code == 200:
        print("DEBUG: GitHub Models API success!")
        data = response.json()
        content = data['choices'][0]['message']['content']
        print("RAW CONTENT:")
        print(repr(content))
        result = [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
        print("PROCESSED RESULT:")
        print(result)
    else:
        print(f"Error: {response.status_code} - {response.text}")
