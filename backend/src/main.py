import os,logging
from contextlib import asynccontextmanager
from sqlalchemy import inspect,text
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from src.config.database import Base,engine
from src.models import entities
from src.routes.api import router
from src.middlewares.request import RequestId,SecurityHeaders
def _migrate():
 """对旧库补齐范围分流所需列/表；全新库由 metadata 直接建出。"""
 Base.metadata.create_all(engine)
 insp=inspect(engine)
 claim_cols={c['name'] for c in insp.get_columns('claims')}
 with engine.begin() as conn:
  for col,ddl in [('amount_min','FLOAT'),('amount_max','FLOAT'),('distance_min','FLOAT'),('distance_max','FLOAT'),('range_note','VARCHAR(1000)')]:
   if col not in claim_cols:conn.execute(text(f'ALTER TABLE claims ADD COLUMN {col} {ddl}'))
@asynccontextmanager
async def lifespan(app):
 _migrate()
 if os.getenv('SEED_DEMO')=='true':
  try:
   from scripts.seed_demo import seed
   seed()
  except Exception:logging.exception('seed failed')
 yield
app=FastAPI(title='报销异常分类复核',lifespan=lifespan)
app.add_middleware(RequestId);app.add_middleware(SecurityHeaders)
app.include_router(router)
@app.get('/health')
def health():
 from sqlalchemy import text as t
 import redis
 with engine.connect() as c:c.execute(t('SELECT 1'))
 try:redis.Redis.from_url(os.environ['REDIS_URL']).ping()
 except Exception:return {'status':'degraded','detail':'redis 不可用，锁降级为单进程模式'}
 return {'status':'ok'}
@app.exception_handler(Exception)
async def errors(request:Request,exc:Exception):
 logging.exception('request failed');return JSONResponse(status_code=500,content={'detail':'服务暂时异常，请稍后重试'})
