import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # Vector search settings
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SIMILARITY_THRESHOLD = 0.3  # Lowered for better matching
    MAX_RESULTS = 5

    # LLM settings
    LLM_MODEL = "gpt-4"
    MAX_TOKENS = 1000
    TEMPERATURE = 0.1
