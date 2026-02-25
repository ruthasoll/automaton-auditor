from dotenv import load_dotenv
load_dotenv()  # loads .env automatically
import os

# Optional: quick check (can remove later)
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Missing OPENAI_API_KEY in .env")
if not os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGCHAIN_TRACING_V2") == "true":
    print("Warning: LANGCHAIN_API_KEY missing → tracing disabled")