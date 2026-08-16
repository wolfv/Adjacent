import createAdjacent from '../dist/adjacent.js';

const Module = await createAdjacent();
const sketch = new Module.ConstraintSketch();
const center = sketch.addPoint(100, 100);
const a = sketch.addPoint(0, 0);
const b = sketch.addPoint(200, 0);
const circle = sketch.addCircle(center, 40);
const line = sketch.addLine(a, b);
if (sketch.tangent(circle, line) !== 0) throw new Error('tangent solve failed');
const geometry = sketch.geometry();
const [cx, cy, ax, ay, bx, by] = geometry.points;
const distance = Math.abs((bx-ax)*(ay-cy)-(ax-cx)*(by-ay))/Math.hypot(bx-ax,by-ay);
if (Math.abs(distance-geometry.radii[0]) > 1e-6) throw new Error('line is not tangent');
sketch.delete();

const spline = new Module.HyperSpline();
spline.setPoints([0,0,100,200,300,100],[false,true,false]);
if (spline.solve(16).paths.length !== 2) throw new Error('hyper spline solve failed');
spline.delete();
console.log('WASM smoke tests passed');
