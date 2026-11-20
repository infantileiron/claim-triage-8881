from sqlalchemy import Column,Integer,String,Float,JSON,Text,ForeignKey,Boolean,UniqueConstraint,Index
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True);password=Column(String(200));role=Column(String(20))
class Claim(Base):
 __tablename__='claims'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True,nullable=False)
 amount=Column(Float);distance=Column(Float);holiday=Column(Boolean);label=Column(Integer,nullable=True);note=Column(Text,default='')
 # 金额/里程暂时只能给范围；点值票据上下界相等
 amount_min=Column(Float);amount_max=Column(Float);distance_min=Column(Float);distance_max=Column(Float)
 range_note=Column(Text,default='')
class Training(Base):
 __tablename__='trainings'
 id=Column(Integer,primary_key=True);name=Column(String(100));threshold=Column(Float);state=Column(String(20),default='queued');result=Column(JSON);error=Column(Text,default='')
class Review(Base):
 __tablename__='reviews'
 __table_args__=(UniqueConstraint('training_id','claim_id',name='uq_review_source'),)
 id=Column(Integer,primary_key=True);training_id=Column(Integer,ForeignKey('trainings.id'));claim_id=Column(Integer,ForeignKey('claims.id'));score=Column(Float);decision=Column(String(30),default='pending');note=Column(Text,default='');status=Column(String(20),default='draft')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
class Evidence(Base):
 __tablename__='evidences'
 id=Column(Integer,primary_key=True);claim_id=Column(Integer,ForeignKey('claims.id'),nullable=False)
 amount_min=Column(Float);amount_max=Column(Float);distance_min=Column(Float);distance_max=Column(Float)
 note=Column(Text,default='');actor=Column(String(100));created=Column(String(40))
class Score(Base):
 __tablename__='scores'
 __table_args__=(Index('ix_scores_active','active_key',unique=True),)
 id=Column(Integer,primary_key=True);claim_id=Column(Integer,ForeignKey('claims.id'),nullable=False,index=True)
 training_id=Column(Integer,ForeignKey('trainings.id'));state=Column(String(20),default='pending')
 p_min=Column(Float);p_max=Column(Float);band=Column(String(20));basis=Column(JSON);error=Column(Text,default='')
 active=Column(Boolean,default=True);active_key=Column(Integer,unique=True);version=Column(Integer,default=1)
 created=Column(String(40))
class TriageTask(Base):
 __tablename__='triage_tasks'
 __table_args__=(Index('ix_triage_active','active_key',unique=True),)
 id=Column(Integer,primary_key=True);claim_id=Column(Integer,ForeignKey('claims.id'),nullable=False,index=True)
 kind=Column(String(20),nullable=False);state=Column(String(20),default='queued')
 score_id=Column(Integer,ForeignKey('scores.id'));training_id=Column(Integer,ForeignKey('trainings.id'))
 p_min=Column(Float);p_max=Column(Float);band=Column(String(20));basis=Column(JSON)
 owner=Column(String(100),default='');attempts=Column(Integer,default=0);note=Column(Text,default='')
 active=Column(Boolean,default=True);active_key=Column(Integer,unique=True)
 created=Column(String(40));updated=Column(String(40))
