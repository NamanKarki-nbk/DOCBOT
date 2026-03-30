from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document
from app.schemas import DocumentResponse
from app.services.ingester import ingest_pdf, delete_index, get_page_count



router = APIRouter(prefix="/document", tags=["Documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db:Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    
    file_bytes = await file.read()
    
    doc = Document(
        filename = file.filename,
        file_size = len(file_bytes),
        page_count = get_page_count(file_bytes)
    )
    
    doc.add()
    db.flush()
    
    try:
        chunk_count = ingest_pdf(file_bytes, doc.id)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    
    db.commit()
    db.refresh(doc)
    return doc


#api to get all the documents
@router.get("/", response_model=list[DocumentResponse])
def list_documents(db:Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


#api to get a single document
@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int , db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

#api to delete a single document
@router.delete("/{document_id}")
def delete_document(document_id: int, db : Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail = "Document not found")
    
    db.delete(doc)
    db.commit()
    delete_index(document_id)
    return {"message": f"Document '{doc.filename}' deleted successfully"}
    
