"""The shell's pane-records road for the node harnesses that run its inline scripts over a stub document.

The dashboard shell renders the shipped panes and builds the panes defined at the kernel in the browser, from GET /panes (kernel.py:
the head script's read keeps its outcome in window.__rompPaneRecords; _LANDING_PANE_RECORDS_JS checks the rows, builds each pane's
DOM and hands the rows to every consumer's join). A harness that feeds such panes to the inline scripts feeds them through that road:
`records_state` is the head read's state object (settled or still loading), and `RECORDS_DOM` stubs the few DOM calls the builder
makes (createElement, the pane row, the rail's #rail-usage anchor, the tab bar's divider and insertBefore, the head's style), handing
every element it puts in the document to the harness's `adopt` hook, so the harness registers it in its own frame and button maps.

`door_rows` writes a defined pane's record as GET /panes answers it (the door's defaults filled, builtin false). Synthetic records
only (the notes-api demo world; TESTHOST)."""
import json

_DOOR_KEYS = ("id", "title", "source", "on", "experimental", "protocol")


def door_rows(*defs):
    """GET /panes's rows for these definitions, the way the door fills them, in the order given: id, title (the id capitalised when
    absent), source, on and experimental (false when absent), protocol (none for a URL source, else romp), builtin false."""
    out = []
    for d in defs:
        row = {"title": d["id"][:1].upper() + d["id"][1:], "on": False, "experimental": False,
               "protocol": "none" if str(d.get("source", "")).startswith("http") else "romp"}
        row.update({k: v for k, v in d.items() if k in _DOOR_KEYS})
        row["builtin"] = False
        out.append(row)
    return out


def records_state(rows=(), rev="r1", state="ok", body=None, **extra):
    """JS: window.__rompPaneRecords as the head script leaves it. `state` ok: the answer {panes: rows, rev} (or `body` as given);
    loading: no answer yet (a driver settles it with settleRecords); failed: `extra` names the error, status and reauth."""
    st = {"state": state, "body": None, "rev": "", "rows": None, "frames": None, "error": "", "status": 0, "reauth": False, "done": []}
    if state == "ok":
        st["body"] = body if body is not None else {"panes": list(rows), "rev": rev}
        st["status"] = 200
    st.update(extra)
    return "window.__rompPaneRecords = " + json.dumps(st) + ";\n"


# installRecordsDom(doc, opts) patches the stub document `doc` for the builder and returns R, the record of what it did:
#   R.created   every element the builder created, in order
#   R.inserted  every element put in the document (connected), in order: a pane's div, then its frame, before its rail button and tab
#   R.attrs     [id, attribute, connected?] per setAttribute, in order (the frame's sandbox before it is in the document)
#   R.styles    the text of each <style> appended to the head
#   R.events    the detail of each romp-pane-records event dispatched on the window
#   R.row, R.rail, R.bar  the row, the rail's scroll group and the bar the builder inserted into (children in document order)
# opts.bar: the stub's #mtabs, which gains querySelector('.mtabs-div') and insertBefore (the bar's own querySelectorAll stays the
# harness's: its adopt hook adds each new tab to the list it returns); opts.adopt(el): every connected element, after its
# attributes are set; opts.win: the global to watch for the event (default: globalThis).
RECORDS_DOM = r"""
function installRecordsDom(doc, opts) {
  opts = opts || {};
  const R = { created: [], inserted: [], attrs: [], styles: [], events: [] };
  const byId = {};
  function mk(tag) {
    const attrs = {}, kids = [], ev = {}, cls = new Set();
    const el = { tagName: String(tag).toUpperCase(), attrs, children: kids, parentNode: null, textContent: '', hidden: false, title: '', isConnected: false, _ev: ev,
      setAttribute(a, v) { attrs[a] = String(v); if (a === 'class') { cls.clear(); String(v).split(/\s+/).filter(Boolean).forEach((c) => cls.add(c)); } R.attrs.push([attrs.id || '', a, el.isConnected]); },
      getAttribute(a) { return a in attrs ? attrs[a] : null; }, removeAttribute(a) { delete attrs[a]; }, hasAttribute(a) { return a in attrs; },
      appendChild(c) { c.parentNode = el; kids.push(c); if (el.isConnected) connect(c); return c; },
      insertBefore(c, ref) { c.parentNode = el; const i = ref ? kids.indexOf(ref) : -1; if (i >= 0) kids.splice(i, 0, c); else kids.push(c); if (el.isConnected) connect(c); return c; },
      addEventListener(t, f) { (ev[t] = ev[t] || []).push(f); }, removeEventListener() {},
      classList: { add: (c) => cls.add(c), remove: (c) => cls.delete(c), contains: (c) => cls.has(c),
        toggle: (c, on) => { if (on === undefined) on = !cls.has(c); if (on) cls.add(c); else cls.delete(c); return on; } },
      contentWindow: { postMessage() {}, addEventListener() {} }, contentDocument: null,
      style: { setProperty() {}, removeProperty() {}, getPropertyValue: () => '' }, querySelector: () => null, querySelectorAll: () => [] };
    Object.defineProperty(el, 'id', { get: () => attrs.id || '', set: (v) => el.setAttribute('id', v) });
    Object.defineProperty(el, 'className', { get: () => attrs.class || '', set: (v) => el.setAttribute('class', v) });
    R.created.push(el);
    return el;
  }
  function connect(el) { el.isConnected = true; if (el.attrs.id) byId[el.attrs.id] = el; R.inserted.push(el); if (opts.adopt) opts.adopt(el); el.children.forEach(connect); }
  const row = mk('div'); row.attrs.class = 'row'; row.isConnected = true;
  const rail = mk('div'); rail.attrs.class = 'rail-scroll'; rail.isConnected = true;
  const anchor = mk('div'); anchor.attrs.id = 'rail-usage'; rail.appendChild(anchor); anchor.isConnected = true;
  const divider = mk('span'); divider.attrs.class = 'mtabs-div'; divider.isConnected = true;
  R.created.length = 0;   // the stub's own anchors are not the builder's
  R.row = row; R.rail = rail;
  const bar = opts.bar || null;
  if (bar) { bar.querySelector = (s) => (s === '.mtabs-div' ? divider : null); bar.insertBefore = (c, ref) => { c.parentNode = bar; (bar._kids = bar._kids || []).push(c); connect(c); return c; }; R.bar = bar; }
  const gid = doc.getElementById ? doc.getElementById.bind(doc) : () => null;
  doc.getElementById = (id) => (id === 'rail-usage' ? anchor : (id === 'mtabs' && bar) ? bar : (byId[id] || gid(id)));
  const q0 = doc.querySelector ? doc.querySelector.bind(doc) : () => null;
  doc.querySelector = (s) => (s === '.row' ? row : q0(s));
  doc.createElement = mk;
  doc.head = { appendChild: (st) => { R.styles.push(String(st.textContent)); return st; } };
  const W = opts.win || globalThis, d0 = W.dispatchEvent ? W.dispatchEvent.bind(W) : null;
  W.dispatchEvent = (e) => { if (e && e.type === 'romp-pane-records') R.events.push(JSON.parse(JSON.stringify({ state: e.detail.state, rows: e.detail.rows, error: e.detail.error, frames: (e.detail.frames || []).map((f) => f.attrs.id) }))); return d0 ? d0(e) : true; };
  return R;
}
// the head read settling: its state, then every subscriber on the done list, as the head script's own settle does
function settleRecords(state, body, error) {
  const rr = window.__rompPaneRecords; rr.state = state; if (state === 'ok') rr.body = body; else rr.error = error || '';
  const d = rr.done; rr.done = []; d.forEach((f) => { try { f(); } catch (e) {} });
}
"""
