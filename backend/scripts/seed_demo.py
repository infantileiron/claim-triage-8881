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
  # 金额/里程暂只能给范围的票据：点值取范围中点，标签待标注
  ranges=[('HX-RANGE-01',1800,2600,120,200,True),('HX-RANGE-02',300,520,40,90,False),('HX-RANGE-03',4200,6800,300,460,True),('HX-RANGE-04',150,260,8,20,False),('HX-RANGE-05',900,1500,60,110,True)]
  for code,amin,amax,dmin,dmax,holiday in ranges:
   if not s.query(Claim).filter_by(code=code).first():
    s.add(Claim(code=code,amount=(amin+amax)/2,distance=(dmin+dmax)/2,holiday=holiday,label=None,
     amount_min=amin,amount_max=amax,distance_min=dmin,distance_max=dmax,range_note='发票/里程单未齐，先按业务给的范围录入',
     note='范围票据；待新凭证收窄后重算异常概率'))
  s.commit();print({'users':s.query(User).count(),'claims':s.query(Claim).count()})
if __name__=='__main__':seed()
