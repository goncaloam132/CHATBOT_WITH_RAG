from langchain_ollama import OllamaEmbeddings


def get_ollama_embeddings():
    """Returns Ollama Embeddings."""
    return OllamaEmbeddings(model="granite-embedding:278m")
