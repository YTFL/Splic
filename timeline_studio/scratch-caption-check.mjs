import { drawCaptionLayout, getCaptionTextLayout } from "./src/lib/captionLayout.js";

const ops = [];
function makeCtx() {
  const ctx = {
    font: "10px sans-serif",
    fillStyle: "#000000",
    strokeStyle: "#000000",
    globalAlpha: 1,
    textAlign: "start",
    textBaseline: "alphabetic",
    lineWidth: 1,
    lineJoin: "miter",
    miterLimit: 10,
    shadowColor: "transparent",
    shadowBlur: 0,
    shadowOffsetX: 0,
    shadowOffsetY: 0,
    letterSpacing: "0px",
    measureText: (text) => ({ width: String(text).length * 8 }),
  };
  const record = (name) => (...args) => {
    ops.push({ op: name, args, fillStyle: ctx.fillStyle, globalAlpha: ctx.globalAlpha, font: ctx.font });
  };
  for (const name of ["save", "restore", "beginPath", "moveTo", "lineTo", "quadraticCurveTo", "closePath", "roundRect", "fill", "stroke", "rect", "clip", "fillText", "strokeText"]) {
    ctx[name] = record(name);
  }
  return ctx;
}

const style = {
  textColor: "#ffffff",
  backgroundColor: "#000000",
  backgroundOpacity: 0.5,
  borderColor: "#35f0dd",
  borderWidth: 0,
  radius: 7,
  paddingX: 22,
  paddingY: 12,
  shadowOpacity: 0.45,
  effect: "normal",
  textStrokeColor: "#05080d",
  textStrokeWidth: 0,
  fontId: "default",
};

const ctx = makeCtx();
const layout = getCaptionTextLayout({
  context: ctx,
  text: "Ye toh full paisa vasool hai",
  captionSize: 14,
  captionStyle: style,
  renderFrame: { width: 640, height: 360 },
});
console.log("layout:", { width: layout.width, height: layout.height, lines: layout.lines, font: layout.metrics.font });
drawCaptionLayout(ctx, layout);
console.log("ops:", JSON.stringify(ops, null, 1));
