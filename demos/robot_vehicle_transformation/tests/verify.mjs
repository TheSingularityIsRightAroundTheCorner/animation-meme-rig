// Browser integration checks; Chrome debugging on 9222 and the local preview on 8766.
const tabs=await(await fetch('http://127.0.0.1:9222/json')).json();
const socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>socket.onopen=r);let id=0;const pending=new Map();
socket.onmessage=e=>{const d=JSON.parse(e.data);if(pending.has(d.id)){pending.get(d.id)(d);pending.delete(d.id);}};
async function send(method,params={}){const key=++id;const p=new Promise(r=>pending.set(key,r));socket.send(JSON.stringify({id:key,method,params}));const d=await p;if(d.error)throw Error(JSON.stringify(d.error));return d.result;}
async function evaluate(expression){const d=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(d.exceptionDetails)throw Error(JSON.stringify(d.exceptionDetails));return d.result.value;}
const url='http://127.0.0.1:8766/showcase.html?verify='+Date.now();await send('Page.navigate',{url});
for(let i=0;i<100;i++){if(await evaluate('location.href==='+JSON.stringify(url)+' && Boolean(window.MotionLab)'))break;await new Promise(r=>setTimeout(r,100));}
const result=await evaluate(`(()=>{
 const M=MotionLab, checks=[]; M.stop();
 function check(ok,name){if(!ok)throw Error(name);checks.push(name);}
 function count(){let n=0;M.scene.traverse(()=>n++);return n;}
 const original=count(), start=M.render('cross',0,1280,720);
 check(start.effects.visibleSegments>0,'Sparks exist during the crossed-fist hold');
 const early=M.renderer.domElement.toDataURL();
 M.render('run',.5); M.render('cross',0);
 check(early===M.renderer.domElement.toDataURL(),'Pose, effects and camera are deterministic');
 const sweep=M.render('cross',1.5);
 check(sweep.effects.visibleSegments>0,'Sparks continue while hands descend');
 check(sweep.arms.every((a,i)=>a.wrist[1]<start.arms[i].wrist[1]),'Both hands descend from the X pose');
 check(sweep.camera.position[1]<start.camera.position[1],'Camera descends with the hands');
 const burst=M.render('cross',2.166667);
 check(burst.effects.burst && burst.effects.visibleSegments>0,'Single release burst is visible');
 const end=M.render('cross',3.5);
 check(end.effects.cleanHold && end.effects.visibleSegments===0,'No sparks remain during the final hold');
 check(end.arms.every(a=>a.wrist[1]<16 && Math.abs(a.wrist[0])>13),'Final hands spread down and outward');
 const bounds=new THREE.Box3().setFromObject(M.robot.root), projected=[];
 for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z])projected.push(new THREE.Vector3(x,y,z).project(M.camera));
 check(projected.every(p=>Math.abs(p.x)<1 && Math.abs(p.y)<1),'Full robot fits inside the final frame');
 const finalImage=M.renderer.domElement.toDataURL();M.render('cross',4.25);
 check(finalImage===M.renderer.domElement.toDataURL(),'Final clean pose holds still');
 let maxReach=0,maxGround=0;
 for(let i=0;i<36;i++){
  const m=M.render('run',i/12);
  check(m.camera.position[1]===9,'Knee-height camera at running frame '+i);
  maxReach=Math.max(maxReach,...[...m.arms,...m.feet].map(v=>v.reachError));
  maxGround=Math.max(maxGround,...m.feet.filter(f=>f.stance).map(f=>Math.abs(f.minY)));
 }
 check(maxReach<.001,'All running joint targets are reachable');
 check(maxGround<.01,'Stance soles stay at the ground plane');
 check(count()===original,'Effects do not add nodes while playing');
 const gl=M.renderer.getContext(),pixel=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
 check(pixel[3]===0,'Canvas retains transparent background');
 check(gl.getError()===gl.NO_ERROR,'No WebGL errors');
 return {passed:true,checks:checks.length,results:checks,maximumReachError:maxReach,maximumStanceGroundOffset:maxGround};
})()`);
console.log(JSON.stringify(result,null,2));socket.close();
