import os 
from langchain_ollama import ChatOllama
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from app.services.ingester import load_index
from dotenv import load_dotenv


load_dotenv()
LLaMA_MODEL = os.getenv("LLaMA_MODEL")


RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are a document QA assistant.
Answer ONLY using the provided context.
If the answer is not in the context, say "I don't know."

Context:
{context}

Question:
{question}
"""
)



def get_llm():
    return ChatOllama(
        model= LLaMA_MODEL,
        temperature=0.1
    )


def answer_quesiton(document_id: int, question: str, top_k: int = 5)-> dict:
    """
    Full RAG pipeline:
    1. Load FAISS index for the document
    2. Similarity search for top_k relevant chunks
    3. Pass chunks + question to Ollama via RetrievalQA chain
    4. Return answer + source chunks

    Returns: { answer: str, sources: [{ page_number, content }] }
    """

    vectorstore = load_index(document_id)
    retriever = vectorstore.as_retriever(
        search_type ="similarity",
        search_kwargs={"k": top_k}
    )
    
    llm = get_llm()
    
    qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    return_source_documents=True,
    chain_type_kwargs={"prompt": RAG_PROMPT}
)

    result = qa_chain.invoke({"query": question})

    sources = []
    seen = set()

    for doc in result.get("source_documents", []):
        content = doc.page_content.strip()
        page = doc.metadata.get("page", 0) + 1

        key = (page, hash(content))

        if key not in seen:
            seen.add(key)
            sources.append({
                "page_number": page,
                "content": content[:300]
            })

    sources = sorted(sources, key=lambda x: x["page_number"])

    return {
        "answer": result.get("result", "").strip(),
        "sources": sources
    }