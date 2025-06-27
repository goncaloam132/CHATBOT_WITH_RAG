from langchain_openai import ChatOpenAI
from config.config import OPENAI_API_KEY

def get_openai_llm():
    """Returns OpenAI Chat Model."""
    return ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY, temperature=0.3)
