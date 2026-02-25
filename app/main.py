from fastapi import FastAPI
from app.rag.ingest import router as ingest_router
from app.rag.query import router as query_router
from app.core.metrics import metrics_store
import os
import uvicorn

app = FastAPI(title="AI RAG Backend")

app.include_router(ingest_router)
app.include_router(query_router)


@app.get("/testing")
def root():
    return {"message": "working.."}
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

@app.get("/metrics")
def get_metrics():
    return metrics_store.snapshot()