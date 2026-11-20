ROLES=('admin','analyst','viewer')
STATES=('queued','running','done','failed')
DECISIONS=('pending','valid','flagged')
LABELS=(0,1)
# 范围分流：任务类型 / 任务状态 / 评分状态 / 概率带
TRIAGE_KINDS=('evidence','review')
TASK_STATES=('queued','claimed','done','cancelled','failed')
SCORE_STATES=('pending','scored','failed')
BANDS=('below','cross','above')
