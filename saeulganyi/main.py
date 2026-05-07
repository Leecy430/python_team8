from dotenv import load_dotenv
load_dotenv()

import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "안녕! 테스트야"}
    ]
)

print(message.content[0].text)