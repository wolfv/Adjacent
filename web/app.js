import createAdjacent from './dist/adjacent.js';

const Module = await createAdjacent();
const spline = new Module.HyperSpline();
const canvas = document.querySelector('#canvas');
const ctx = canvas.getContext('2d');
const status = document.querySelector('#status');

const state = {
  tool: 'select',
  points: [[100,480],[235,210],[390,390],[555,170],[710,360],[875,190]],
  smooth: [false,true,true,true,true,false],
  manual: {}, lines: [], circles: [], pending: null, selected: null, drag: null,
};
let solution = null;

function sync() {
  spline.setPoints(state.points.flat(), state.smooth);
  for (const [key, value] of Object.entries(state.manual)) {
    spline.setManualHandle(+key, 0, value[0][0], value[0][1]);
    spline.setManualHandle(+key, 1, value[1][0], value[1][1]);
  }
  solution = spline.solve(56);
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
  for (const shape of state.lines) line(shape[0],shape[1],'#475569',3);
  for (const [center,radius] of state.circles) {
    ctx.beginPath(); ctx.arc(center[0],center[1],radius,0,Math.PI*2);
    ctx.strokeStyle='#475569';ctx.lineWidth=3;ctx.stroke();
  }
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
  status.textContent=`C++/WASM · ${solution.paths.length} hyperbeziers · max automatic G² error ${maxError.toExponential(2)} · ${state.lines.length} lines · ${state.circles.length} circles`;
}

function position(event){const r=canvas.getBoundingClientRect();return[event.clientX-r.left,event.clientY-r.top]}
function near(a,b,r=15){return (a[0]-b[0])**2+(a[1]-b[1])**2<=r*r}
function pick(pos) {
  for(let i=0;i<state.points.length;i++)if(near(pos,state.points[i]))return{kind:'point',index:i};
  for(let i=0;i<solution.handles.length;i++)for(let side=0;side<2;side++)
    if(near(pos,[solution.handles[i][side*2],solution.handles[i][side*2+1]],12))return{kind:'handle',index:i,side};
  return null;
}

canvas.addEventListener('pointerdown',event=>{
  const pos=position(event);
  if(state.tool==='select'){
    state.drag=pick(pos); if(state.drag?.kind==='point')state.selected=state.drag.index;
    canvas.setPointerCapture(event.pointerId);draw();return;
  }
  if(state.tool==='pen'){
    state.points.push(pos);state.smooth.push(true);sync();draw();return;
  }
  if(!state.pending){state.pending=pos;return}
  if(state.tool==='line')state.lines.push([state.pending,pos]);
  if(state.tool==='circle')state.circles.push([state.pending,Math.hypot(pos[0]-state.pending[0],pos[1]-state.pending[1])]);
  state.pending=null;draw();
});
canvas.addEventListener('pointermove',event=>{
  if(!state.drag)return;const pos=position(event);
  if(state.drag.kind==='point')state.points[state.drag.index]=pos;
  else {
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

function svgText(){
  const box=canvas.getBoundingClientRect();let paths='';
  solution.paths.forEach(path=>{let d=`M${path[0].toFixed(2)},${path[1].toFixed(2)}`;for(let i=2;i<path.length;i+=2)d+=` L${path[i].toFixed(2)},${path[i+1].toFixed(2)}`;paths+=`<path d="${d}"/>\n`});
  state.lines.forEach(s=>paths+=`<line x1="${s[0][0]}" y1="${s[0][1]}" x2="${s[1][0]}" y2="${s[1][1]}"/>\n`);
  state.circles.forEach(s=>paths+=`<circle cx="${s[0][0]}" cy="${s[0][1]}" r="${s[1]}"/>\n`);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${box.width} ${box.height}" fill="none" stroke="black" stroke-width="2">\n${paths}</svg>\n`;
}
function download(name,text,type){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
document.querySelector('#export-svg').onclick=()=>download('adjacent.svg',svgText(),'image/svg+xml');
document.querySelector('#save-project').onclick=()=>download('adjacent.json',JSON.stringify({...state,drag:null,pending:null},null,2),'application/json');
document.querySelector('#open-project').onchange=async event=>{
  const data=JSON.parse(await event.target.files[0].text());Object.assign(state,data,{drag:null,pending:null});sync();draw();
};

sync();draw();
