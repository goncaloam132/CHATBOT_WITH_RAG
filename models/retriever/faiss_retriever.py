from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from utils.vector_store import load_vector_store
from models.llms.openai_llm import get_openai_llm
from models.llms.ollama_llm import get_ollama_llm

def get_conversational_chain(model_name):
    """Creates a RetrievalQA chain with FAISS retriever and a custom prompt template."""
    prompt_template = PromptTemplate(
        template="""Responda a pergunta da forma mais detalhada possível com base no contexto fornecido.
        Se a resposta não estiver no contexto, apenas diga: "A resposta não está disponível no contexto."
        Não invente respostas.\n\n
        Contexto:\n {context}\n
        Pergunta: \n{question}\n

        Resposta:
        """,
        input_variables=["context", "question"]
    )

    if model_name == "openai":
        model = get_openai_llm() 
    elif model_name == "ollama":
        model = get_ollama_llm()
    else:
        raise ValueError(f"Modelo desconhecido: {model_name}")

    retriever = load_vector_store(model_name).as_retriever()

    return RetrievalQA.from_chain_type(
        llm=model,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt_template},
        return_source_documents=True
    )
