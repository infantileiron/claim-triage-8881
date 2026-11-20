from pydantic import BaseModel,Field,model_validator
from typing import Optional,Literal
class Login(BaseModel):email:str;password:str
class ClaimInput(BaseModel):
 code:str=Field(min_length=1,max_length=60)
 amount:Optional[float]=Field(default=None,ge=0,le=100000,allow_inf_nan=False)
 distance:Optional[float]=Field(default=None,ge=0,le=10000,allow_inf_nan=False)
 amount_min:Optional[float]=Field(default=None,ge=0,le=100000,allow_inf_nan=False)
 amount_max:Optional[float]=Field(default=None,ge=0,le=100000,allow_inf_nan=False)
 distance_min:Optional[float]=Field(default=None,ge=0,le=10000,allow_inf_nan=False)
 distance_max:Optional[float]=Field(default=None,ge=0,le=10000,allow_inf_nan=False)
 holiday:bool=False
 label:Optional[Literal[0,1]]=None
 note:str=Field(default='',max_length=1000)
 range_note:str=Field(default='',max_length=1000)
 @model_validator(mode='after')
 def _ranges(self):
  ams=[x for x in (self.amount_min,self.amount_max) if x is not None]
  dms=[x for x in (self.distance_min,self.distance_max) if x is not None]
  if len(ams)==1 or len(dms)==1:raise ValueError('范围上下界必须同时填写')
  if ams and ams[0]>ams[1]:raise ValueError('金额下界不能大于上界')
  if dms and dms[0]>dms[1]:raise ValueError('里程下界不能大于上界')
  if self.amount is None and not ams:raise ValueError('请填写确定金额，或填写金额范围上下界')
  if self.distance is None and not dms:raise ValueError('请填写确定里程，或填写里程范围上下界')
  if self.amount_min is None:self.amount_min=self.amount_min if self.amount_min is not None else self.amount
  if self.amount_max is None:self.amount_max=self.amount
  if self.distance_min is None:self.distance_min=self.distance
  if self.distance_max is None:self.distance_max=self.distance
  return self
class TrainingInput(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 threshold:float=Field(default=.5,ge=.1,le=.9,allow_inf_nan=False)
class ReviewInput(BaseModel):
 decision:Literal['valid','flagged']
 note:str=Field(min_length=6,max_length=2000)
class EvidenceInput(BaseModel):
 amount_min:float=Field(ge=0,le=100000,allow_inf_nan=False)
 amount_max:float=Field(ge=0,le=100000,allow_inf_nan=False)
 distance_min:float=Field(ge=0,le=10000,allow_inf_nan=False)
 distance_max:float=Field(ge=0,le=10000,allow_inf_nan=False)
 note:str=Field(default='',max_length=1000)
 @model_validator(mode='after')
 def _check(self):
  if self.amount_min>self.amount_max:raise ValueError('金额下界不能大于上界')
  if self.distance_min>self.distance_max:raise ValueError('里程下界不能大于上界')
  return self
class CompleteInput(BaseModel):
 note:str=Field(default='',max_length=2000)
