// Phase-1 static specification checks, not GenVM contract tests.
// Reproduce with: node tools/check_phase1_design.mjs
import {readFileSync} from "node:fs";
import {dirname,join} from "node:path";
import {fileURLToPath} from "node:url";
const root=join(dirname(fileURLToPath(import.meta.url)),"..");
const spec=JSON.parse(readFileSync(join(root,"spec/phase1_design.json"),"utf8"));
function validate(d){
 let checks=0,simulations=0;
 function must(c,m){checks++;if(!c)throw Error("Check "+checks+": "+m)}
 const s=new Set(d.statuses),terminal=new Set(d.terminal),ops=d.actions;
 must(d.scope==="PHASE1_ONLY","phase boundary");
 must(d.version==="1.0.1-design","version");
 must(s.size===d.statuses.length,"unique states");
 must(Object.keys(ops).length===18,"18 defined ops");
 must(s.size===11,"11 states");
 must(d.denomination==="GEN_WEI_U256","value type");
 must(d.terms_commitment.domain==="SemanticEscrow.v1"&&d.terms_commitment.algorithm==="SHA-256","domain separated full terms");
 must(d.terms_commitment.input.includes("buyer_nonce")&&d.terms_commitment.input.includes("criteria_text"),"material contract terms included");
 must(d.invariants.includes("domain_separated_full_terms_commitment"),"full term commitment invariant");
 must(d.limits.milestones_min===1&&d.limits.milestones_max===5,"stages");
 must(d.limits.criteria_items_min===1&&d.limits.criteria_items_max===8,"rubric");
 must(d.limits.criteria_item_utf8_bytes_max<=512,"criteria bounded");
 must(d.limits.evidence_entries_min>=2&&d.limits.evidence_entries_max<=5,"evidence count");
 must(d.limits.evidence_raw_bytes_max===6000,"evidence body bound");
 must(d.limits.contract_challenges_per_milestone===1,"single challenge");
 const roles=new Set(["buyer","seller","anyone","buyer_or_seller"]);
 for(const [name,o]of Object.entries(ops)){
   must(s.has(o.to),"target "+name);
   must(roles.has(o.role),"role "+name);
   must(Array.isArray(o.from),"source list "+name);
   must(["NONE","LOCK_EXACT_DEPOSIT","PAYOUT_CURRENT","REFUND_ALL_REMAINING"].includes(o.money),"money "+name);
   for(const from of o.from){must(s.has(from),"source "+name);must(!terminal.has(from),"terminal reopened "+name)}
   if(o.money!=="NONE"&&name!=="create_deal")must(terminal.has(o.to),"transfer in nonterminal "+name);
   if(name.includes("inconclusive"))must(o.from.length===1&&o.to===o.from[0]&&o.money==="NONE","inconclusive may not pay "+name);
 }
 must(ops.create_deal.role==="buyer"&&ops.create_deal.money==="LOCK_EXACT_DEPOSIT","deposit");
 must(ops.submit_evidence.role==="seller","seller-only proof");
 must(ops.challenge_approval.role==="buyer"&&ops.challenge_rejection.role==="seller","loser-only challenge");
 must(ops.challenge_approval.guard.includes("unique_supplement")&&ops.challenge_rejection.guard.includes("unique_supplement"),"challenge new evidence");
 must(ops.settle_approved.money==="PAYOUT_CURRENT"&&ops.settle_rejected.money==="REFUND_ALL_REMAINING","payout/refund policy");
 must(ops.timeout_challenge_original_approved.guard.includes("initial=APPROVED")&&ops.timeout_challenge_original_rejected.guard.includes("initial=REJECTED"),"appeal fallback");
 must(d.cancel_overlay.confirm_cancel.role==="counterparty_only","no unilateral cancellation");
 must(d.cancel_overlay.expire_cancel.effect.includes("no refund"),"expired cancel cannot transfer");
 must(d.deal_states.includes("CLOSED_QUEUED")&&d.deal_states.includes("TERMINATED_QUEUED"),"deal endpoints");
 must(d.settlement_observation.PAYOUT_QUEUED.includes("not beneficiary credit"),"not received");
 const reached=new Set(["AWAITING_DELIVERY"]);
 for(let i=0;i<20;i++)for(const x of Object.values(ops))if(x.from.some(z=>reached.has(z)))reached.add(x.to);
 for(const t of s)must(["WAITING","CANCELED_REFUNDED_QUEUED"].includes(t)||reached.has(t),"unreachable "+t);
 for(const [inTime,outTime] of [["submit_evidence","timeout_unsubmitted"],["assess_approved","timeout_unassessed"],["challenge_approval","settle_approved"],["reassess_approved","timeout_challenge_original_approved"]]){
  must(ops[inTime].guard.includes("now<"),"before strict");
  must(ops[outTime].guard.includes("now>="),"expiration inclusive");
  for(const boundary of [1,1e4,2147483647])for(const t of [boundary-1,boundary,boundary+1])must((t<boundary)!==(t>=boundary),"deadline partition");
 }
 for(let count=1;count<=5;count++)for(let seed=1;seed<=100;seed++){
  const a=Array.from({length:count},(_,i)=>(i+1)*(seed+1)),deposit=a.reduce((x,y)=>x+y,0);
  for(let fail=0;fail<=count;fail++){
   let locked=deposit,payout=0,refund=0;const intents=new Set();
   for(let i=0;i<count;i++){
    must(!intents.has(i),"unique milestone intent");intents.add(i);
    if(i<fail){locked-=a[i];payout+=a[i];}
    else{const rest=a.slice(i).reduce((x,y)=>x+y,0);locked-=rest;refund+=rest;break;}
    must(locked>=0,"non-negative locked");
    must(deposit===locked+payout+refund,"in-flight conserved");
   }
   must(deposit===locked+payout+refund,"conserved on settlement");
   must(locked===0,"all obligations exhausted");
   must(intents.size===(fail<count?fail+1:count),"intent count");
   simulations++;
  }
 }
 const need=["deposit=remaining_locked+payout_queued_total+refund_queued_total","no_double_settlement","immutable_roles_terms","no_outbound_before_protocol_finalized","queued_transfer_not_recipient_credit","no_unilateral_cancel","no_cross_deal_ledger_moves"];
 for(const k of need)must(d.invariants.includes(k),"missing "+k);
 return {passed_checks:checks,abstract_ledger_scenarios:simulations,model_states:s.size,defined_actions:Object.keys(ops).length,scope:"DESIGN_ONLY_NOT_CONTRACT_TEST"};
}
console.log(JSON.stringify(validate(spec),null,2));
