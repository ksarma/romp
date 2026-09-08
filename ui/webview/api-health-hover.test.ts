// The API cell's hover history (2026-09-08): the rail's API cell hover and click detail carry a History
// section read from GET /api-health when they open, the way the spend hover carries its per-window rows.
// The section shows the signal's overall state with its since-time and reason, one row per window in the
// spend hover's label/figure grammar, the newest six transitions with how long each state held, a kernel
// restart as its own row or a divider, and one loud line when the read fails. The shell page is
// kernel-served inline JS with no jsdom harness, so these are source pins (the repo convention, as
// spend-windows-hover.test.ts); tests/test_api_health_hover_browser.py executes the same JS in Chromium and
// tests/test_api_health_hover.py holds the kernel half (the payload, the route's gate, the frame's dedupe).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");
const BACKEND = fs.readFileSync(path.join(ROOT, "kernel", "sdk_backend.py"), "utf8");
const STRIP = fs.readFileSync(path.join(ROOT, "ui", "webview", "strip.ts"), "utf8");
const REFERENCE = fs.readFileSync(path.join(ROOT, "docs", "reference.md"), "utf8");
const GUIDE = fs.readFileSync(path.join(ROOT, "docs", "guide.md"), "utf8");
const JS = KERNEL.split('_LANDING_APIH_JS = """')[1].split('"""')[0];
const HIST = JS.slice(JS.indexOf("// ── History"), JS.indexOf("// full=false is the HOVER"));

test("the history is read from the designed route when the hover or the detail opens, the way the shell's other reads go", () => {
  assert.equal(JS.split("fetch(").length - 1, 1, "one read in the cell's script: the history's");
  assert.ok(HIST.includes("fetch('/api-health',{cache:'no-store'})"));
  // the same shape as the shell's own /usage/fleet read: no token in the call; the romp_token cookie rides, and
  // a same-origin GET sends no Origin, which _origin_ok accepts
  assert.ok(KERNEL.includes("fetch('/usage/fleet',{cache:'no-store'})"));
  assert.match(KERNEL, /if not origin:\n\s+return True/, "_origin_ok accepts an absent Origin");
  // the show, the open and a frame on an open card each read; nothing else does
  assert.ok(JS.includes("tip.classList.remove('ru-modal');tip.style.display='block';el.setAttribute('aria-describedby','ah-tip');load(true);render();}"),
    "show drops the last answer and reads: a hover never paints an earlier hover's numbers while its own read is in flight");
  assert.ok(HIST.includes("function load(fresh){var n=++histSeq;if(fresh)HIST=null;"));
  assert.ok(JS.includes("window.__rompApiClose=close;back.onclick=close;try{tip.focus();}catch(e){}load();}"), "open reads");
  assert.ok(JS.includes("if(tip.style.display!=='block')return;   // an open detail re-renders from the new frame, nothing else does\nload();"), "a frame on an open card re-reads");
});

test("no timers: the show is the event, the newest read wins, and the answer is painted through the held gate", () => {
  assert.ok(!JS.includes("setTimeout") && !JS.includes("setInterval"), "no timer anywhere in the cell's script");
  assert.equal(HIST.split("if(n!==histSeq)return;").length - 1, 2, "both arms of the read drop an answer a newer read superseded");
  assert.equal(HIST.split("if(tip.style.display!=='block')return;if(held){dirty=true;return;}render();").length - 1, 2,
    "the answer repaints an open card only, and never under a held pointer (the frame's own gate)");
});

test("a failed read is one loud line in place of the rows: never stale numbers, never silence", () => {
  assert.ok(HIST.includes("if(!r.ok)throw new Error('HTTP '+r.status);return r.json();"), "a non-2xx is a failure that names its status");
  assert.ok(HIST.includes("HIST=(d&&d.buckets)?d:{error:'malformed answer'};"), "an answer without the signal's shape is a failure too");
  assert.ok(HIST.includes("HIST={error:String((e&&e.message)||e)};"));
  assert.ok(HIST.includes("if(HIST.error)return h+'<div class=\"ah-line ah-err\">Could not read the API history: '+esc(HIST.error)+'</div></div>';"),
    "the line stands where the rows would, and the function returns before any row");
  assert.ok(KERNEL.includes(".ah-err{color:#e5484d}"), "the API-error red, a status color");
  assert.ok(HIST.includes("if(!HIST)return h+'<div class=\"rl-dots ah-wait\"><i></i><i></i><i></i></div></div>';"), "before the first answer: the loader's dots");
  assert.ok(KERNEL.includes(".rl-dots i{width:7px;height:7px;border-radius:50%;background:#9cd2ff;animation:rl-bnc"), "the boot splash's dots, in the accent");
});

test("the section wears the spend hover's grammar: a heading, label/figure rows, the caveat on the label", () => {
  assert.ok(HIST.includes("'<div class=\"ru-tip-win ah-hist\"><div class=ru-tip-name><span>History</span>'"));
  assert.ok(HIST.includes("'<span class=ru-tip-reset>as of '+hms(HIST.asOf)+'</span>'"), "the payload's asOf, so a pinned card's numbers carry their read time");
  // the head: the signal's state word with the dot in its color, since when, and the bucket's reason under it
  assert.ok(HIST.includes("'<div class=\"ru-tip-row ah-head\"><i class=ah-dot data-state='+esc(st)+'></i><span class=ah-word>'+esc(st)+'</span>'"));
  assert.ok(HIST.includes("'<span class=ah-since>since '+hmd(b.stateSince)+'</span>'"));
  assert.ok(HIST.includes("if(b&&b.why)h+='<div class=\"ah-line ru-tip-reset\">'+esc(b.why)+'</div>';"), "the reason in the small annotation grammar, no new font size");
  // the windows come from the config in force, labelled in minutes, the incomplete one saying how long the kernel is up
  assert.ok(HIST.includes("((d.config&&d.config.windows)||[60,300,900]).forEach(function(w){h+=winRow(w,(b.windows||{})[String(w)],d.uptimeS);});"));
  assert.ok(HIST.includes("var lab=(w%60===0?(w/60)+' min':w+' s');if(c&&c.complete===false&&typeof up==='number')lab+=' · kernel up '+dur(up);"));
  assert.ok(HIST.includes("pl(c.requests,'attempt')+' · '+pct(c.rate429)+' 429 · '+pct(c.rate5xx)+' 5xx · '+(c.gaveUp||0)+' gave up · '+pl(c.sessionsRetrying,'session')+' retrying'"),
    "attempts, the 429 and 5xx shares, give-ups, sessions retrying; the rest stays in romp api-health");
  assert.ok(HIST.includes("'no attempts'"), "a window with nothing in it says so");
  assert.ok(HIST.includes("'<div class=\"ru-tip-row ah-hrow\"><span class=ru-tip-k>'+esc(lab)+'</span><span class=ru-tip-v>'+esc(v)+'</span></div>'"), "the spend row's classes");
  // the no-bucket case says so in place of the rows
  assert.ok(HIST.includes("if(!b)h+='<div class=ah-line>No API traffic seen'+(typeof d.bootAt==='number'?' since the kernel started at '+hmd(d.bootAt):' yet')+'.</div>';"));
  // the section sits after the sessions waiting and before the tmux coverage line, in hover and detail alike
  assert.ok(JS.includes("rows.forEach(function(r){h+=rowHTML(r,full);});h+='</div>';}\nh+=histHTML();\nif(m.tmux>0)h+="));
});

test("the tail: six rows newest first, each state's hold, and a restart never hidden", () => {
  assert.ok(JS.includes("var HIST_ROWS=6;"));
  assert.ok(HIST.includes(".sort(function(a,b){return b.t-a.t;})"), "newest first: the spend hover's shortest-window-first order");
  assert.ok(HIST.includes("for(var j=i-1;j>=0;j--)if(rows[j].bucket===r.bucket){end=rows[j].t;break;}"), "a state holds until the SAME bucket's next change");
  assert.ok(HIST.includes("+dur(end-r.t)+(end===now?' so far':'')+"), "the current state is 'so far'");
  // the boot's own row is matched on the kernel's reason, byte for byte
  const why = BACKEND.match(/API_HEALTH_RESTART_WHY = "([^"]+)"/);
  assert.ok(why, "the backend names the boot's reason once");
  assert.ok(JS.includes("var RESTART_WHY='" + (why as RegExpMatchArray)[1] + "';"));
  assert.ok(HIST.includes("restart=r.why===RESTART_WHY"));
  assert.ok(HIST.includes("(restart?' · kernel restarted':'')"));
  // and where the tail crosses this kernel's bootAt with no such row (the bucket was already unknown at the
  // previous stop, so the boot filed nothing) a divider is inserted
  assert.ok(HIST.includes("if(!crossed&&typeof boot==='number'&&r.t<boot){crossed=true;"));
  assert.ok(HIST.includes("if(!prevRestart){out+='<div class=\"ru-tip-row ah-hrow ah-boot\"><span class=ru-tip-k>'+hmd(boot)+'</span><span class=ah-hword>kernel restarted</span></div>';"));
  assert.ok(HIST.includes("prevRestart=restart;shown++;}"));
  // a bucket is named only when there are several; two of one family are told apart by their auth label
  assert.ok(HIST.includes("var word=(multi?bname(d,r.bucket)+' ':'')+r.to"));
  assert.ok(HIST.includes("return dup?fam+' · '+(b.auth||key.split('|')[0]):fam;}"));
  assert.ok(HIST.includes("' · worst of '+nb+' buckets</span>'"));
});

test("accessibility: focus shows the hover, blur hides it, the cell is described by the tip, and the close does not re-pop it", () => {
  assert.ok(JS.includes("el.addEventListener('focus',function(){if(skipFocus||pinned||tip.style.display==='block')return;show(null);});"));
  assert.ok(JS.includes("el.addEventListener('blur',function(){if(!pinned)hide();});"));
  assert.ok(JS.includes("function hide(){tip.style.display='none';el.removeAttribute('aria-describedby');}"));
  assert.ok(JS.includes("el.addEventListener('mouseleave',function(){if(!pinned)hide();});"));
  assert.ok(JS.includes("skipFocus=true;try{(fb&&fb.focus?fb:el).focus();}catch(e){}skipFocus=false;}"),
    "the refocus fires the cell's focus event; the flag covers that one call and is reset when it returns");
  // the cell was a keyboard button before; still is
  assert.ok(KERNEL.includes('<div id=rail-api class=\\"ru-w ru-ah\\" hidden role=button tabindex=0 aria-label=\\"API ok\\" data-state=ok>'));
});

test("the head dot wears status hexes, never the accent; the row and divider styles are quiet", () => {
  assert.ok(KERNEL.includes(".ah-dot[data-state=thrashing]{background:#e5484d;opacity:1}.ah-dot[data-state=recovering]{background:#e67e22;opacity:.7}"));
  for (const rule of KERNEL.match(/[^{}]*\.ah-dot[^{}]*\{[^}]*\}/g) || []) assert.ok(!rule.includes("var(--accent)"), rule);
  assert.ok(KERNEL.includes(".ah-hword{opacity:.8}.ah-hsub{opacity:.55}.ah-boot .ah-hword{font-style:italic;opacity:.6}"));
  assert.ok(KERNEL.includes(".ah-hname{margin-top:6px}.ah-err{color:#e5484d}.ah-wait{margin:5px 0 2px}"));
  assert.ok(!HIST.includes("font-size"), "no new font size: the reason and as-of reuse .ru-tip-reset");
});

test("the frame is untouched: no history rides the push, and the dedupe still compares the whole frame", () => {
  const frame = KERNEL.slice(KERNEL.indexOf("def _api_health_frame(now, tmux):"), KERNEL.indexOf("_APIH_LAST = [None]"));
  for (const k of ['"windows"', '"transitions"', '"buckets"', '"history"', '"overall"']) assert.ok(!frame.includes(k), k);
  assert.ok(KERNEL.includes("s = json.dumps(frame, sort_keys=True)\n    if s == _APIH_LAST[0]:\n        return"));
});

test("the words are plain: no em dash, no romp nouns, no 'fleet'", () => {
  assert.ok(!HIST.includes("—"));
  assert.ok(!HIST.toLowerCase().includes("fleet"));
  for (const w of ["card", "board", "goal", "column"]) assert.ok(!HIST.includes("'" + w), w);
});

test("the strip has no API health cell to mirror (the strip twin is a named follow-up), and the docs carry the hover", () => {
  assert.ok(!STRIP.includes("rail-api") && !STRIP.includes("apiHealth"), "nothing in strip.ts renders the API health cell yet");
  assert.ok(JS.includes("strip.ts") || KERNEL.includes("the VS Code strip twin (strip.ts"), "the follow-up is named in the cell's header");
  const sec = REFERENCE.slice(REFERENCE.indexOf("### The bottom bar's indicator"), REFERENCE.indexOf("## Kernel performance counters"));
  assert.ok(sec.includes("**History**") && sec.includes("`GET /api-health`") && sec.includes("`kernel restarted`"));
  assert.ok(GUIDE.includes("the history under it") && GUIDE.includes("last 1, 5 and 15 minutes"));
});
