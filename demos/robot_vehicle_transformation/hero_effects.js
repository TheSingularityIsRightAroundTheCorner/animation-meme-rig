/* Deterministic pooled geometry: no external textures, no frame-to-frame accumulation. */
(function(global){
  'use strict';
  function build(scene,palette){
    var T=global.THREE, V=function(x,y,z){return new T.Vector3(x,y,z);};
    var group=new T.Group();group.name='HeroSparks';scene.add(group);
    var geometry=new T.BoxGeometry(1,1,1), pool=[], used=0;
    var colors={core:new T.Color(palette.white),blue:new T.Color(palette.antigravityBlue).lerp(new T.Color(palette.white),.55),gold:new T.Color(palette.gaugeYellow)};
    for(var i=0;i<320;i++){
      var mesh=new T.Mesh(geometry,new T.MeshBasicMaterial({transparent:true,depthWrite:false,toneMapped:false}));
      mesh.visible=false;group.add(mesh);pool.push(mesh);
    }
    function random(seed){var n=seed>>>0;return function(){n=(1664525*n+1013904223)>>>0;return n/4294967296;};}
    function segment(a,b,width,color,opacity){
      if(used>=pool.length)return;
      var mesh=pool[used++],d=b.clone().sub(a);mesh.visible=true;
      mesh.position.copy(a).add(b).multiplyScalar(.5);mesh.scale.set(width,Math.max(.001,d.length()),width);
      mesh.quaternion.setFromUnitVectors(V(0,1,0),d.normalize());mesh.material.color.copy(colors[color]);mesh.material.opacity=opacity;
    }
    function bolt(a,b,rng,strength){
      var points=[a];for(var j=1;j<5;j++)points.push(a.clone().lerp(b,j/5).add(V((rng()-.5)*1.1,(rng()-.5)*1.1,(rng()-.5)*.5)));
      points.push(b);
      for(var k=0;k<points.length-1;k++){
        segment(points[k],points[k+1],.15,'blue',strength*.8);
        segment(points[k],points[k+1],.055,'core',strength);
      }
    }
    function render(time,robot,camera){
      pool.forEach(function(m){m.visible=false;});used=0;
      var tick=Math.floor((time+1e-7)*12), rng=random(901+tick*491);
      var wrists=['L','R'].map(function(side){return robot.parts.claudeBike['hand'+side].getWorldPosition(new T.Vector3());});
      var active=time<2.22;
      if(active){
        wrists.forEach(function(c){
          c=c.clone().add(V(0,0,1.0));
          for(var j=0;j<4;j++){
            var angle=rng()*Math.PI*2, radius=1.4+rng()*1.8;
            var a=c.clone().add(V(Math.cos(angle)*radius,Math.sin(angle)*radius,.5));
            var b=c.clone().add(V(Math.cos(angle+1.4)*radius,Math.sin(angle+1.4)*radius,.7));
            bolt(a,b,rng,.9);
          }
          for(var n=0;n<11;n++){
            var d=V(rng()-.5,rng()-.5,.15+rng()*.2).normalize();
            var start=c.clone().addScaledVector(d,1.8+rng()*2);
            segment(start,start.clone().addScaledVector(d,.25+rng()*1.5),.05,n%3?'gold':'core',.7+rng()*.3);
          }
        });
        if(time<1.12)bolt(wrists[0].clone().add(V(0,0,2)),wrists[1].clone().add(V(0,0,2)),rng,1);
      }
      var age=(time-2.05)/.42;
      if(age>=0 && age<1){
        camera.updateMatrixWorld();
        var right=V(1,0,0).applyQuaternion(camera.quaternion), up=V(0,1,0).applyQuaternion(camera.quaternion);
        var center=robot.parts.gptShip.chestFrame.getWorldPosition(new T.Vector3()).add(V(0,0,7));
        var fixed=random(577);
        for(var s=0;s<64;s++){
          var theta=(s+fixed()*.65)/64*Math.PI*2;
          var dir=right.clone().multiplyScalar(Math.cos(theta)).addScaledVector(up,Math.sin(theta));
          var radius=2+age*(75+fixed()*40), length=1.5+age*11;
          var a=center.clone().addScaledVector(dir,radius), b=a.clone().addScaledVector(dir,length);
          segment(a,b,.08+.05*(1-age),s%3?'blue':'core',Math.max(0,1-age*.7));
        }
      }
      return {visibleSegments:used,burst:age>=0&&age<1,cleanHold:time>=2.47};
    }
    return {render:render,group:group};
  }
  global.HeroEffects={build:build};
})(window);
