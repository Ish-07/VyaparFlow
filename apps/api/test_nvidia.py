"""
Standalone NVIDIA NIM connectivity + latency test.
Run this directly - it has NO dependency on the rest of the VyaparFlow
project, so a failure here tells you the problem is your network/key/
NVIDIA's service, not your app code.
"""
import time
from openai import OpenAI

API_KEY = "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"
BASE_URL = "https://integrate.api.nvidia.com/v1"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=90)

print("=== Test 1: Can we reach the API at all? (list models) ===")
start = time.monotonic()
try:
    models = client.models.list()
    elapsed = time.monotonic() - start
    print(f"OK in {elapsed:.1f}s - found {len(models.data)} models")
except Exception as e:
    print(f"FAILED after {time.monotonic() - start:.1f}s: {type(e).__name__}: {e}")

print()
print("=== Test 2: Simple chat completion (small prompt, should be fast) ===")
start = time.monotonic()
try:
    completion = client.chat.completions.create(
        model="meta/llama-3.3-70b-instruct",
        messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
        temperature=0.2,
        max_tokens=20,
        stream=False,
    )
    elapsed = time.monotonic() - start
    print(f"OK in {elapsed:.1f}s")
    print("Response:", completion.choices[0].message.content)
except Exception as e:
    print(f"FAILED after {time.monotonic() - start:.1f}s: {type(e).__name__}: {e}")

print()
print("=== Test 3: Embedding call (should be fast, ~1s) ===")
start = time.monotonic()
try:
    response = client.embeddings.create(
        model="nvidia/nemotron-3-embed-1b",
        input=["test text for embedding"],
        encoding_format="float",
        extra_body={"input_type": "query", "truncate": "END"},
    )
    elapsed = time.monotonic() - start
    print(f"OK in {elapsed:.1f}s - dimension: {len(response.data[0].embedding)}")
except Exception as e:
    print(f"FAILED after {time.monotonic() - start:.1f}s: {type(e).__name__}: {e}")

print()
print("=== Test 4: Larger RAG-style prompt (closer to your real failing case) ===")
start = time.monotonic()
try:
    completion = client.chat.completions.create(
        model="meta/llama-3.3-70b-instruct",
        messages=[
            {"role": "system", "content": "Answer the question using only the provided context."},
            {"role": "user", "content": "Context:\n" + ("This is sample invoice text. " * 100) + "\n\nQuestion: What are the payment terms?"},
        ],
        temperature=0.2,
        max_tokens=400,
        stream=False,
    )
    elapsed = time.monotonic() - start
    print(f"OK in {elapsed:.1f}s")
    print("Response:", completion.choices[0].message.content[:200])
except Exception as e:
    print(f"FAILED after {time.monotonic() - start:.1f}s: {type(e).__name__}: {e}")