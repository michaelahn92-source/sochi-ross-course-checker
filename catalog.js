const {Cam, fit, proj, facing, rings, prism, solid, put, mk, rrect, poly,
  tween, tset, tval, tdone, register, pointer, disposer} = HL;

function mount({stage, svg, read}, value) {
  const bag = disposer(), C = Cam(45, .5, 2.05);
  fit(C, [[-3,-5,0],[75,-5,0],[75,85,0],[-3,85,0],[0,0,88]], 200,166);
  const P = proj(C), front = facing(C), g = mk('g',{},svg), drawers=[];
  let reach=value, active=-1;
  const [base,bi]=rings(-3,-5,75,57,5,1.5);
  put(solid(g),prism(P,front,base,bi,-4,0));
  for(let i=0;i<4;i++) {
    const group=mk('g',{},g), tray=solid(group), lip=solid(group);
    const handle=mk('path',{class:'nf lo'},group), pocket=mk('path',{class:'nf lo'},group);
    const rest=[3,0,8,1][i];
    drawers.push({i,z:i*21,rest,open:tween(rest),tray,lip,handle,pocket,drawn:NaN});
  }
  function draw(d, extension) {
    if(d.drawn===extension)return;
    d.drawn=extension;
    const [r,inner]=rings(0,extension,72,52+extension,3,1.2);
    put(d.tray,prism(P,front,r,inner,d.z,d.z+17));
    const [lr,li]=rings(1,49+extension,71,54+extension,2,0.7);
    put(d.lip,prism(P,front,lr,li,d.z+1,d.z+16));
    d.handle.setAttribute('d',poly(rrect(27,d.z+4,45,d.z+8,1.7,6).map(p=>P(p.u,54+extension,p.v))));
    d.pocket.setAttribute('d',poly(rrect(25,d.z+10,47,d.z+14,1.1,6).map(p=>P(p.u,54+extension,p.v))));
    d.lip.sil.classList.toggle('hi',active<0?d.i===2:d.i===active);
  }
  const loop=register(stage,(_dt,now)=>{
    let moving=false;
    drawers.forEach(d=>{draw(d,tval(d.open,now));if(!tdone(d.open,now))moving=true});
    return moving;
  });
  bag.add(loop.unregister);
  const centers=drawers.map(d=>P(36,53+d.rest,d.z+9));
  function choose(a){
    if(a===active)return;
    const from=a>=0?a:active,now=performance.now();active=a;
    drawers.forEach(d=>{tset(d.open,a<0?d.rest:d.i===a?reach:d.rest*.3,now,Math.abs(d.i-from)*40);d.drawn=NaN});
    read.textContent=a<0?'rest':['MBA','BBA','graduate','undergrad'][a];loop.wake();
  }
  bag.add(pointer(stage,{move:p=>{
    let closest=-1,dist=Infinity;
    centers.forEach((c,i)=>{const d=Math.hypot((p[0]-c[0])*.7,p[1]-c[1]);if(d<dist){dist=d;closest=i}});
    choose(dist<55?closest:-1);
  },leave:()=>choose(-1)}));
  bag.add(()=>svg.replaceChildren());
  return {set:v=>{reach=v;const a=active;active=-2;choose(a)},destroy:bag.dispose};
}
hairline({name:'catalog',means:'Four catalog drawers: the one under your pointer opens for a closer look.',rules:[1,3,4,5,7,8,9,10],range:[12,25,36],tour:[[226,188],[226,146],[226,117],null],mount});
