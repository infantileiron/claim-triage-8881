from fastapi import HTTPException
from src.models.entities import Training
def ensure_training(s,i):
 row=s.get(Training,i)
 if not row:raise HTTPException(404,'训练版本不存在')
 return row
