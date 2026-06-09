import os
import google.auth
import google.auth.transport.requests
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION   = os.environ.get("GCP_LOCATION", "us-central1")

credentials, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
auth_req = google.auth.transport.requests.Request()
credentials.refresh(auth_req)

client = OpenAI(
    api_key=credentials.token,
    base_url=f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/openapi/"
)

resp = client.chat.completions.create(
    model="google/gemini-2.5-flash-lite",
    messages=[{"role": "user", "content": "Reply with one word: working"}],
    max_tokens=10
)
print(resp.choices[0].message.content)
print(f"Tokens: {resp.usage.total_tokens}")