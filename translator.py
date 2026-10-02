import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_KEY")

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPEN_ROUTER_API_KEY,
)

english_word = input("Enter an English word to translate: ").strip()

if english_word:
  print("Waiting for response...", flush=True)
  response = client.chat.completions.create(
    model="qwen/qwen3.8-27b:free",
    messages=[
      {
        "role": "system",
        "content": "Translate the user's English word into Traditional Chinese. Reply with only the translation.",
      },
      {"role": "user", "content": english_word},
    ],
  )

  print(response.choices[0].message.content)