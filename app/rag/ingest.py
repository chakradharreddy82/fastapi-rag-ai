import os
from fastapi import APIRouter, UploadFile, File
from langchain_community.vectorstores import PGVector
from langchain_mistralai import MistralAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import DATABASE_URL, MISTRAL_API_KEY

router = APIRouter(prefix="/api")


@router.post("/upload-doc/")
async def upload_doc(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"

    os.makedirs("temp", exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    loader = PyPDFLoader(file_path)
    documents = loader.load()

    for doc in documents:
        doc.metadata["source"] = file.filename

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    texts = splitter.split_documents(documents)

    embeddings = MistralAIEmbeddings(
        model="mistral-embed",
        api_key=MISTRAL_API_KEY,
    )

    PGVector.from_documents(
        documents=texts,
        embedding=embeddings,
        connection_string=DATABASE_URL,
        collection_name="rag_docs",
    )

    return {"message": "Document uploaded & embeddings created"}