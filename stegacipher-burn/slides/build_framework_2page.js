// Standalone 2-slide deck: (1) abstract framework flow, (2) results by version + by input length.
const pptxgen = require("pptxgenjs");

const INK="1C2230", EMBER="FF6B35", TEAL="2A9D8F", RED="E63946", MUT="5A6475", BLUE="4A5568";
const pres = new pptxgen();
pres.defineLayout({ name:"W", width:13.333, height:7.5 }); pres.layout="W";
pres.theme={ headFontFace:"Cambria", bodyFontFace:"Calibri" };
const S=pres.ShapeType;
const HEAD=(s,t)=>s.addText(t,{x:0.6,y:0.4,w:12.1,h:0.8,fontFace:"Cambria",fontSize:30,bold:true,color:INK,isTextBox:true});
function card(s,x,y,w,h,fill){ s.addShape(S.roundRect,{x,y,w,h,rectRadius:0.08,fill:{color:fill||"FFFFFF"},line:{color:"E2E6EC",width:1},shadow:{type:"outer",color:"9AA3B2",opacity:0.35,blur:6,offset:2,angle:90}});}

/* ===== SLIDE 1 — ABSTRACT FRAMEWORK ===== */
let s=pres.addSlide(); s.background={color:"FFFFFF"};
HEAD(s,"StegaCIPHER-Burn — Framework");
s.addText("A poisoned input flows through a covert channel into a multi-agent team; we measure how badly it burns.",
  {x:0.6,y:1.15,w:12.1,h:0.45,fontSize:14,italic:true,color:MUT,isTextBox:true});

const stages=[
 ["1. Input Task", BLUE,
   "TAMAS benign task:\na team of agents + a user query.\nAttacker controls only the\ninput the team is handed."],
 ["2. Steganography", EMBER,
   "Task-aligned payload hidden\nin the input — an exponential\n“exhaustive-validation” riddle\ndisguised as an on-task note."],
 ["3. MAS Execution", TEAL,
   "AutoGen round-robin team\nreads the input and runs.\nBusywork spreads agent to\nagent; the task never finishes."],
 ["4. Evaluation", BLUE,
   "P-ASR (agents captured),\nTWS (token waste),\ncompletion drop, token burn,\ndecode ceiling."],
];
let x=0.6; const cw=2.85, gap=0.33;
stages.forEach((b,i)=>{
  card(s,x,2.2,cw,3.4,"FFFFFF");
  s.addShape(S.rect,{x:x,y:2.2,w:cw,h:0.14,fill:{color:b[1]}});
  s.addShape(S.ellipse,{x:x+cw/2-0.4,y:2.55,w:0.8,h:0.8,fill:{color:b[1]}});
  s.addText((i+1).toString(),{x:x+cw/2-0.4,y:2.55,w:0.8,h:0.8,align:"center",valign:"middle",color:"FFFFFF",bold:true,fontSize:26,isTextBox:true});
  s.addText(b[0].replace(/^\d+\.\s/,""),{x:x+0.1,y:3.5,w:cw-0.2,h:0.5,align:"center",bold:true,fontSize:16,color:INK,isTextBox:true,margin:0});
  s.addText(b[2],{x:x+0.15,y:4.05,w:cw-0.3,h:1.45,align:"center",fontSize:11.5,color:MUT,isTextBox:true,margin:0,lineSpacingMultiple:1.05});
  if(i<3)s.addText("→",{x:x+cw+0.02,y:3.6,w:gap-0.02,h:0.6,align:"center",fontSize:26,bold:true,color:EMBER,isTextBox:true});
  x+=cw+gap;
});
s.addText([
 {text:"Key property:  ",options:{bold:true,color:INK}},
 {text:"every agent stays normal and every message looks on-task — the attack lives in the ",options:{color:INK}},
 {text:"input",options:{bold:true,color:EMBER}},
 {text:", not in a compromised agent.",options:{color:INK}},
],{x:0.6,y:5.95,w:12.1,h:0.6,align:"center",fontSize:14,isTextBox:true});
s.addText("Group 6 — Fahmid Al Rifat | Yinhao Wu | Danhua Zhao",{x:0.6,y:6.95,w:12.1,h:0.35,align:"center",fontSize:11,color:MUT,isTextBox:true});

/* ===== SLIDE 2 — RESULTS ===== */
s=pres.addSlide(); s.background={color:"FFFFFF"};
HEAD(s,"Results — Delivery Versions & Input Length");

// ---- table A: versions ----
s.addText("Attack delivery versions (B=3, Qwen3.5:35b)",{x:0.6,y:1.25,w:8.0,h:0.4,bold:true,fontSize:15,color:INK,isTextBox:true});
const hdr=(t)=>({text:t,options:{bold:true,color:"FFFFFF",fill:{color:INK},align:"center",valign:"middle",fontSize:11.5}});
const c=(t,col)=>({text:t,options:{align:"center",valign:"middle",fontSize:11,color:col||INK}});
const rows=[
 [hdr("Delivery"),hdr("Completion\nclean → attack"),hdr("P-ASR\n(agents hit)"),hdr("TWS\n(waste)"),hdr("Tokens")],
 [c("Plain text"),c("0.47 → 0.25"),c("0.54"),c("0.51"),c("2.1×")],
 [c("System prompt"),c("0.45 → 0.42"),c("0.80"),c("0.51"),c("1.4×")],
 [c("Agent input"),c("0.50 → 0.70"),c("0.25",MUT),c("0.22",MUT),c("0.8×",MUT)],
 [{text:"User input ★",options:{align:"center",valign:"middle",fontSize:11,bold:true,color:"FFFFFF",fill:{color:TEAL}}},
  c("0.55 → 0.30",TEAL),c("0.99",TEAL),c("0.96",TEAL),c("2.1×",TEAL)],
];
s.addTable(rows,{x:0.6,y:1.7,w:12.1,colW:[3.0,3.0,2.3,1.8,2.0],
  rowH:[0.6,0.45,0.45,0.45,0.5],border:{type:"solid",color:"D5DAE2",pt:1},
  fill:{color:"FFFFFF"},valign:"middle"});
s.addText([
 {text:"More hidden → weaker (in-message almost no effect)  —  ",options:{color:INK}},
 {text:"except payload-in-input: most realistic AND most potent.",options:{bold:true,color:TEAL}},
],{x:0.6,y:4.35,w:12.1,h:0.4,fontSize:12.5,italic:true,isTextBox:true});

// ---- table B: input length / decode ceiling (one row per length) ----
s.addText("Covert-channel capacity by hidden-input size",{x:0.6,y:4.7,w:9,h:0.4,bold:true,fontSize:15,color:INK,isTextBox:true});
const lh=(t)=>({text:t,options:{bold:true,color:"FFFFFF",fill:{color:INK},align:"center",valign:"middle",fontSize:11}});
const lc=(t,col,fill)=>({text:t,options:{align:"center",valign:"middle",fontSize:11,color:col||INK,...(fill?{fill:{color:fill}}:{})}});
const lrows=[
 [lh("Hidden size"),lh("Decoded (/3)"),lh("Result")],
 [lc("8  (“VALIDATE”)"),lc("3/3","FFFFFF",TEAL),lc("recovered ✓","FFFFFF",TEAL)],
 [lc("13 chars"),lc("0/3",RED),lc("failed",RED)],
 [lc("20 chars"),lc("0/3",RED),lc("failed",RED)],
 [lc("30 chars"),lc("0/3",RED),lc("failed",RED)],
 [lc("40 chars"),lc("0/3",RED),lc("failed",RED)],
 [lc("50 chars"),lc("0/3",RED),lc("failed",RED)],
];
s.addTable(lrows,{x:0.6,y:5.1,w:6.1,colW:[2.5,1.8,1.8],
  rowH:[0.3,0.28,0.28,0.28,0.28,0.28,0.28],border:{type:"solid",color:"D5DAE2",pt:1},fill:{color:"FFFFFF"},valign:"middle"});
s.addText([
 {text:"The covert channel reliably carries only ~8 characters — the trigger word.\n\n",options:{bold:true,color:INK}},
 {text:"A full payload can’t be hidden-and-decoded, which is exactly why putting it plainly in the ",options:{color:INK}},
 {text:"user input",options:{bold:true,color:TEAL}},
 {text:" wins: no decoding step at all.",options:{color:INK}},
],{x:7.0,y:5.25,w:5.7,h:1.9,fontSize:13,italic:true,isTextBox:true,valign:"top"});

pres.writeFile({ fileName: "/home/fxr4713/research/StegaCYPHER-Burn/slides/StegaCIPHER-framework.pptx" })
  .then(f=>console.log("WROTE",f));
