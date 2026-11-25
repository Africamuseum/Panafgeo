import asyncio
import json
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("URL")
MODEL = os.getenv("MODEL")

prompt = """Summarize the following text and convert it into JSON-LD, using schema.org for archive component. Keep the text in French. Here is an example of output structure:
    {
      "@context": "https://schema.org",
      "@type": "ArchiveComponent",
      "@id": "",
      "abstract": "",
      "author": [{"@type": "Person", "name": ""}],
      "contentLocation": [{"@type": "Place", "name": ""}],
      "countryOfOrigin": {"@type": "Country", "name": ""},
      "temporalCoverage": "",
      "mentions": [{"@type": "Person", "name": ""}],
      "headline": "",
      "keywords": [""],
      "producer": {"@type": "Organization", "name": ""}
    }
    The text is:
"""

async def extract_keywords(text, client):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt + text},
                ]
            }
        ],
        "max_tokens": 4096,
        "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    response = await client.post(URL, json=payload)
    data = response.json()
    choice = data["choices"][0]
    print(choice["message"]["content"])
    return data

async def process(content_list):
    async with httpx.AsyncClient(timeout=120, limits=httpx.Limits(max_connections=16)) as client:
        tasks = [extract_keywords(full_str, client) for full_str in content_list]

        keywords_list = await asyncio.gather(*tasks, return_exceptions=True)
    return keywords_list

if __name__ == "__main__":
    with open("01784_02.json", "r", encoding="utf-8") as f:
        content = f.read()
    content = json.loads(content)
    content_list = []
    print("Number of tokens: ", len("\n".join(obj["text"] for obj in content))/4)
    content_list.append("\n".join(obj["text"] for obj in content))
    keywords_list = asyncio.run(process(content_list))