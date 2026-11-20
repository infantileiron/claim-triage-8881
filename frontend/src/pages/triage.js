import {state} from '../stores/session.js';import {esc} from '../utils/html.js';import {badge} from '../components/common/status.js';import {select} from '../components/common/fields.js';import {BAND_LABEL,KIND_LABEL,TASK_STATE_LABEL} from '../constants/enums.js';
const pct=v=>v==null?'—':(v*100).toFixed(2)+'%';
const claimOf=id=>state.claims.find(c=>c.id===id);
const bandTag=b=>b?`<span class="tag band-${b}">${esc(BAND_LABEL[b]||b)}</span>`:'—';
function basisBlock(basis,error){
 if(error)return `<p class="error">${esc(error)}</p>`;
 if(!basis)return '<p>暂无依据</p>';
 const ar=basis.amount_range||[null,null],dr=basis.distance_range||[null,null];
 const fmt=(v,d)=>v==null?'—':Number(v).toFixed(d);
 return `<details class="basis"><summary>评分依据</summary>
 <p>训练版本 #${esc(basis.training_id)} · 阈值 ${pct(basis.threshold)} · 节假日 ${basis.holiday?'是':'否'}</p>
 <p>有效金额范围 ${fmt(ar[0],2)} ~ ${fmt(ar[1],2)} 元；有效里程 ${fmt(dr[0],1)} ~ ${fmt(dr[1],1)} km${basis.evidence_ids?.length?`；凭证 #${basis.evidence_ids.join(', #')}`:'；无新凭证'}</p>
 <p>${esc(basis.reason||'')}</p><p class="eyebrow">${esc(basis.formula||'')}</p></details>`;
}
function taskCard(t){
 const c=claimOf(t.claim_id);
 return `<article class="rec">
 <h3>任务 #${t.id} · ${esc(c?.code||('#'+t.claim_id))} · ${esc(KIND_LABEL[t.kind]||t.kind)} ${badge(TASK_STATE_LABEL[t.state]||t.state)} ${t.band?bandTag(t.band):''}</h3>
 <p>概率区间 ${pct(t.p_min)} ~ ${pct(t.p_max)}${t.owner?` · 领取人 ${esc(t.owner)}`:''} · 尝试 ${t.attempts+1} 次</p>
 ${basisBlock(t.basis,'')}
 ${t.note?`<p>处理说明：${esc(t.note)}</p>`:''}
 <p class="actions">
 ${t.state==='queued'?`<button data-claim="${t.id}">领取任务</button>`:''}
 ${t.state==='claimed'?`<button data-complete="${t.id}">填写处理结果</button>`:''}
 ${t.state==='failed'?`<button data-retry="${t.id}">失败重试</button>`:''}
 </p></article>`;
}
export function render(){
 const pending=state.scores.filter(x=>x.state==='pending');
 const failed=state.tasks.filter(t=>t.state==='failed');
 const active=state.tasks.filter(t=>t.active&&t.state!=='failed');
 const claimOptions=state.claims.map(c=>[c.id,`#${c.id} ${c.code}`]);
 return `<div class="split"><section class="panel">
 <div class="result-head"><h2>范围票据概率上下界与分流</h2><button id="refresh-triage">刷新</button></div>
 <p class="notice">金额/里程只拿到范围时，用最新已完成训练版本在范围矩形上求异常概率最小值与最大值：上界仍低于阈值暂不派单；区间跨越阈值先补证；下界即高于阈值直接送复核。新凭证到达后旧评分立即失效并按新范围重算，已领取任务沿用原凭据，未领取任务作废后按新评分分流。</p>
 <h3>待评分（${pending.length}）</h3>
 ${pending.map(x=>{const c=claimOf(x.claim_id);return `<p>#${x.claim_id} ${esc(c?.code||'')} · ${esc(x.error||'等待训练版本')}</p>`}).join('')||'<p>无待评分票据。</p>'}
 <h3>分流任务（${active.length}）</h3>
 ${active.map(taskCard).join('')||'<p>暂无活动任务。</p>'}
 <h3>失败（${failed.length}）</h3>
 ${failed.map(taskCard).join('')||'<p>无失败任务。</p>'}
 <h3>评分版本（含已失效）</h3>
 <div class=scroll><table><thead><tr><th>票据</th><th>版本</th><th>状态</th><th>概率下界</th><th>概率上界</th><th>分带</th><th>有效</th></tr></thead><tbody>
 ${state.scores.map(x=>{const c=claimOf(x.claim_id);return `<tr><td>${esc(c?.code||x.claim_id)}</td><td>v${x.version}</td><td>${esc(x.state)}</td><td>${pct(x.p_min)}</td><td>${pct(x.p_max)}</td><td>${x.band?esc(BAND_LABEL[x.band]||x.band):'—'}</td><td>${x.active?'当前':'已失效'}</td></tr>`}).join('')}
 </tbody></table></div>
 <h3>凭证记录</h3>
 <div class=scroll><table><thead><tr><th>凭证</th><th>票据</th><th>金额范围</th><th>里程范围</th><th>录入人</th><th>说明</th></tr></thead><tbody>
 ${state.evidences.map(e=>{const c=claimOf(e.claim_id);return `<tr><td>#${e.id}</td><td>${esc(c?.code||e.claim_id)}</td><td>${e.amount_min.toFixed(2)}~${e.amount_max.toFixed(2)}</td><td>${e.distance_min.toFixed(1)}~${e.distance_max.toFixed(1)}</td><td>${esc(e.actor)}</td><td>${esc(e.note)}</td></tr>`}).join('')||'<tr><td colspan=6>暂无凭证。</td></tr>'}
 </tbody></table></div>
 </section>
 <aside class="side">
 <h2>录入新凭证</h2>
 <form id="evidence">
 ${select('票据','claim_id',claimOptions)}
 <label>金额下界 / 元<input name="amount_min" type="number" required min="0" max="100000" step="0.01"></label>
 <label>金额上界 / 元<input name="amount_max" type="number" required min="0" max="100000" step="0.01"></label>
 <label>里程下界 / km<input name="distance_min" type="number" required min="0" max="10000" step="0.1"></label>
 <label>里程上界 / km<input name="distance_max" type="number" required min="0" max="10000" step="0.1"></label>
 <label>凭证说明<textarea name="note" rows="3"></textarea></label>
 <button class="primary">提交并重算</button>
 </form>
 <p>有效范围=原范围与全部凭证范围的交集；无交集会被拒绝，旧评分保持有效。</p>
 <p><button id="rescore-all">按最新版本全部重算</button></p>
 </aside></div>`;
}
