from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id:int
    filename:str
    file_size : int
    page_count: int
    created_at: datetime
    
    class Config: 
        from_attributes = True
        

class QueryRequest(BaseModel):
    document_id: int
    question: str
    top_k: int = 5
    
    
class SourceChunk(BaseModel):
    page_number: int
    content: str
    
    
class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    
    

class QueryLogResponse(BaseModel):
    id: int
    document_id: int
    question: str
    answer: str
    created_at: datetime
    
    class Config:
        from_attributes = True