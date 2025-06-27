from langchain_openai import OpenAIEmbeddings
from config.config import OPENAI_API_KEY

def get_openai_embeddings():
    """Returns OpenAI Embeddings."""
    return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
