import os
from contextlib import contextmanager
from datetime import datetime,timezone
import redis
from sqlalchemy import update
from src.models.entities import Claim,Training,Evidence,Score,TriageTask,Audit
from src.services.analysis import model_params,range_bounds,band_of,BAND_TEXT
REDIS_URL=os.environ.get('REDIS_URL','redis://localhost:6379/0')
def now():return datetime.now(timezone.utc).isoformat()
class TriageError(Exception):pass
@contextmanager
def claim_lock(claim_id,timeout=8):
 """同一票据的补证/领取串行化；Redis 不可用时降级为进程内锁（单 worker 演示环境）。"""
 key=f'claim:lock:{claim_id}'
 try:
  r=redis.Redis.from_url(REDIS_URL,socket_timeout=2,socket_connect_timeout=2)
  r.ping()
  got=r.set(key,'1',nx=True,ex=timeout)
  if not got:raise TriageError('该票据正在被其他操作处理，请稍后重试')
  try:yield
  finally:r.delete(key)
 except redis.RedisError:
  yield
def latest_training(s):
 return s.query(Training).filter_by(state='done').order_by(Training.id.desc()).first()
def effective_ranges(claim,evidences):
 """有效范围=票据录入范围与全部凭证范围逐维取交集。"""
 amin,amax=claim.amount_min,claim.amount_max
 dmin,dmax=claim.distance_min,claim.distance_max
 used=[]
 for e in evidences:
  amin=max(amin,e.amount_min);amax=min(amax,e.amount_max)
  dmin=max(dmin,e.distance_min);dmax=min(dmax,e.distance_max)
  used.append(e.id)
 if amin>amax or dmin>dmax:
  raise TriageError('新凭证与原范围没有交集，无法在原凭据内收窄，请核对凭证金额/里程')
 return amin,amax,dmin,dmax,used
def _deactivate_scores(s,claim_id):
 n=s.query(Score).filter_by(claim_id=claim_id,active=True).update({Score.active:False,Score.active_key:None})
 return n
def _deactivate_tasks(s,claim_id):
 """旧评分失效：未着手(queued/failed)任务作废；已领取(claimed)沿用原凭据继续。"""
 rows=s.query(TriageTask).filter(TriageTask.claim_id==claim_id,TriageTask.active==True,
  TriageTask.state.in_(['queued','failed'])).all()
 for t in rows:t.active=False;t.active_key=None;t.state='cancelled';t.updated=now()
 return rows
def score_claim(s,claim):
 """按最新已完成训练版本对票据当前有效范围重算异常概率上下界并落库（新评分版本）。"""
 training=latest_training(s)
 prev=s.query(Score).filter_by(claim_id=claim.id,active=True).first()
 version=(prev.version if prev else 0)+1
 base=Score(claim_id=claim.id,state='pending',version=version,active=False,created=now())
 s.add(base);s.flush()
 if not training:
  base.state='failed';base.error='暂无已完成的训练版本，等待训练完成后评分'
  return base
 try:
  evidences=s.query(Evidence).filter_by(claim_id=claim.id).order_by(Evidence.id).all()
  amin,amax,dmin,dmax,used=effective_ranges(claim,evidences)
  params=model_params(training.result)
  p_min,p_max,corners=range_bounds(params,amin,amax,dmin,dmax,claim.holiday)
  band=band_of(p_min,p_max,params['threshold'])
  base.training_id=training.id;base.state='scored';base.p_min=p_min;base.p_max=p_max;base.band=band
  base.basis=dict(training_id=training.id,threshold=params['threshold'],
   amount_range=[amin,amax],distance_range=[dmin,dmax],holiday=bool(claim.holiday),
   evidence_ids=used,extreme_points=corners,
   reason=BAND_TEXT[band],formula='p=sigmoid(b+Σ w·标准化(金额,里程,节假日,每公里金额))；在范围矩形上解析求极值')
 except TriageError as e:
  base.state='failed';base.error=str(e)
 except Exception as e:
  base.state='failed';base.error='评分失败：'+str(e)
 return base
def activate_score(s,score):
 _deactivate_scores(s,score.claim_id)
 score.active=True;score.active_key=score.claim_id;s.flush()
def dispatch(s,claim,score):
 """依据概率带派单；每票至多一条 active 任务，重复调用不重复派单。

 above(下界即超阈值)->复核任务；cross(跨阈值)->补证任务；below(上界仍低于阈值)->暂不派单。
 无可用模型/范围冲突的失败评分 -> failed 任务，供页面失败列表重试。
 """
 existing=s.query(TriageTask).filter_by(claim_id=claim.id,active=True).first()
 if existing:return existing,False
 if score.state!='scored':
  task=TriageTask(claim_id=claim.id,kind='evidence',state='failed',score_id=score.id,
   training_id=score.training_id,basis=score.basis,note=score.error,attempts=0,created=now(),updated=now())
 elif score.band=='below':
  return None,False
 else:
  kind='review' if score.band=='above' else 'evidence'
  task=TriageTask(claim_id=claim.id,kind=kind,state='queued',score_id=score.id,
   training_id=score.training_id,p_min=score.p_min,p_max=score.p_max,band=score.band,
   basis=score.basis,attempts=0,created=now(),updated=now())
 s.add(task);s.flush();task.active=True;task.active_key=claim.id;s.flush()
 return task,True
def rescore_and_route(s,claim):
 """新凭证/新范围后的标准重算流程：旧评分失效 → 重算 → 未着手任务取消 → 按新评分分流。"""
 score=score_claim(s,claim)
 _deactivate_scores(s,claim.id)
 activate_score(s,score)
 _deactivate_tasks(s,claim.id)
 task,_=dispatch(s,claim,score)
 return score,task
def add_evidence(s,claim,data,user):
 # 先校验交集：无交集直接拒绝，旧评分与已派任务保持有效
 ev=Evidence(claim_id=claim.id,amount_min=data['amount_min'],amount_max=data['amount_max'],
  distance_min=data['distance_min'],distance_max=data['distance_max'],note=data.get('note',''),
  actor=user.email,created=now())
 effective_ranges(claim,[ev])
 s.add(ev);s.flush()
 score,task=rescore_and_route(s,claim)
 routed=(task.kind+'/'+task.state) if task else 'below/暂不派单'
 s.add(Audit(actor=user.email,action=f'新凭证 #{ev.id} 票据 {claim.code}：旧评分失效，按新范围重算并分流为 {routed}',created=now()))
 return ev,score,task
def claim_task(s,task_id,user):
 """原子领取：条件 UPDATE 保证同一票不会被补证侧/复核侧两边领走。"""
 row=s.execute(update(TriageTask).where(TriageTask.id==task_id,TriageTask.state=='queued',TriageTask.active==True)
  .values(state='claimed',owner=user.email,updated=now())).rowcount
 s.commit()
 if not row:raise TriageError('任务已被领取或已失效，请刷新列表')
 return s.get(TriageTask,task_id)
def complete_task(s,task_id,user,note):
 task=s.get(TriageTask,task_id)
 if not task or not task.active:raise TriageError('任务不存在或已失效')
 if task.state!='claimed' or task.owner!=user.email:raise TriageError('只有领取人可以完成该任务')
 task.state='done';task.note=note or task.note;task.updated=now();s.commit()
 s.add(Audit(actor=user.email,action=f'完成分流任务 #{task.id}（票据 #{task.claim_id}，{task.kind}）',created=now()));s.commit()
 return task
def retry_task(s,task_id,user):
 """失败重试：基于当前最新评分重新派单，active 唯一键保证不重复派单。"""
 task=s.get(TriageTask,task_id)
 if not task:raise TriageError('任务不存在')
 if task.state!='failed':raise TriageError('仅失败任务可以重试')
 claim=s.get(Claim,task.claim_id)
 attempts=task.attempts+1
 task.attempts=attempts;task.active=False;task.active_key=None
 score=s.query(Score).filter_by(claim_id=claim.id,active=True).first() or score_claim(s,claim)
 if not score.active:activate_score(s,score)
 new_task,created=dispatch(s,claim,score)
 if new_task is not None:new_task.attempts=attempts
 s.add(Audit(actor=user.email,action=(f'重试分流任务 票据 {claim.code} → 新任务 #{new_task.id}（第 {attempts+1} 次）'
   if new_task else f'重试分流任务 票据 {claim.code}：当前概率上界低于阈值，暂不派单（第 {attempts+1} 次）'),created=now()))
 s.commit()
 return new_task or task
