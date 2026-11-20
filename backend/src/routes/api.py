import os,json
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Claim,Training,Review,Audit,Evidence,Score,TriageTask
from src.schemas.business import Login,ClaimInput,TrainingInput,ReviewInput,EvidenceInput,CompleteInput
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump
from src.services import triage
from src.services.triage import TriageError,claim_lock,rescore_and_route,add_evidence,claim_task,complete_task,retry_task
from src.controllers.business import ensure_training
router=APIRouter()
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/claims')
def claims(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Claim).order_by(Claim.id).all()]
def _apply_ranges(r,data):
 d=data.model_dump()
 for k,v in d.items():setattr(r,k,v)
 # 点值字段取范围中点，兼容既有训练快照与评分
 r.amount=(data.amount_min+data.amount_max)/2
 r.distance=(data.distance_min+data.distance_max)/2
 return r
@router.post('/claims')
def create_claim(data:ClaimInput,u=Depends(editor),s=Depends(db)):
 r=Claim(**data.model_dump());_apply_ranges(r,data);s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'报销编号重复')
 s.refresh(r)
 with claim_lock(r.id):
  score,task=rescore_and_route(s,r);s.commit()
 routed=(task.kind+'/'+task.state) if task else 'below/暂不派单'
 audit(s,u,f'录入报销 {r.code}（范围金额 {r.amount_min:.2f}~{r.amount_max:.2f}，里程 {r.distance_min:.1f}~{r.distance_max:.1f}），分流 {routed}')
 return dump(r)
@router.put('/claims/{i}')
def edit_claim(i:int,data:ClaimInput,u=Depends(editor),s=Depends(db)):
 r=s.get(Claim,i)
 if not r:raise HTTPException(404,'报销样本不存在')
 with claim_lock(i):
  _apply_ranges(r,data)
  score,task=rescore_and_route(s,r)
  try:s.commit()
  except IntegrityError:s.rollback();raise HTTPException(409,'报销编号重复')
 routed=(task.kind+'/'+task.state) if task else 'below/暂不派单'
 audit(s,u,f'修订报销 {r.code} 范围/字段，旧评分失效并重新分流为 {routed}');return dump(r)
@router.get('/trainings')
def trainings(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Training).order_by(Training.id.desc()).all()]
@router.post('/trainings')
def train(data:TrainingInput,u=Depends(editor),s=Depends(db)):
 rows=[dump(r) for r in s.query(Claim).order_by(Claim.id).all()];r=Training(**data.model_dump(),result={'snapshot':rows});s.add(r);s.commit()
 try:redis.Redis.from_url(os.environ['REDIS_URL']).rpush('claim:trainings',r.id)
 except redis.RedisError:r.state='failed';r.error='队列暂不可用，请稍后重新提交';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'提交训练 '+str(r.id));return dump(r)
@router.get('/trainings/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(ensure_training(s,i))
@router.get('/trainings/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_training(s,i)
 if r.state!='done':raise HTTPException(409,'仅成功训练可导出')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="claim-triage-{i}.json"'})
@router.post('/trainings/{i}/reviews')
def generate(i:int,u=Depends(editor),s=Depends(db)):
 r=ensure_training(s,i)
 if r.state!='done':raise HTTPException(409,'训练完成后才能生成复核任务')
 created=0
 for p in r.result['pending']:
  if p['score']>=r.threshold and not s.query(Review).filter_by(training_id=i,claim_id=p['id']).first():s.add(Review(training_id=i,claim_id=p['id'],score=p['score']));created+=1
 s.commit();audit(s,u,'生成风险复核 '+str(i));return {'created':created}
@router.get('/reviews')
def reviews(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Review).order_by(Review.id.desc()).all()]
@router.put('/reviews/{i}')
def review(i:int,data:ReviewInput,u=Depends(editor),s=Depends(db)):
 r=s.get(Review,i)
 if not r:raise HTTPException(404,'复核任务不存在')
 if r.status=='approved':raise HTTPException(409,'已签核复核不可修改')
 r.decision=data.decision;r.note=data.note;s.commit();audit(s,u,'人工复核 '+str(i));return dump(r)
@router.post('/reviews/{i}/approve')
def approve(i:int,u=Depends(admin),s=Depends(db)):
 r=s.get(Review,i)
 if not r:raise HTTPException(404,'复核任务不存在')
 if r.decision=='pending' or r.status!='draft':raise HTTPException(409,'先填写人工判断，且只签核一次')
 r.status='approved';s.commit();audit(s,u,'签核复核 '+str(i));return dump(r)
# ---------------- 范围分流 ----------------
@router.get('/triage/overview')
def overview(u=Depends(current),s=Depends(db)):
 scores=s.query(Score).filter_by(active=True).all();tasks=s.query(TriageTask).filter_by(active=True).all()
 return {'scores':[dump(x) for x in scores],'tasks':[dump(x) for x in tasks],
  'evidences':[dump(x) for x in s.query(Evidence).order_by(Evidence.id.desc()).all()]}
@router.post('/claims/{i}/evidence')
def evidence(i:int,data:EvidenceInput,u=Depends(editor),s=Depends(db)):
 claim=s.get(Claim,i)
 if not claim:raise HTTPException(404,'报销样本不存在')
 try:
  with claim_lock(i):
   ev,score,task=add_evidence(s,claim,data.model_dump(),u);s.commit()
 except TriageError as e:raise HTTPException(409,str(e))
 return {'evidence':dump(ev),'score':dump(score),'task':dump(task)}
@router.post('/triage/tasks/{i}/claim')
def take(i:int,u=Depends(editor),s=Depends(db)):
 task=s.get(TriageTask,i)
 if not task:raise HTTPException(404,'分流任务不存在')
 try:
  with claim_lock(task.claim_id):return dump(claim_task(s,i,u))
 except TriageError as e:raise HTTPException(409,str(e))
@router.post('/triage/tasks/{i}/complete')
def finish(i:int,data:CompleteInput,u=Depends(editor),s=Depends(db)):
 try:return dump(complete_task(s,i,u,data.note))
 except TriageError as e:raise HTTPException(409,str(e))
@router.post('/triage/tasks/{i}/retry')
def retry(i:int,u=Depends(editor),s=Depends(db)):
 task=s.get(TriageTask,i)
 if not task:raise HTTPException(404,'分流任务不存在')
 try:
  with claim_lock(task.claim_id):return dump(retry_task(s,i,u))
 except TriageError as e:raise HTTPException(409,str(e))
@router.post('/triage/rescore')
def rescore_all(u=Depends(editor),s=Depends(db)):
 n=0
 for c in s.query(Claim).order_by(Claim.id).all():
  with claim_lock(c.id):rescore_and_route(s,c);n+=1
 s.commit();audit(s,u,f'按最新训练版本重算 {n} 笔范围票据评分并分流')
 return {'rescored':n}
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
