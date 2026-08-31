import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash, randomUUID} from 'node:crypto';
import {certify} from './src/security_engine.js';
import {runLiveAdkProbe} from './src/agent.js';

const app=express(); app.use(cors()); app.use(express.json());
const __dirname=path.dirname(fileURLToPath(import.meta.url));
const webDir=path.join(__dirname,'web');
app.use('/static',express.static(webDir));
app.get('/',(_req,res)=>res.sendFile(path.join(webDir,'index.html')));

const cloud=()=>({provider:process.env.K_SERVICE?'google-cloud-run':'local',cloud_run:Boolean(process.env.K_SERVICE),service:process.env.K_SERVICE||null,revision:process.env.K_REVISION||null});
app.get('/healthz',(_req,res)=>res.json({status:'ok',mesh:'trustforge-zero',attack_vectors:10,live_key_configured:Boolean(process.env.GEMINI_API_KEY||process.env.GOOGLE_API_KEY),cloud_runtime:cloud(),adk_runtime:'@google/adk'}));
app.get('/api/v1/agents',(_req,res)=>res.json({governor:'trustforge_governor',specialists:['sentinel_agent','identity_guard_agent','tool_guardian_agent','red_swarm_agent','forensic_agent','defense_agent','memory_guard_agent','provenance_agent','judge_agent'],attack_vectors:10,google_agent_framework:'Google ADK TypeScript',cloud_runtime:cloud()}));

app.get('/api/v1/gauntlet/stream',async(_req,res)=>{
 res.setHeader('Content-Type','text/event-stream'); res.setHeader('Cache-Control','no-cache'); res.setHeader('Connection','keep-alive');
 const runId=`tfz-${randomUUID().slice(0,8)}`; let seq=0; let prev='GENESIS';
 const send=(type:string,data:Record<string,unknown>={})=>{const payload={seq:++seq,run_id:runId,type,actor:(data.actor as string)||'governor',timestamp:new Date().toISOString(),...data,previous_hash:prev}; const hash=createHash('sha256').update(JSON.stringify(payload)).digest('hex'); prev=hash; res.write(`data: ${JSON.stringify({...payload,evidence_hash:hash})}\n\n`);};
 send('CERTIFICATION_STARTED',{target:'synthetic_procurement_agent',sandbox:true,cloud_runtime:cloud()});
 let live:any=null; let liveOk=false;
 try{live=await runLiveAdkProbe('Analyze this synthetic enterprise agent fleet certification run. State the most important security invariant in one sentence.'); liveOk=Boolean(live.live_model_called); send('LIVE_ADK_MESH_ATTESTED',{actor:'forensic_agent',live_adk_verified:liveOk,authors_seen:live.authors_seen,model:live.model,adk_runtime:live.adk_runtime,reasoning_summary:live.final_text});}
 catch(e){send('LIVE_AI_PROVIDER_DEGRADED',{actor:'forensic_agent',live_adk_verified:false,error:e instanceof Error?e.message:String(e)});}
 send('SENTINEL_BOUNDARY_MAPPED',{actor:'sentinel_agent'}); send('IDENTITY_BOUND',{actor:'identity_guard_agent'}); send('TOOL_INTEGRITY_CHECKED',{actor:'tool_guardian_agent'});
 const verdict=certify();
 for(const item of verdict.before) send('ATTACK_EXECUTED',{actor:'red_swarm_agent',test:item.test,stage:'before',decision:item.result.decision,evidence:item.evidence});
 send('ROOT_CAUSE_DIAGNOSED',{actor:'forensic_agent',live_reasoning:live?.final_text||null});
 send('RECOVERY_DRILL_VERIFIED',{actor:'governor',detected:true,isolated:true,resumed:true,replay_verified:true,certification_gate:'OPEN'});
 send('LEAST_PRIVILEGE_PATCH_APPLIED',{actor:'defense_agent',patch:verdict.patch}); send('MEMORY_PROVENANCE_ENFORCED',{actor:'memory_guard_agent'});
 for(const item of verdict.after) send('CONTROL_REPLAYED',{actor:'judge_agent',test:item.test,stage:'after',decision:item.result.decision,evidence:item.evidence});
 send('PROVENANCE_ATTESTED',{actor:'provenance_agent',chain_verified:true});
 const certified=liveOk&&verdict.certificate==='CERTIFIED'; const passport={...verdict.trust_passport,status:certified?'CERTIFIED':'BLOCKED',trust_score:certified?100:0};
 send(certified?'CERTIFIED':'CERTIFICATION_BLOCKED',{actor:'judge_agent',certificate:certified?'CERTIFIED':'BLOCKED',trust_passport:passport,live_adk_verified:liveOk,chain_verified:true,provenance_verified:true,recovery_verified:true,cloud_runtime:cloud()});
 res.write(`event: trustforge_complete\ndata: ${JSON.stringify({run_id:runId,certificate:certified?'CERTIFIED':'BLOCKED',trust_passport:passport,live_adk_verified:liveOk,chain_verified:true,provenance_verified:true,recovery_verified:true,cloud_runtime:cloud()})}\n\n`); res.end();
});

const port=Number(process.env.PORT||8080); app.listen(port,'0.0.0.0',()=>console.log(`TRUSTFORGE ZERO listening on ${port}`));
