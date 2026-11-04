/* Deterministic shot rig. Original fusion geometry and module are unchanged. */
(function (global) {
  'use strict';
  function build(robot) {
    var T = global.THREE, P = robot.parts, root = robot.root;
    var V = function (x,y,z) { return new T.Vector3(x,y,z); };
    robot.setScaling(1).setFusion(1); root.updateMatrixWorld(true);
    var rest = [], worlds = new Map(), metrics = {};
    root.traverse(function(o) {
      rest.push({o:o,p:o.position.clone(),q:o.quaternion.clone(),s:o.scale.clone()});
      worlds.set(o,o.matrixWorld.clone());
    });
    function restore() {
      rest.forEach(function(r) { r.o.position.copy(r.p); r.o.quaternion.copy(r.q); r.o.scale.copy(r.s); });
      robot.setFusion(1).setScaling(1).setGauge(1);
      metrics = {feet:[], arms:[]};
    }
    function world(o,p,q) {
      o.parent.updateWorldMatrix(true,false);
      o.position.copy(o.parent.worldToLocal(p.clone()));
      o.quaternion.copy(o.parent.getWorldQuaternion(new T.Quaternion()).invert()).multiply(q);
      o.updateWorldMatrix(false,true);
    }
    function follow(o, source) {
      source.updateWorldMatrix(true,false); o.parent.updateWorldMatrix(true,false);
      var delta = source.matrixWorld.clone().multiply(worlds.get(source).clone().invert());
      var local = o.parent.matrixWorld.clone().invert().multiply(delta).multiply(worlds.get(o));
      local.decompose(o.position,o.quaternion,o.scale); o.updateWorldMatrix(false,true);
    }
    function aim(direction) {
      var y=direction.clone().normalize().negate(), z=V(0,0,1);
      z.addScaledVector(y,-z.dot(y));
      if(z.lengthSq()<0.0001) z=V(0,1,0).addScaledVector(y,-y.y);
      z.normalize(); var x=y.clone().cross(z).normalize(); z=x.clone().cross(y).normalize();
      return new T.Quaternion().setFromRotationMatrix(new T.Matrix4().makeBasis(x,y,z));
    }
    function solve(start,target,l1,l2,pole) {
      var dir=target.clone().sub(start), requested=dir.length();
      var d=T.MathUtils.clamp(requested,Math.abs(l1-l2)+0.001,l1+l2-0.001); dir.normalize();
      var a=(l1*l1-l2*l2+d*d)/(2*d), h=Math.sqrt(Math.max(0,l1*l1-a*a));
      var bend=pole.clone().sub(start); bend.addScaledVector(dir,-bend.dot(dir)).normalize();
      var joint=start.clone().addScaledVector(dir,a).addScaledVector(bend,h);
      var end=start.clone().addScaledVector(dir,d);
      return {joint:joint,end:end,upper:aim(joint.clone().sub(start)),lower:aim(end.clone().sub(joint)),error:Math.abs(requested-d)};
    }
    function arm(side,shoulder,wrist,pole,length) {
      var a=P.claudeBike['armFrame'+side], f=P.claudeBike['forearm'+side];
      var ik=solve(shoulder,wrist,length||3.2,6.3,pole);
      world(a,shoulder.clone().add(V(0,-0.6,0).applyQuaternion(ik.upper)),ik.upper);
      // Existing silver telescoping member bridges the longer shoulder-to-elbow span.
      P.claudeBike['innerFrame'+side].position.y=-(length||3.2)/2;
      P.claudeBike['innerFrame'+side].scale.y=(length||3.2)/3.2;
      world(f,ik.joint.clone().add(V(0,-2.75,0).applyQuaternion(ik.lower)),ik.lower);
      var extras=['wheel'+side,'fork'+side];
      extras.push(side==='L'?'handlebar':'saddle'); if(side==='R')extras.push('frontFairing');
      extras.forEach(function(k) { if(P.claudeBike[k])follow(P.claudeBike[k],f); });
      metrics.arms.push({side:side,reachError:ik.error,wrist:ik.end.toArray()});
    }
    function leg(side,ankle,pitch,stance) {
      var thigh=P.gptShip['thigh'+side], shin=P.gptShip['shin'+side], foot=P.gptShip['ankle'+side];
      var hip=thigh.getWorldPosition(new T.Vector3());
      var ik=solve(hip,ankle,4.2,8.25,hip.clone().add(V(0,-4,12)));
      world(thigh,hip,ik.upper);
      world(shin,ik.joint.clone().add(V(0,-3.8,0).applyQuaternion(ik.lower)),ik.lower);
      world(foot,ik.end,new T.Quaternion().setFromAxisAngle(V(1,0,0),pitch));
      if(P.gptShip['bowFairing'+side])follow(P.gptShip['bowFairing'+side],shin);
      var bounds=new T.Box3().setFromObject(P.gptShip['sole'+side]);
      metrics.feet.push({side:side,stance:stance,minY:bounds.min.y,reachError:ik.error,ankle:ik.end.toArray()});
    }
    function smooth(t) { t=T.MathUtils.clamp(t,0,1); return t*t*(3-2*t); }
    function cross(seconds) {
      restore();
      var open=smooth((seconds-1.10)/0.75);
      root.position.y=-0.6; root.updateMatrixWorld(true);
      ['L','R'].forEach(function(side) {
        var sign=side==='L'?-1:1;
        // The shoulder carriage moves forward; two different depth planes keep the bulky gauntlets apart.
        var z=side==='L'?6.5:10.5;
        var shoulder=V(sign*5.7,22.7,z).lerp(V(sign*7.8,21.2,0),open);
        var strain=seconds<1.10 ? Math.sin(seconds*79+sign)*0.045 : 0;
        var wrist=V(-sign*3.0,28.4+strain,z+0.6).lerp(V(sign*14.1,14.1,3.1),open);
        var pole=V(sign*11,18,Math.max(5,z));
        arm(side,shoulder,wrist,pole,4.2);
      });
      leg('L',V(-3.8,2.423,0.4),0,true); leg('R',V(3.8,2.423,-0.4),0,true);
      root.updateMatrixWorld(true); return metrics;
    }
    function run(seconds) {
      restore();
      var phase=(seconds/1.2)%1, wave=Math.sin(phase*Math.PI*2);
      root.position.y=-1.25-0.45*Math.sin(phase*Math.PI*4);
      root.rotation.x=0.10; root.rotation.y=0.035*wave; root.rotation.z=-0.025*wave;
      root.updateMatrixWorld(true);
      ['L','R'].forEach(function(side,index) {
        var sign=index?1:-1, p=(phase+index*0.5)%1, stance=p<0.43;
        var u=stance?p/0.43:(p-0.43)/0.57;
        var z=stance?3.3-6.6*u:-3.3+6.6*smooth(u);
        var lift=stance?0:3.5*Math.sin(Math.PI*u);
        var pitch=stance?0:0.35*Math.sin(Math.PI*u);
        leg(side,V(sign*3.05,2.423+lift,1.5+z),pitch,stance);
        var shoulder=root.localToWorld(V(sign*7.8,21.2,0));
        var swing=Math.sin(p*Math.PI*2);
        var wrist=shoulder.clone().add(V(sign*0.8,-5.2-1.5*swing,2.5-4.5*swing));
        arm(side,shoulder,wrist,shoulder.clone().add(V(sign*2,-6,-4)),3.2);
      });
      root.updateMatrixWorld(true); return metrics;
    }
    return {cross:cross,run:run,restore:restore,getMetrics:function(){return metrics;}};
  }
  global.MechaMotionRig={build:build};
})(window);
