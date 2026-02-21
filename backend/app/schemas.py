from pydantic import BaseModel

class ReadingCreate(BaseModel):
    pond_id: int
    dissolved_oxygen: float
    temperature: float
    ammonia: float
    ph: float
