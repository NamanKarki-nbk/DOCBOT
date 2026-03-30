from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import QueryLog, Document
from app.schemas import QueryRequest, QueryResponse, QueryLogResponse
from app.services.rag import answer_quesiton


router = APIRouter(prefix="/query", tags= ["Query"])

@router.post("/", response_model=QueryResponse)
def query_document(payload: QueryRequest, db: Session = get_db):
    doc = db.query(Document).filter(Document.id == payload.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        result = answer_quesiton(payload.document_id, payload.question, payload.top_k)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="FAISS INDEX not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail = f"RAG pipeline error: {str(e)}")
    
    #log every query to postgress
    log = QueryLog(
        document_id = payload.document_id,
        question = payload.question,
        answer = result["answer"]
    )
    db.add(log)
    db.commit()
    
    return result


@router.get("/history.{document_id}", response_model=list[QueryLogResponse])
def query_history(document_id: int , db: Session = Depends(get_db)):
    return (
        db.query(QueryLog)
        .filter(QueryLog.document_id ==document_id)
        .order_by(QueryLog.created_at.desc())
        .limit(20)
        .all()
    )