/** @typedef {{id:number,code:string,amount:number,distance:number,holiday:boolean,label:0|1|null,note:string,amount_min:number|null,amount_max:number|null,distance_min:number|null,distance_max:number|null,range_note:string}} Claim */
/** @typedef {{id:number,name:string,threshold:number,state:string,result:object}} Training */
/** @typedef {{id:number,claim_id:number,training_id:number,score:number,decision:string,status:string}} Review */
/** @typedef {{id:number,claim_id:number,training_id:number|null,state:'pending'|'scored'|'failed',p_min:number|null,p_max:number|null,band:'below'|'cross'|'above'|null,basis:object|null,error:string,active:boolean,version:number,created:string}} Score */
/** @typedef {{id:number,claim_id:number,kind:'evidence'|'review',state:'queued'|'claimed'|'done'|'cancelled'|'failed',score_id:number,training_id:number,p_min:number,p_max:number,band:string,basis:object,owner:string,attempts:number,note:string,active:boolean,created:string,updated:string}} TriageTask */
/** @typedef {{id:number,claim_id:number,amount_min:number,amount_max:number,distance_min:number,distance_max:number,note:string,actor:string,created:string}} Evidence */
