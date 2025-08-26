from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from .indexing import build_index
from .query import query_index

app = FastAPI(
    title="Tool Sync - Analysis Server",
    description="A server to analyze work items using a RAG pipeline.",
    version="0.1.0",
)

class IndexRequest(BaseModel):
    work_items_path: str

@app.get("/")
def read_root():
    """
    Root endpoint that returns the server status.
    """
    return {"status": "Analysis server is running"}

@app.post("/index", status_code=202)
async def trigger_indexing(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    Triggers the indexing process for the work items in the background.
    """
    background_tasks.add_task(build_index, request.work_items_path)
    return {"message": "Indexing process started in the background."}

@app.get("/query")
async def query_work_items(pergunta: str, n_results: int = 5) -> Dict[str, Any]:
    """
    Queries the work item index with a question.
    """
    if not pergunta:
        raise HTTPException(status_code=400, detail="A 'pergunta' (question) query parameter is required.")

    results = query_index(question=pergunta, n_results=n_results)
    return {"results": results}
