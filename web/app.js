import createAdjacent from './dist/adjacent.js';

const Module = await createAdjacent();
const spline = new Module.HyperSpline();
let cad = new Module.ConstraintSketch();
const canvas = document.querySelector('#canvas');
const ctx = canvas.getContext('2d');
const status = document.querySelector('#status');

const state = {
  tool: 'select',
  points: [[100,480],[235,210],[390,390],[555,170],[710,360],[875,190]],
  smooth: [false,true,true,true,true,false],
  manual: {}, cadPoints: [], lines: [], circles: [], constraints: [],
  pending: null, selected: null, selectedCadPoints: [], selectedLines: [],
  selectedCircles: [], drag: null,
};
let solution = null;
let cadGeometry = {points: [], radii: [], dof: 0};

function sync() {
  spline.setPoints(state.points.flat(), state.smooth);
  for (const [key, value] of Object.entries(state.manual)) {
    spline.setManualHandle(+key, 0, value[0][0], value[0][1]);
    spline.setManualHandle(+key, 1, value[1][0], value[1][1]);
  }
  solution = spline.solve(56);
}

function refreshCad() {
  cadGeometry = cad.geometry();
  state.cadPoints = [];
  for (let i=0;i<cadGeometry.points.length;i+=2)
    state.cadPoints.push([cadGeometry.points[i],cadGeometry.points[i+1]]);
}
function addCadPoint(pos) {
  const id=cad.addPoint(pos[0],pos[1]); state.cadPoints[id]=[...pos]; return id;
}
function applyCadConstraint(spec, record=true) {
  const a=spec.args; let result;
  if(spec.type==='fixed')result=cad.fixed(a[0]);
  else if(spec.type==='coincident')result=cad.coincident(a[0],a[1]);
  else if(spec.type==='horizontal')result=cad.horizontal(a[0]);
  else if(spec.type==='vertical')result=cad.vertical(a[0]);
  else if(spec.type==='distance')result=cad.distance(a[0],a[1],a[2]);
  else if(spec.type==='length')result=cad.length(a[0],a[1]);
  else if(spec.type==='parallel')result=cad.parallel(a[0],a[1]);
  else if(spec.type==='perpendicular')result=cad.perpendicular(a[0],a[1]);
  else if(spec.type==='equalLength')result=cad.equalLength(a[0],a[1]);
  else if(spec.type==='midpoint')result=cad.midpoint(a[0],a[1]);
  else if(spec.type==='pointOnLine')result=cad.pointOnLine(a[0],a[1]);
  else if(spec.type==='pointLineDistance')result=cad.pointLineDistance(a[0],a[1],a[2]);
  else if(spec.type==='angle')result=cad.angle(a[0],a[1],a[2]);
  else if(spec.type==='diameter')result=cad.diameter(a[0],a[1]);
  else if(spec.type==='equalRadius')result=cad.equalRadius(a[0],a[1]);
  else if(spec.type==='concentric')result=cad.concentric(a[0],a[1]);
  if(record)state.constraints.push(spec); refreshCad(); return result;
}
function rebuildCad() {
  cad.delete(); cad=new Module.ConstraintSketch();
  state.cadPoints.forEach(p=>cad.addPoint(p[0],p[1]));
  state.lines.forEach(s=>cad.addLine(s[0],s[1]));
  state.circles.forEach(s=>cad.addCircle(s[0],s[1]));
  const specs=[...state.constraints]; state.constraints=[];
  specs.forEach(spec=>applyCadConstraint(spec,true)); refreshCad();
}

function resize() {
  const box = canvas.getBoundingClientRect();
  const dpr = devicePixelRatio || 1;
  canvas.width = Math.round(box.width * dpr); canvas.height = Math.round(box.height * dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0); draw();
}
new ResizeObserver(resize).observe(canvas);

const line = (a,b,color,width=1,dash=[]) => {
  ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.strokeStyle=color;
  ctx.lineWidth=width; ctx.setLineDash(dash); ctx.stroke(); ctx.setLineDash([]);
};

function drawGrid() {
  const {width,height}=canvas.getBoundingClientRect();
  ctx.clearRect(0,0,width,height); ctx.strokeStyle='#eef2f7'; ctx.lineWidth=1;
  for(let x=0;x<width;x+=50) line([x,0],[x,height],'#eef2f7');
  for(let y=0;y<height;y+=50) line([0,y],[width,y],'#eef2f7');
}

function draw() {
  if (!solution) sync();
  drawGrid();
  state.lines.forEach((shape,index)=>line(state.cadPoints[shape[0]],state.cadPoints[shape[1]],
    state.selectedLines.includes(index)?'#dc2626':'#475569',3));
  state.circles.forEach((shape,index) => {
    const center=state.cadPoints[shape[0]],radius=cadGeometry.radii[index]??shape[1];
    ctx.beginPath(); ctx.arc(center[0],center[1],radius,0,Math.PI*2);
    ctx.strokeStyle=state.selectedCircles.includes(index)?'#dc2626':'#475569';ctx.lineWidth=3;ctx.stroke();
  });
  solution.paths.forEach((path,index) => {
    const h=solution.handles[index], a=state.points[index], b=state.points[index+1];
    line(a,[h[0],h[1]],'#94a3b8',1,[5,4]); line(b,[h[2],h[3]],'#94a3b8',1,[5,4]);
    for (let side=0;side<2;side++) {
      const x=h[side*2],y=h[side*2+1];
      line([x-5,y-5],[x+5,y+5],h[4]?'#dc2626':'#f97316',2);
      line([x-5,y+5],[x+5,y-5],h[4]?'#dc2626':'#f97316',2);
    }
    ctx.beginPath();ctx.moveTo(path[0],path[1]);
    for(let i=2;i<path.length;i+=2)ctx.lineTo(path[i],path[i+1]);
    ctx.strokeStyle='#2563eb';ctx.lineWidth=4;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke();
  });
  state.cadPoints.forEach((p,index)=>{
    ctx.beginPath();ctx.arc(p[0],p[1],6,0,Math.PI*2);ctx.fillStyle='#7c3aed';ctx.fill();
    ctx.strokeStyle=state.selectedCadPoints.includes(index)?'#ef4444':'white';ctx.lineWidth=2;ctx.stroke();
  });
  state.points.forEach((p,index) => {
    ctx.beginPath();
    if(state.smooth[index])ctx.arc(p[0],p[1],8,0,Math.PI*2);
    else ctx.rect(p[0]-8,p[1]-8,16,16);
    ctx.fillStyle='#0ea5e9'; if(!state.smooth[index])ctx.fillStyle='#22c55e';ctx.fill();
    ctx.strokeStyle=index===state.selected?'#ef4444':'white';ctx.lineWidth=3;ctx.stroke();
  });
  let maxError=0;
  for(let i=0;i+1<solution.curvatures.length;i++) {
    if(state.smooth[i+1] && !state.manual[i] && !state.manual[i+1])
      maxError=Math.max(maxError,Math.abs(solution.curvatures[i][1]-solution.curvatures[i+1][0]));
  }
  status.textContent=`C++/WASM · ${solution.paths.length} hyperbeziers · G² error ${maxError.toExponential(2)} · CAD DOF ${cadGeometry.dof} · ${state.constraints.length} constraints`;
}

function position(event){const r=canvas.getBoundingClientRect();return[event.clientX-r.left,event.clientY-r.top]}
function near(a,b,r=15){return (a[0]-b[0])**2+(a[1]-b[1])**2<=r*r}
function segmentDistance(p,a,b){
  const dx=b[0]-a[0],dy=b[1]-a[1],d=dx*dx+dy*dy;
  const t=d?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/d)):0;
  return Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy);
}
function pick(pos) {
  for(let i=0;i<state.cadPoints.length;i++)if(near(pos,state.cadPoints[i]))return{kind:'cadPoint',index:i};
  for(let i=0;i<state.lines.length;i++){const s=state.lines[i];if(segmentDistance(pos,state.cadPoints[s[0]],state.cadPoints[s[1]])<9)return{kind:'line',index:i}}
  for(let i=0;i<state.circles.length;i++){const s=state.circles[i],c=state.cadPoints[s[0]],r=cadGeometry.radii[i]??s[1];if(Math.abs(Math.hypot(pos[0]-c[0],pos[1]-c[1])-r)<9)return{kind:'circle',index:i}}
  for(let i=0;i<state.points.length;i++)if(near(pos,state.points[i]))return{kind:'point',index:i};
  for(let i=0;i<solution.handles.length;i++)for(let side=0;side<2;side++)
    if(near(pos,[solution.handles[i][side*2],solution.handles[i][side*2+1]],12))return{kind:'handle',index:i,side};
  return null;
}

canvas.addEventListener('pointerdown',event=>{
  const pos=position(event);
  if(state.tool==='select'){
    state.drag=pick(pos);
    if(!event.shiftKey){state.selectedCadPoints=[];state.selectedLines=[];state.selectedCircles=[]}
    if(state.drag?.kind==='point')state.selected=state.drag.index;
    if(state.drag?.kind==='cadPoint'&&!state.selectedCadPoints.includes(state.drag.index))state.selectedCadPoints.push(state.drag.index);
    if(state.drag?.kind==='line'&&!state.selectedLines.includes(state.drag.index))state.selectedLines.push(state.drag.index);
    if(state.drag?.kind==='circle'&&!state.selectedCircles.includes(state.drag.index))state.selectedCircles.push(state.drag.index);
    canvas.setPointerCapture(event.pointerId);draw();return;
  }
  if(state.tool==='pen'){
    state.points.push(pos);state.smooth.push(true);sync();draw();return;
  }
  if(!state.pending){state.pending=pos;return}
  if(state.tool==='line'){
    const a=addCadPoint(state.pending),b=addCadPoint(pos);state.lines.push([a,b]);cad.addLine(a,b);
  }
  if(state.tool==='circle'){
    const center=addCadPoint(state.pending),radius=Math.hypot(pos[0]-state.pending[0],pos[1]-state.pending[1]);
    state.circles.push([center,radius]);cad.addCircle(center,radius);
  }
  state.pending=null;cad.solve();refreshCad();draw();
});
canvas.addEventListener('pointermove',event=>{
  if(!state.drag)return;const pos=position(event);
  if(state.drag.kind==='point')state.points[state.drag.index]=pos;
  else if(state.drag.kind==='cadPoint'){
    cad.dragPoint(state.drag.index,pos[0],pos[1]);refreshCad();draw();return;
  } else if(state.drag.kind==='handle') {
    const i=state.drag.index, h=solution.handles[i];
    const handles=state.manual[i]||[[h[0],h[1]],[h[2],h[3]]];handles[state.drag.side]=pos;
    state.manual[i]=handles;
  }
  sync();draw();
});
canvas.addEventListener('pointerup',()=>state.drag=null);
canvas.addEventListener('dblclick',event=>{
  const hit=pick(position(event));if(hit?.kind==='point'&&hit.index>0&&hit.index<state.points.length-1){
    state.smooth[hit.index]=!state.smooth[hit.index];sync();draw();
  }
});

document.querySelectorAll('.tool').forEach(button=>button.onclick=()=>{
  document.querySelectorAll('.tool').forEach(b=>b.classList.remove('active'));button.classList.add('active');
  state.tool=button.dataset.tool;state.pending=null;
});
document.querySelector('#toggle-point').onclick=()=>{
  if(state.selected!=null&&state.selected>0&&state.selected<state.points.length-1){state.smooth[state.selected]=!state.smooth[state.selected];sync();draw()}
};
document.querySelector('#reset-handles').onclick=()=>{
  Object.keys(state.manual).forEach(key=>spline.resetHandle(+key));state.manual={};sync();draw();
};

document.querySelector('#remove-constraint').onclick=()=>{
  if(state.constraints.length){state.constraints.pop();cad.removeLastConstraint();refreshCad();draw()}
};
document.querySelectorAll('[data-constraint]').forEach(button=>button.onclick=()=>{
  const type=button.dataset.constraint,p=state.selectedCadPoints,l=state.selectedLines,c=state.selectedCircles;
  const number=(message,initial)=>{const value=prompt(message,String(initial));return value===null?null:+value};
  let args=null;
  if(type==='fixed'&&p.length===1)args=[p[0]];
  else if(type==='coincident'&&p.length===2)args=[p[0],p[1]];
  else if((type==='horizontal'||type==='vertical')&&l.length===1)args=[l[0]];
  else if(type==='distance'&&p.length===2){const v=number('Point distance',100);if(v!==null)args=[p[0],p[1],v]}
  else if(type==='length'&&l.length===1){const v=number('Line length',100);if(v!==null)args=[l[0],v]}
  else if(['parallel','perpendicular','equalLength','angle'].includes(type)&&l.length===2){
    args=[l[0],l[1]];if(type==='angle'){const v=number('Angle in degrees',90);if(v===null)return;args.push(v*Math.PI/180)}
  }
  else if((type==='midpoint'||type==='pointOnLine')&&p.length===1&&l.length===1)args=[p[0],l[0]];
  else if(type==='pointLineDistance'&&p.length===1&&l.length===1){const v=number('Point-line distance',50);if(v!==null)args=[p[0],l[0],v]}
  else if(type==='diameter'&&c.length===1){const v=number('Diameter',100);if(v!==null)args=[c[0],v]}
  else if((type==='equalRadius'||type==='concentric')&&c.length===2)args=[c[0],c[1]];
  if(!args){alert('Select the required point(s), line(s), or circle(s). Shift-click for multiple selection.');return}
  const result=applyCadConstraint({type,args});draw();
  if(result===1)alert('The solver did not converge; geometry was rolled back.');
});

function svgText(){
  const box=canvas.getBoundingClientRect();let paths='';
  solution.paths.forEach(path=>{let d=`M${path[0].toFixed(2)},${path[1].toFixed(2)}`;for(let i=2;i<path.length;i+=2)d+=` L${path[i].toFixed(2)},${path[i+1].toFixed(2)}`;paths+=`<path d="${d}"/>\n`});
  state.lines.forEach(s=>{const a=state.cadPoints[s[0]],b=state.cadPoints[s[1]];paths+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>\n`});
  state.circles.forEach((s,i)=>{const c=state.cadPoints[s[0]],r=cadGeometry.radii[i]??s[1];paths+=`<circle cx="${c[0]}" cy="${c[1]}" r="${r}"/>\n`});
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${box.width} ${box.height}" fill="none" stroke="black" stroke-width="2">\n${paths}</svg>\n`;
}
function download(name,text,type){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
document.querySelector('#export-svg').onclick=()=>download('adjacent.svg',svgText(),'image/svg+xml');
document.querySelector('#save-project').onclick=()=>download('adjacent.json',JSON.stringify({...state,drag:null,pending:null},null,2),'application/json');
document.querySelector('#open-project').onchange=async event=>{
  const data=JSON.parse(await event.target.files[0].text());Object.assign(state,data,{drag:null,pending:null});rebuildCad();sync();draw();
};

refreshCad();sync();draw();
