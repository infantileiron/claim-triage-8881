import random,math
from src.config.database import Base,engine,Session
from src.models.entities import User,Claim
def seed():
 from src.utils.security import hash_password
 Base.metadata.create_all(engine);rng=random.Random(3106)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  for i in range(300):
   code=f'HX-1115-{i+1:03}';distance=round(rng.uniform(5,800),1);holiday=rng.random()<.25;amount=round(distance*rng.uniform(1.2,5.5)+rng.uniform(50,900),2)
   risk=-4.7+amount/700+1.1*holiday+amount/(distance+1)/8;label=int(rng.random()<1/(1+math.exp(-risk))) if i<260 else None
   if not s.query(Claim).filter_by(code=code).first():s.add(Claim(code=code,amount=amount,distance=distance,holiday=holiday,label=label,note='历史人工复核标签；仅用于模拟训练，不连接真实报销'))
  s.commit();print({'users':s.query(User).count(),'claims':s.query(Claim).count()})
if __name__=='__main__':seed()
