import {api,post} from './api/client.js';import {state} from './stores/session.js';import {routes,page} from './router/index.js';import {values,feedback} from './hooks/form.js';import {esc} from './utils/html.js';import * as claims from './pages/claims.js';import * as training from './pages/training.js';import * as evaluation from './pages/evaluation.js';import * as reviews from './pages/reviews.js';import * as triage from './pages/triage.js';
const pages=[claims,training,evaluation,reviews,triage];
const root=document.querySelector('#app');
async function load(){
 const [claims,trainings,reviews,ov]=await Promise.all(['/claims','/trainings','/reviews','/triage/overview'].map(x=>api(x)));
 state.claims=claims;state.trainings=trainings;state.reviews=reviews;
 state.scores=ov.scores;state.tasks=ov.tasks;state.evidences=ov.evidences;
 state.selected=state.trainings.find(t=>t.id===state.selected?.id)||state.trainings[0]||null;
}
function login(){root.innerHTML=`<div class="login"><section class="cover"><div class="eyebrow">HEXU / EXPENSE REVIEW 006</div><h1>让复核精力，<br>先到有疑点的票据。</h1><p>禾序咨询 · 财务审阅卷宗<br>从历史人工标签学习，保留每一次模型版本。<br>评分解释 / 阈值比较 / 独立复核判断 / 范围概率上下界</p></section><section><div class="eyebrow">CLAIM TRIAGE</div><h2>登录财务卷宗</h2><form id="login"><label>工作邮箱<input name="email" type="email" value="analyst@demo.local" required></label><label>密码<input name="password" type="password" value="Demo123!" required></label><button class="primary">进入报销复核</button></form><p id="error" class="error"></p><p>演示：admin / analyst / viewer @demo.local<br>密码：Demo123!</p></section></div>`;document.querySelector('form').onsubmit=e=>{e.preventDefault();run(async()=>{let d=await post('/auth/login',values(e.target));localStorage.setItem('token',d.token);state.user=d.user;await load();render()})}}
function render(){let n=Math.min(4,Math.max(0,page()));root.innerHTML=`<header><div class=brand>禾序 / 财务审阅卷宗 <span class=eyebrow>CLAIM TRIAGE</span></div><div>${esc(state.user.email)} · ${esc(state.user.role)} <button id=logout>退出</button></div></header><div class=layout><nav>${routes.map((r,i)=>`<button data-nav=${i} class="${i===n?'active':''}">0${i+1} ${r}</button>`).join('')}<p class=eyebrow>AUDIT FILES<br>2026 / HEXU</p></nav><main><div class=intro><div><div class=eyebrow>OPERATIONS RESEARCH / 0${n+1}</div><h1>${routes[n]}</h1><p>历史标签形成训练版本，留出指标帮助选择复核阈值。范围票据给出概率上下界，跨阈值先补证、高风险送复核；新凭证到达即重算。模型筛选候选，人工保留判断，负责人签核结果。</p></div><span class=tag>${state.claims.length} 笔样本</span></div><p id=error class=error></p>${pages[n].render()}</main></div>`;bind();if(state.user.role==='viewer')document.querySelectorAll('form button, #generate, #rescore-all, [data-claim], [data-retry], [data-complete]').forEach(b=>{b.disabled=true;b.textContent='观察员只读'})}
async function run(fn){try{await fn()}catch(e){feedback(e.message)}}
function bind(){
 document.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>location.hash=b.dataset.nav);
 document.querySelector('#logout').onclick=()=>{localStorage.removeItem('token');state.user=null;login()};
 for(let [id,path] of [['claim','/claims'],['training','/trainings'],['review','/reviews']]){
  let f=document.querySelector('#'+id);if(!f)continue;
  f.onsubmit=e=>{e.preventDefault();run(async()=>{
   let d=values(f);
   for(let k of ['amount_min','amount_max','distance_min','distance_max','threshold','label'])if(k in d)d[k]=d[k]===''?null:Number(d[k]);
   if('holiday'in d)d.holiday=d.holiday==='true';
   let record=d.record_id;delete d.record_id;
   let created=record?await api(path+'/'+record,{method:'PUT',body:JSON.stringify(d)}):await post(path,d);
   if(id==='training'){state.selected=created;location.hash='2'}
   await load();render();
  })};
 }
 let ev=document.querySelector('#evidence');
 if(ev)ev.onsubmit=e=>e.preventDefault(),run(async()=>{
  let d=values(ev);for(let k of ['claim_id','amount_min','amount_max','distance_min','distance_max'])d[k]=Number(d[k]);
  let cid=d.claim_id;delete d.claim_id;
  await post(`/claims/${cid}/evidence`,d);feedback('凭证已录入，旧评分失效并已按新范围重算');await load();render();
 });
 document.querySelectorAll('[data-training]').forEach(b=>b.onclick=()=>run(async()=>{state.selected=await api('/trainings/'+b.dataset.training);location.hash='2';render()}));
 document.querySelectorAll('[data-approve]').forEach(b=>b.onclick=()=>run(async()=>{await post('/reviews/'+b.dataset.approve+'/approve',{});await load();render()}));
 document.querySelectorAll('[data-claim]').forEach(b=>b.onclick=()=>run(async()=>{await post('/triage/tasks/'+b.dataset.claim+'/claim',{});feedback('领取成功，同一票据不会被重复领走');await load();render()}));
 document.querySelectorAll('[data-complete]').forEach(b=>b.onclick=()=>run(async()=>{
  let note=prompt('填写处理结果与证据说明（可留空）：')||'';
  await api('/triage/tasks/'+b.dataset.complete+'/complete',{method:'POST',body:JSON.stringify({note})});await load();render();
 }));
 document.querySelectorAll('[data-retry]').forEach(b=>b.onclick=()=>run(async()=>{let t=await post('/triage/tasks/'+b.dataset.retry+'/retry',{});feedback('已按当前评分重新派单为 '+t.state+'，不重复派单');await load();render()}));
 let refresh=document.querySelector('#refresh');if(refresh)refresh.onclick=()=>run(async()=>{await load();render()});
 let rt=document.querySelector('#refresh-triage');if(rt)rt.onclick=()=>run(async()=>{await load();render()});
 let rescore=document.querySelector('#rescore-all');if(rescore)rescore.onclick=()=>run(async()=>{let r=await post('/triage/rescore',{});feedback('已重算 '+r.rescored+' 笔票据');await load();render()});
 let gen=document.querySelector('#generate');if(gen)gen.onclick=()=>run(async()=>{let r=await post('/trainings/'+state.selected.id+'/reviews',{});await load();location.hash='3';render();feedback('已新增 '+r.created+' 个复核任务')});
 let download=document.querySelector('#download');if(download)download.onclick=()=>run(async()=>{let d=await api('/trainings/'+state.selected.id+'/export');let u=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));let a=document.createElement('a');a.href=u;a.download='claim-triage-'+d.id+'.json';a.click();URL.revokeObjectURL(u)});
}
window.onhashchange=()=>{if(state.user)render()};if(localStorage.getItem('token'))run(async()=>{try{state.user=await api('/me');await load();render()}catch(e){localStorage.removeItem('token');login();feedback(e.message)}});else login();
