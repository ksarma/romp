// The file BROWSER that lives in the FEED pane (plans/file-browser.md, the user 2026-08-14): a
// breadcrumb bar over one directory's entries — click a directory to descend, a file to open in the
// existing viewer, an ancestor crumb to walk up. It exists because the viewer could only ever show a
// path someone else surfaced; this is the "just look around the repo" half.
//
// It is the viewer's SIBLING overlay and sits BENEATH it (z-index): opening a file from a listing
// overlays the viewer on top with the listing intact underneath, so closing the file returns to the
// listing. The close contract is ownership-aware — the viewer suppresses its viewFileClosed while a
// browser is open beneath (file-view.ts tellShellClosed), and the browser's own browseClosed does the
// pane restore — so the shell puts the feed pane back exactly once, whoever closes last.
//
// The listing rides a WebSocket op (listDir → dirListing), NOT a new HTTP route: the sid field routes
// it to the session-OWNING kernel over the existing federation splice, so browsing a remote session's
// disk needs zero relay code. Staleness is the dirComplete protocol — a client-minted reqId echoed
// back, replies dropped on mismatch, one in-flight ask with newest-value coalescing (the pacing is the
// round-trip itself — an event, not a timer). File BYTES stay on HTTP /file via the existing viewer.
import { openFileView } from "./file-view";
import { fileUrl } from "./preview";

type DirEntry = {
  name: string; isDir: boolean; isLink: boolean;
  size: number; mtime: number; viewable?: boolean;
};
type DirListing = {
  type: "dirListing"; reqId?: number; host?: string; sid?: string;
  base?: string; parent?: string | null; entries?: DirEntry[];
  total?: number; truncated?: boolean; error?: string;
};

let post: (m: Record<string, unknown>) => void = () => { /* bound by initFileBrowse */ };
let reqSeq = 0;
let inflight = false;
let queued: string | null = null;      // newest navigation typed while one ask was in flight
let curPath = "";                      // the listing being shown (or asked for)
let curSid: string | null = null;
let showHidden = false;

function el(tag: string, cls?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

// Same restore contract as the viewer's tellShellClosed, for the browser's own close. Fires on EVERY
// close path; the shell treats browseClosed and viewFileClosed identically.
function tellShellClosed(): void {
  try {
    if (window.parent !== window) window.parent.postMessage({ romp: "browseClosed" }, "*");
  } catch { /* no shell (standalone /feed) — nothing to restore */ }
}

export function closeFileBrowse(): void {
  const box = document.getElementById("romp-filebrowse");
  if (!box) return;
  box.remove();
  document.body.classList.remove("filebrowse-open");
  tellShellClosed();
}

function human(n: number): string {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + " GB";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + " MB";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + " KB";
  return n + " B";
}

// The download idiom the viewer uses: a transient cookie-authed <a download> the BROWSER owns; the
// kernel's attachment disposition keeps the page from navigating.
function startDownload(path: string): void {
  const a = document.createElement("a");
  a.href = fileUrl(path, curSid) + "&download=1";
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function joinPath(base: string, name: string): string {
  return (base === "/" ? "" : base) + "/" + name;
}

/** Open the browser at `path` (as the sid's kernel resolves it — "." means that session's cwd). */
export function openFileBrowse(path: string, sid?: string | null): void {
  const had = document.getElementById("romp-filebrowse");
  curSid = sid || null;
  showHidden = false;
  if (!had) {
    const box = el("div", "filebrowse");
    box.id = "romp-filebrowse";
    document.body.classList.add("filebrowse-open");

    const bar = el("div", "fb-bar");
    const crumbs = el("div", "fb-crumbs");
    crumbs.id = "fb-crumbs";
    const acts = el("div", "fileview-acts");
    const hid = el("button", "fileview-btn") as HTMLButtonElement;
    hid.type = "button"; hid.id = "fb-hidden"; hid.textContent = "Hidden";
    hid.title = "Show dotfiles too";
    hid.addEventListener("click", () => {           // static overlay chrome — direct listeners are
      showHidden = !showHidden;                     // click-safe here, same as the viewer's buttons
      hid.classList.toggle("on", showHidden);
      hid.setAttribute("aria-pressed", String(showHidden));
      ask(curPath);
    });
    const close = el("button", "fileview-btn fileview-close") as HTMLButtonElement;
    close.type = "button"; close.textContent = "✕"; close.title = "Close (Esc)";
    close.setAttribute("aria-label", "Close the file browser");
    close.addEventListener("click", closeFileBrowse);
    acts.appendChild(hid); acts.appendChild(close);
    bar.appendChild(crumbs); bar.appendChild(acts);

    const list = el("div", "fb-list");
    list.id = "fb-list";
    box.appendChild(bar); box.appendChild(list);
    document.body.appendChild(box);

    // ONE click listener on the stable list root — rows are rebuilt per navigation, so per-row
    // listeners are exactly the destroyed-mid-click bug (ui/CLAUDE.md); the crumbs delegate the
    // same way on their own stable bar node.
    list.addEventListener("click", (ev) => {
      const row = (ev.target as HTMLElement).closest("[data-act]") as HTMLElement | null;
      if (!row || !list.contains(row)) return;
      onAct(row);
    });
    crumbs.addEventListener("click", (ev) => {
      const c = (ev.target as HTMLElement).closest("[data-path]") as HTMLElement | null;
      if (!c || !crumbs.contains(c)) return;
      ask(c.dataset.path || "/");
    });
    // Per-entry mechanics one level deeper (the one ctx-menu vocabulary): Copy path / Download /
    // Open folder — the last via the chat's own openFolder path, which stays on the LOCAL kernel.
    list.addEventListener("contextmenu", (ev) => {
      const row = (ev.target as HTMLElement).closest("[data-path]") as HTMLElement | null;
      if (!row || !list.contains(row)) return;
      ev.preventDefault();
      showRowMenu(ev as MouseEvent, row.dataset.path || "", row.dataset.act === "dir");
    });

    // Escape / arrows / Enter / Backspace. TOPMOST-only: the viewer registers its own Escape handler
    // when it opens ON TOP of this, and this one stands down while the viewer exists — the browser
    // opened first, so it registered first and runs first on each keydown.
    const onKey = (e: KeyboardEvent) => {
      const box2 = document.getElementById("romp-filebrowse");
      if (!box2) { document.removeEventListener("keydown", onKey); return; }
      if (document.getElementById("romp-fileview")) return;   // the viewer is topmost — its key
      if (e.key === "Escape") { e.preventDefault(); closeFileBrowse(); return; }
      if (e.key === "Backspace" || e.key === "ArrowLeft") {
        const cs = box2.querySelectorAll<HTMLElement>("#fb-crumbs [data-path]");
        const up = cs.length >= 2 ? cs[cs.length - 2] : null;   // the crumb before the current one
        if (up) { e.preventDefault(); ask(up.dataset.path || "/"); }
        return;
      }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const rows = [...box2.querySelectorAll<HTMLElement>(".fb-row[data-act]")];
        if (!rows.length) return;
        const at = rows.findIndex((r) => r.classList.contains("active"));
        const next = e.key === "ArrowDown" ? Math.min(rows.length - 1, at + 1) : Math.max(0, at - 1);
        rows.forEach((r, i) => r.classList.toggle("active", i === next));
        rows[next].scrollIntoView({ block: "nearest" });
        return;
      }
      if (e.key === "Enter") {
        const active = box2.querySelector<HTMLElement>(".fb-row.active");
        if (active) { e.preventDefault(); onAct(active); }
      }
    };
    document.addEventListener("keydown", onKey);
  }
  ask(path);
}

function onAct(row: HTMLElement): void {
  const p = row.dataset.path || "";
  if (row.dataset.act === "dir") { ask(p); return; }
  if (row.dataset.act === "file") { openFileView(p, curSid); return; }
  if (row.dataset.act === "dl") startDownload(p);       // download-only rows download directly —
}                                                       // a viewer that could only apologize helps nobody

function showRowMenu(e: MouseEvent, path: string, isDir: boolean): void {
  document.getElementById("fb-ctx")?.remove();
  const menu = el("div", "ctx-menu");
  menu.id = "fb-ctx";
  const add = (label: string, fn: () => void) => {
    const item = el("div", "ctx-item");
    item.textContent = label;
    item.addEventListener("click", (ev) => { ev.stopPropagation(); menu.remove(); fn(); });
    menu.appendChild(item);
  };
  add("Copy path", () => { navigator.clipboard?.writeText(path); });
  if (!isDir) add("Download", () => startDownload(path));
  document.body.appendChild(menu);
  const r = menu.getBoundingClientRect();
  menu.style.left = Math.max(0, Math.min(e.clientX, window.innerWidth - r.width - 4)) + "px";
  menu.style.top = Math.max(0, Math.min(e.clientY, window.innerHeight - r.height - 4)) + "px";
  const dismiss = () => { menu.remove(); document.removeEventListener("click", dismiss); };
  document.addEventListener("click", dismiss);
}

// One in-flight ask; a navigation typed meanwhile waits as `queued` and fires when the reply lands —
// the dirComplete pacing (no debounce; the round-trip is the event).
function ask(path: string): void {
  curPath = path;
  if (inflight) { queued = path; return; }
  inflight = true;
  const list = document.getElementById("fb-list");
  if (list) {
    // the loading rule: the romp loader first, never a blank or a frozen listing
    const load = el("div", "fileview-load");
    load.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
      + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
    list.replaceChildren(load);
  }
  post({ type: "listDir", path, sid: curSid || undefined, reqId: ++reqSeq, hidden: showHidden });
}

function onListing(m: DirListing): void {
  if (m.reqId !== reqSeq) return;                 // a stale reply — a newer navigation superseded it
  inflight = false;
  if (queued !== null) { const q = queued; queued = null; ask(q); return; }
  const box = document.getElementById("romp-filebrowse");
  const list = document.getElementById("fb-list");
  const crumbs = document.getElementById("fb-crumbs");
  if (!box || !list || !crumbs) return;           // closed while the ask was in flight

  if (m.error) {
    // Loud, path-naming, and never a dead end: the crumbs above stay clickable as the way out.
    const why = el("div", "fileview-err");
    why.textContent = m.error;
    list.replaceChildren(why);
    return;
  }

  const base = m.base || "/";
  curPath = base;                                  // the kernel's resolved, ~-collapsed truth
  // Breadcrumbs: every ancestor is a click. "~" stays one segment; "/" roots an absolute path.
  crumbs.replaceChildren();
  const segs = base.split("/").filter((s) => s !== "");
  let acc = base.startsWith("~") ? "" : "/";
  const rootCrumb = el("span", "fb-crumb");
  rootCrumb.dataset.path = base.startsWith("~") ? "~" : "/";
  rootCrumb.textContent = base.startsWith("~") ? "~" : "/";
  if (base.startsWith("~")) segs.shift();
  crumbs.appendChild(rootCrumb);
  if (base.startsWith("~")) acc = "~";
  for (const s of segs) {
    const sep = el("span", "fb-crumb-sep"); sep.textContent = "/";
    crumbs.appendChild(sep);
    acc = (acc === "/" ? "" : acc) + "/" + s;
    const c = el("span", "fb-crumb");
    c.dataset.path = acc;
    c.textContent = s;
    crumbs.appendChild(c);
  }
  crumbs.title = base;

  const rows: HTMLElement[] = [];
  for (const en of m.entries || []) {
    const p = joinPath(base, en.name);
    const row = el("div", "fb-row");
    row.dataset.path = p;
    const nm = el("span", "fb-name");
    if (en.isDir) {
      row.dataset.act = "dir";
      nm.textContent = en.name + "/";
      row.classList.add("fb-dir");
      row.title = p + (en.isLink ? "  ·  symlink" : "");
    } else {
      const dlOnly = en.viewable === false;
      row.dataset.act = dlOnly ? "dl" : "file";
      nm.textContent = en.name;
      if (dlOnly) row.classList.add("fb-dlonly");
      row.title = p + (en.isLink ? "  ·  symlink" : "")
        + "  ·  " + new Date(en.mtime * 1000).toLocaleString()
        + (dlOnly ? "  ·  not viewable in the browser — click downloads it" : "");
      const sz = el("span", "fb-size");
      sz.textContent = (dlOnly ? "⤓ " : "") + human(en.size);
      row.appendChild(nm); row.appendChild(sz);
      rows.push(row);
      continue;
    }
    row.appendChild(nm);
    rows.push(row);
  }
  if (!rows.length) {
    const empty = el("div", "fb-more");
    empty.textContent = "empty directory";
    rows.push(empty);
  }
  if (m.truncated) {
    // no silent caps: say exactly what was left out
    const more = el("div", "fb-more");
    more.textContent = (m.entries || []).length + " of " + (m.total || 0)
      + " entries — the rest aren't shown";
    rows.push(more);
  }
  list.replaceChildren(...rows);
  list.scrollTop = 0;
}

/** Bind the kernel poster and listen for the shell's relay + the kernel's listing replies.
 *  Called once, from the feed's boot (beside initFileView). */
export function initFileBrowse(poster: (m: Record<string, unknown>) => void): void {
  post = poster;
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (!m) return;
    if (m.romp === "browseFiles" && typeof m.path === "string") {
      openFileBrowse(m.path || ".", typeof m.sid === "string" ? m.sid : null);
    } else if (m.type === "dirListing") {
      onListing(m as DirListing);
    }
  });
}
