import json,hashlib
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
 return dict(train_n=len(train_rows),test_n=len(test_rows),label_counts=counts,metrics=metrics(scored,threshold),threshold_comparison=[metrics(scored,t) for t in (.3,.5,.7)],holdout=scored,pending=predictions,coefficients=[{'feature':f,'coefficient':float(c)} for f,c in zip(FEATURES,model.named_steps['logit'].coef_[0])],train_codes=[r['code'] for r in train_rows],test_codes=[r['code'] for r in test_rows],scaler_mean=model.named_steps['scale'].mean_.tolist(),seed=SEED,checksum=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),warning='评分只用于排定人工复核顺序。标签不进入特征；标准化只在训练集拟合。留出集为演示评估集，反复调阈值后不再是最终独立验收集。系数为标准化关联，不代表因果。')
