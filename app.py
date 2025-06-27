import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from utils.pdf_processing import get_pdf_text_with_page_info
from utils.text_processing import get_text_chunks_openai, get_text_chunks_ollama
from utils.vector_store import get_vector_store, check_vector_store_exists  
from models.retriever.faiss_retriever import get_conversational_chain
from models.llms.openai_llm import get_openai_llm
from models.llms.ollama_llm import get_ollama_llm

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Armazenar histórico de mensagens (simples para demonstração)
chat_history = []

# Pasta onde os PDFs serão armazenados
UPLOAD_FOLDER = "data/raw_pdfs"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Criar diretório se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lista global para armazenar nomes dos PDFs
pdf_files = []

@app.route("/")
def index():
    return render_template("index.html", pdf_files=pdf_files)

@app.route("/upload", methods=["POST"])
def upload_files():
    global pdf_files

    if "pdfs" not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado!"}), 400

    files = request.files.getlist("pdfs")

    for file in files:
        if file.filename == "":
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Salvar o arquivo no servidor
        file.save(filepath)

        # Evitar duplicados na lista
        if filename not in pdf_files:
            pdf_files.append(filename)

    return jsonify({"message": "PDFs enviados com sucesso!", "pdfs": pdf_files})

@app.route("/process_pdfs", methods=["POST"])
def process_pdfs():
    global pdf_files

    if not pdf_files:
        return jsonify({"message": "Nenhum PDF carregado!"}), 400

    all_text_chunks = []
    all_text_with_info = []

    # Primeiro, processamos os PDFs e extraímos o texto
    for filename in pdf_files:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        with open(filepath, "rb") as f:
            pdf_text_with_info = get_pdf_text_with_page_info([f], filename)
            all_text_with_info.extend(pdf_text_with_info)

    # Selecionar chunking baseado no modelo escolhido
    embedding_model = request.form.get("embedding_model", "openai")
    text_chunks = get_text_chunks_openai(all_text_with_info) if embedding_model == "openai" else get_text_chunks_ollama(all_text_with_info)

    # Aqui, vamos garantir que o `filename` é atribuído corretamente a cada chunk de texto
    for chunk in text_chunks:
        # Se o chunk não tem o `filename` atribuído, o atribuímos manualmente
        chunk['filename'] = chunk.get('filename', filename)  # Garantir que o chunk recebe o filename correto
        all_text_chunks.append(chunk)

        # DEBUG: Verifique se cada chunk está correto
        print(f"Chunk: {chunk['text'][:100]}... (Fonte: {chunk['filename']})")

    # Passar o modelo de embedding para get_vector_store
    get_vector_store(all_text_chunks, embedding_model)

    return jsonify({"message": "Processamento concluído!"})





@app.route("/list_pdfs", methods=["GET"])
def list_pdfs():
    return jsonify({"pdfs": pdf_files})

@app.route("/view/<filename>")
def view_pdf(filename):
    return render_template("view_pdf.html", filename=filename)

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/chat", methods=["POST"])
def chat():
    print("Chat route was hit!")
    user_question = request.json.get("question")
    if not user_question:
        return jsonify({"error": "No question provided"}), 400

    embedding_model = request.json.get("embedding_model", "openai")
    use_rag_str = request.json.get("use_rag", 0)
    use_rag = int(use_rag_str) == 1  # Converter para booleano


    try:
        if use_rag:  # Utilizador usa o RAG
            vector_store_exists = check_vector_store_exists(embedding_model)
            if vector_store_exists: # Vector store existe
                chain = get_conversational_chain(embedding_model)
                response = chain.invoke({"query": user_question})
                answer = response["result"] if response else "I couldn't find a specific answer in the PDFs."
                source_documents = response.get("source_documents", [])
                sources = []
                for doc in source_documents:
                    filename = doc.metadata.get('filename')
                    page = doc.metadata.get('page')
                    if filename and page:
                        sources.append({"filename": filename, "page": page})
            else: # Vector store não existe
                if embedding_model == "openai":
                    model = get_openai_llm()
                else:
                    model = get_ollama_llm()

                answer = model.invoke(user_question)

                if hasattr(answer, 'content'):
                    answer = answer.content
                elif isinstance(answer, str):
                    answer = answer
                else:
                    answer = str(answer)
                sources = []
        else:  # Utilizador quer utilizar LLM diretamente
            if embedding_model == "openai":
                model = get_openai_llm()
            else:
                model = get_ollama_llm()

            answer = model.invoke(user_question)

            if hasattr(answer, 'content'):
                answer = answer.content
            elif isinstance(answer, str):
                answer = answer
            else:
                answer = str(answer)
            sources = []

    except Exception as e:
        answer = f"An error occurred: {str(e)}"
        sources = []

    chat_history.append({"role": "user", "content": user_question})
    chat_history.append({"role": "assistant", "content": answer})

    return jsonify({"response": answer, "chat_history": chat_history, "sources": sources})

if __name__ == "__main__":
    app.run(debug=True)
