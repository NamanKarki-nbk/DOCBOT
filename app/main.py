from fastapi import FastAPI
from app.routers import documents, query


app = FastAPI(
    title="DocBot",
    description="RAG-powered PDF QA BOT",
    
)
app.include_router(documents.router)
app.include_router(query.router)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}