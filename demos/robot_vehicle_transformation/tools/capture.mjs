// Deno: local Chrome remote-debugging port 9222; local preview server port 8766.
// deno run --allow-net=127.0.0.1:9222 --allow-read --allow-write capture.mjs probe OUTPUT_DIR
const mode=Deno.args[0]||'probe', output=Deno.args[1]||'frames';
await Deno.mkdir(output,{recursive:true});
const tabs=await(await fetch('http://127.0.0.1:9222/json')).json();
const socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>socket.onopen=r);let id=0;const pending=new Map();
socket.onmessage=e=>{const d=JSON.parse(e.data);if(pending.has(d.id)){pending.get(d.id)(d);pending.delete(d.id);}};
async function send(method,params={}){const key=++id;const p=new Promise(r=>pending.set(key,r));socket.send(JSON.stringify({id:key,method,params}));const d=await p;if(d.error)throw Error(JSON.stringify(d.error));return d.result;}
async function evaluate(expression){const d=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(d.exceptionDetails)throw Error(JSON.stringify(d.exceptionDetails));return d.result.value;}
await send('Page.enable');
const url='http://127.0.0.1:8766/showcase.html?capture='+Date.now();
await send('Page.navigate',{url});
for(let i=0;i<100;i++){if(await evaluate('location.href==='+JSON.stringify(url)+' && Boolean(window.MotionLab)'))break;await new Promise(r=>setTimeout(r,100));}
await evaluate('MotionLab.stop()');
let records=[];
const shots=mode==='probe'?[['cross',0],['cross',.75],['cross',1.25],['cross',1.7],['cross',2.1],['cross',2.4],['cross',2.8],['cross',4],['run',0],['run',.3],['run',.6]]:Array.from({length:mode==='cross'?54:36},(_,i)=>[mode,i/12]);
for(let n=0;n<shots.length;n++){
 const [shot,time]=shots[n],w=mode==='probe'?1280:1920,h=mode==='probe'?720:1080;
 const data=await evaluate(`(()=>{const metrics=MotionLab.render(${JSON.stringify(shot)},${time},${w},${h});return {metrics,png:MotionLab.renderer.domElement.toDataURL('image/png')};})()`);
 const bytes=Uint8Array.from(atob(data.png.split(',')[1]),c=>c.charCodeAt(0));
 if(mode==='probe')await Deno.writeFile(output+'/'+shot+'_'+time+'.png',bytes);
 else for(let hold=0;hold<2;hold++)await Deno.writeFile(output+'/frame_'+String(n*2+hold+1).padStart(4,'0')+'.png',bytes);
 records.push({shot,time,...data.metrics});
}
// Check random-access determinism after posing another timestamp/shot.
const deterministic=await evaluate(`(()=>{function pose(){MotionLab.render('run',.5);let a=[];MotionLab.robot.root.traverse(o=>a.push(...o.matrixWorld.elements));return JSON.stringify(a);}const a=pose();MotionLab.render('cross',.2);MotionLab.render('run',1.7);return a===pose();})()`);
await Deno.writeTextFile(output+'/metrics.json',JSON.stringify({deterministic,records},null,2));
console.log(JSON.stringify({mode,poses:records.length,deterministic,maximumReachError:Math.max(...records.flatMap(r=>[...r.arms,...r.feet].map(v=>v.reachError))),stanceMinY:records.flatMap(r=>r.feet.filter(f=>f.stance).map(f=>f.minY))}));
socket.close();
