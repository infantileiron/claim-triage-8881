import json,hashlib,math
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
SEED=3106
FEATURES=['金额','里程','节假日','每公里金额']
def features(row):return [row['amount'],row['distance'],int(row['holiday']),row['amount']/(row['distance']+1)]
def metrics(rows,threshold):
 tp=sum(r['label']==1 and r['score']>=threshold for r in rows);fp=sum(r['label']==0 and r['score']>=threshold for r in rows)
 fn=sum(r['label']==1 and r['score']<threshold for r in rows);tn=sum(r['label']==0 and r['score']<threshold for r in rows)
 precision=tp/(tp+fp) if tp+fp else 0;recall=tp/(tp+fn) if tp+fn else 0
 return dict(threshold=threshold,tp=tp,fp=fp,fn=fn,tn=tn,precision=precision,recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0,accuracy=(tp+tn)/len(rows) if rows else 0)
def train(rows,threshold):
 labelled=[r for r in rows if r['label'] is not None];counts={str(v):sum(r['label']==v for r in labelled) for v in (0,1)}
 if len(labelled)<40 or min(counts.values())<10:raise ValueError('至少40个已标注样本，且正常/异常各至少10个；请先补充人工标签')
 train_rows,test_rows=train_test_split(labelled,test_size=.25,random_state=SEED,stratify=[r['label'] for r in labelled])
 model=Pipeline([('scale',StandardScaler()),('logit',LogisticRegression(random_state=SEED,max_iter=1000,C=1.0))])
 model.fit([features(r) for r in train_rows],[r['label'] for r in train_rows])
 scored=[{'id':r['id'],'code':r['code'],'label':r['label'],'score':float(p)} for r,p in zip(test_rows,model.predict_proba([features(r) for r in test_rows])[:,1])]
 pending=[r for r in rows if r['label'] is None]
 predictions=[{'id':r['id'],'code':r['code'],'score':float(p)} for r,p in zip(pending,model.predict_proba([features(r) for r in pending])[:,1])] if pending else []
 return dict(train_n=len(train_rows),test_n=len(test_rows),label_counts=counts,metrics=metrics(scored,threshold),threshold_comparison=[metrics(scored,t) for t in (.3,.5,.7)],holdout=scored,pending=predictions,coefficients=[{'feature':f,'coefficient':float(c)} for f,c in zip(FEATURES,model.named_steps['logit'].coef_[0])],intercept=float(model.named_steps['logit'].intercept_[0]),scaler_mean=model.named_steps['scale'].mean_.tolist(),scaler_scale=model.named_steps['scale'].scale_.tolist(),train_codes=[r['code'] for r in train_rows],test_codes=[r['code'] for r in test_rows],seed=SEED,checksum=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),warning='评分只用于排定人工复核顺序。标签不进入特征；标准化只在训练集拟合。留出集为演示评估集，反复调阈值后不再是最终独立验收集。系数为标准化关联，不代表因果。')
def model_params(result):
 """从冻结训练结果还原标准化逻辑回归参数，供范围上下界评分复用同一版本。"""
 return dict(w=[float(c['coefficient']) for c in result['coefficients']],intercept=float(result['intercept']),
  mean=[float(x) for x in result['scaler_mean']],scale=[float(x) for x in result['scaler_scale']],
  threshold=float(result['metrics']['threshold']),seed=result.get('seed',SEED))
def _sigmoid(z):
 if z>=0:return 1/(1+math.exp(-z))
 ez=math.exp(z);return ez/(1+ez)
def _linear(w,b,mean,scale,a,d,h):
 x=[a,d,h,a/(d+1)]
 return b+sum(wi*(xi-mi)/si for wi,xi,mi,si in zip(w,x,mean,scale))
def range_bounds(params,amount_min,amount_max,distance_min,distance_max,holiday):
 """在金额/里程范围矩形上求异常概率的全局最小值与最大值。

 线性预测子 g(a,d)=c0*a+c2*d+c3*a/(d+1)+c4：对 a 为线性，对 d 的极值
 只可能出现在 d 边界或驻点 d*=sqrt(|c3*a/c2|)-1，故解析枚举即可，不依赖网格。
 """
 w=params['w'];b=params['intercept'];mean=params['mean'];scale=params['scale'];h=int(bool(holiday))
 c0=w[0]/scale[0];c2=w[1]/scale[1];c3=w[3]/scale[3]
 c4=b-sum(w[i]*mean[i]/scale[i] for i in range(4))+w[2]*h/scale[2]
 def g(a,d):return c0*a+c2*d+c3*a/(d+1)+c4
 ds=[distance_min,distance_max]
 candidates=[]
 for a in (amount_min,amount_max):
  for d in ds:candidates.append((a,d))
  if c2!=0:
   r2=c3*a/c2
   if r2>0:
    d_star=math.sqrt(r2)-1
    if distance_min<d_star<distance_max:candidates.append((a,d_star))
 vals=[g(a,d) for a,d in candidates]
 z_min,z_max=min(vals),max(vals)
 return _sigmoid(z_min),_sigmoid(z_max),sorted(set((round(a,6),round(d,6)) for a,d in candidates))
def band_of(p_min,p_max,threshold):
 if p_max<threshold:return 'below'
 if p_min>=threshold:return 'above'
 return 'cross'
BAND_TEXT={'below':'概率上界低于阈值，暂不派单','cross':'概率区间跨越阈值，先补证收窄范围','above':'概率下界即高于阈值，直接送复核'}
