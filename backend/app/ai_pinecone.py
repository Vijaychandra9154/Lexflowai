"""Pinecone + LangChain helper for production RAG."""
import os
import openai

try:
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import Pinecone
    from langchain.llms import OpenAI
    from langchain.chains import RetrievalQA
except Exception as e:
    raise ImportError(
        "Please install langchain and pinecone-client to use production vector store: "
        "pip install langchain pinecone-client"
    )

import pinecone

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "lexflowai-index")

openai.api_key = os.getenv("OPENAI_API_KEY")

_embeddings = None
_vectorstore = None


def init_pinecone():
    global _embeddings, _vectorstore
    if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
        raise ValueError("PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set")
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    _embeddings = OpenAIEmbeddings()
    # Attempt to create index if it doesn't exist
    try:
        if PINECONE_INDEX_NAME not in pinecone.list_indexes():
            pinecone.create_index(PINECONE_INDEX_NAME, dimension=1536, metric="cosine")
    except Exception:
        # Index might already exist or permissions limited
        pass
    index = pinecone.Index(PINECONE_INDEX_NAME)
    _vectorstore = Pinecone(index, _embeddings.embed_query, "text")
    return _vectorstore


def add_texts_to_index(texts, metadatas=None):
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = init_pinecone()
    _vectorstore.add_texts(texts=texts, metadatas=metadatas or [{} for _ in texts])


def query_index(query: str, top_k: int = 5):
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = init_pinecone()
    docs = _vectorstore.similarity_search(query, k=top_k)
    return [d.page_content for d in docs]


def generate_with_retrieval(query: str, instruction: str, top_k: int = 5):
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = init_pinecone()
    llm = OpenAI(temperature=0, model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=_vectorstore.as_retriever(search_kwargs={"k": top_k}),
    )
    prompt = f"User instruction: {instruction}\n\nUser query: {query}"
    return qa.run(prompt)
