import os
from fastapi import APIRouter, UploadFile, File

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

router = APIRouter(prefix="/api")

DB_FAISS_PATH = "vectorstore/db_faiss"


@router.post("/upload-doc/")
async def upload_doc(file: UploadFile = File(...)):
    file_path = f"temp/{file.filename}"

    # save file
    with open(file_path, "wb") as f:
        f.write(await file.read())

    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # metadata
    for doc in documents:
        doc.metadata["source"] = file.filename

    # chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    texts = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # multi-doc support
    if os.path.exists(DB_FAISS_PATH):
        db = FAISS.load_local(
            DB_FAISS_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        db.add_documents(texts)
    else:
        db = FAISS.from_documents(texts, embeddings)

    db.save_local(DB_FAISS_PATH)

    return {"message": "Document uploaded & embeddings created"}