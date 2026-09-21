// The browser-legs census: which test modules reach a browser, read from the TypeScript compiler's tree of each module, not
// from its spelling. One module, two readers: ui/webview/ci-browser-legs-census.test.ts (the vscode-extension job's test leg,
// which holds the roster plus the exclusions to this census and runs the planted forms) and scripts/ci-browser-legs.sh (the
// step's pre-run check, in the same job after its npm ci). The compiler is loaded from vscode-extension/node_modules and
// nowhere else, so CI's Shell job, which installs nothing, never runs this: its tools/ci-browser-legs.test.mjs holds the
// parse-free checks (file shape, duplicates, both files, reasons, the ci.yml pins) and says so in its messages. Without the
// compiler this module exits 1 naming that job and judges nothing.
//
// For every test module esbuild's test build bundles (a .test.ts directly in vscode-extension/src, ui or ui/webview, the
// three directories esbuild.js testBuild reads) it derives:
//   launcher:  the module imports ui/webview/real-viewer-leg.ts by RESOLVED path (relative to the module, .js read as .ts, the
//              suffix added when absent) under any binding form (named, aliased, namespace, default, import-equals, require(),
//              await import(), a createRequire-bound loader or the launcher's own exported requireCjs, declared or assigned,
//              destructured or whole) and calls that module's inBrowser THROUGH the binding (an identifier bound to the
//              export, or a literal inBrowser member of a namespace binding; through parentheses, !, as, .call/.apply/.bind).
//              A type-only import binds nothing. The import without a call is recorded (launcherImported) and is not a leg.
//   playwright: the module names a playwright package (playwright, playwright-core, @playwright/test, or a subpath) by any
//              specifier form, either quote; the engines it reaches from a playwright-derived expression (chromium, firefox,
//              webkit: a property, a bracketed literal, a destructured binding, a named import, or a computed name FOLDED by
//              lexical scope through four closed forms: a const bound to a literal, a for-of over an array literal, a parameter
//              typed as a union of string literals, a string-typed parameter whose every direct call site in the module passes a
//              literal); a launch of its own (launch, launchPersistentContext, launchServer, connect, connectOverCDP on a
//              playwright-derived expression, by property, bracket, destructuring or .call/.apply). Derivation stops at a call
//              that is not a loader: a browser returned by launch() or a wrapper's return value is not the package.
//   skipTodo:  every .skip( and .todo( call and every { skip: } or { todo: } option property, with its line, read from the tree,
//              so one held in a comment or a string is not one.
//   swallow:   a shared inBrowser call inside a try statement that has a catch clause, with its line: REPORTED, not refused
//              (such a leg is admitted to the roster; the count over the tree is printed by the census test).
//   embedded:  a string or template literal whose TEXT loads a playwright package (a child-process driver's source): counted
//              as reaching a browser, on the safe side, and never rosterable (the switch never reaches a child process).
//   REFUSALS:  a form the walker cannot classify refuses with file and line, never reports it absent: an import or loader
//              specifier that is not a string literal and folds through no closed form; a computed member with a name it
//              cannot fold on a playwright or launcher binding; the inBrowser binding used as a value, not called; a local
//              declaration shadowing a launcher or playwright binding; a parse diagnostic. The CLI exits 2 on any refusal.
// THE CENSUS RULE: a module is a browser leg when it calls the shared launcher through its binding, names a playwright
// package, or holds a driver string that does. THE ROSTER GATE (rosterGap, null when the leg passes): a shared call, no
// playwright package of its own, no launch of its own, no driver string, no skip or todo; the engines it names are a separate
// verdict (engineNames: the gating job installs Chromium only). A leg's class (classOf): shared, own, both, embedded.
// Two residuals, stated: the fold of a string-typed parameter reads the module's own call sites only (no module imports a
// .test.ts, so a caller from another module does not arise); and derivation stops at a non-loader call, so a launch made on a
// wrapper function's return value is not a launch to the walker. Neither is a spelling list: each is a rule with a stated
// boundary, and the census test prints the counts the tree gives them.
// CLI, from vscode-extension/: node scripts/browser-legs-census.mjs [--list|--tsv|--json] [--strict-computed] [root]. --list
// prints the legs' bundle paths (out-tests/<dir>/<name>.test.js, the roster's spelling); --tsv one line per module read, leg
// or not: bundle TAB 1 or 0 (a leg or not) TAB roster gap (- when it passes; for a module that is not a leg, the launcher
// import it never calls, or -) TAB engines other than Chromium (- when none) TAB class, the form the script reads; --json the
// whole record. --strict-computed refuses every computed member instead of folding (a probe, not a mode either reader uses).
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const EXT = path.resolve(HERE, "..");
export const REPO = path.resolve(EXT, "..");
export const LEG_DIRS = ["vscode-extension/src", "ui", "ui/webview"];
export const LAUNCHER_REL = "ui/webview/real-viewer-leg.ts";
const PW_PACKAGES = ["playwright", "playwright-core", "@playwright/test"];
const ENGINES = new Set(["chromium", "firefox", "webkit"]);
const LAUNCHES = new Set(["launch", "launchPersistentContext", "launchServer", "connect", "connectOverCDP"]);

/** typescript, from vscode-extension/node_modules and nowhere else; a named error when npm ci has not run. */
export function loadTypescript() {
  const req = createRequire(path.join(EXT, "package.json"));
  try { return req("typescript"); }
  catch (e) {
    throw new Error("browser-legs-census: the typescript compiler is not installed under vscode-extension/node_modules (run npm ci in vscode-extension/ first; CI's Shell job never has it and runs the parse-free checks in tools/ci-browser-legs.test.mjs instead): " + String(e && e.message).split("\n")[0]);
  }
}

const isPwPackage = (spec) => PW_PACKAGES.some((p) => spec === p || spec.startsWith(p + "/"));

/** Classify one module. `file` is absolute; `src` its text; `opts.strictComputed` refuses every computed member on a tracked binding. */
export function classify(ts, file, src, opts = {}) {
  const rel = path.relative(opts.root || REPO, file);
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const lineOf = (n) => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const refusals = [];
  const refuse = (n, why) => { const msg = rel + ":" + lineOf(n) + ": " + why + ": " + n.getText(sf).split("\n")[0].slice(0, 120); if (!refusals.includes(msg)) refusals.push(msg); };
  const diags = sf.parseDiagnostics;
  if (diags.length) {
    const d = diags[0];
    return { rel, refusals: [rel + ":" + (sf.getLineAndCharacterOfPosition(d.start ?? 0).line + 1) + ": the parser reports a diagnostic, so the module is refused rather than judged over the parser's recovery: " + ts.flattenDiagnosticMessageText(d.messageText, " ")] };
  }
  const launcherAbs = path.join(opts.root || REPO, LAUNCHER_REL);
  const resolveSpec = (spec) => {
    if (!spec.startsWith(".")) return { kind: isPwPackage(spec) ? "playwright" : "package", spec };
    let abs = path.resolve(path.dirname(file), spec);
    if (/\.[cm]?js$/.test(abs)) abs = abs.replace(/\.[cm]?js$/, ".ts"); else if (!/\.[cm]?ts$/.test(abs)) abs += ".ts";
    return { kind: abs === launcherAbs ? "launcher" : "local", spec, abs };
  };

  // bindings: name -> { module: "launcher"|"playwright"|..., member: null (whole module) | "inBrowser" | "chromium" | ... }
  const bindings = new Map();
  const declared = new Set();          // every locally declared identifier not from an import/loader, for shadow detection
  const loaders = new Set(["require"]); // identifiers that load a module when called with a string: require, createRequire results
  const pwDerived = new Map();          // identifier -> { engine?: string, launch?: string } for expressions derived from playwright
  const engines = new Set(), launches = [], skipTodo = [], swallow = [];
  let sharedCalls = 0;
  const playwright = new Set();
  const launcherImported = [];

  const unwrap = (e) => {
    for (;;) {
      if (ts.isAwaitExpression(e) || ts.isAsExpression(e) || ts.isTypeAssertionExpression(e) || ts.isSatisfiesExpression(e) || ts.isNonNullExpression(e) || ts.isParenthesizedExpression(e)) e = e.expression;
      else return e;
    }
  };
  const literalName = (n) => ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isNumericLiteral(n) ? n.text : null;
  /** The set of string values an identifier can take at a USE SITE, through closed forms only, by lexical scope: from the use
   *  upward, the first enclosing scope that declares the name decides: a const/let bound to a literal; a for-of over an array
   *  literal of literals; a parameter typed as a union of string literal types; a parameter typed `string` whose every call
   *  site in the module passes a literal at that position (the function named by identifier, called directly). Anything else,
   *  or a name no enclosing scope declares: null (refuse). */
  const foldIdentifier = (id) => {
    const name = id.text;
    const declOf = (scope) => {
      let hit = null;
      const look = (n) => {
        if (hit) return;
        if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === name) { hit = n; return; }
        if (ts.isParameter(n) && ts.isIdentifier(n.name) && n.name.text === name) { hit = n; return; }
        if (ts.isBindingElement(n) && ts.isIdentifier(n.name) && n.name.text === name) { hit = n; return; }
        if (n !== scope && (ts.isFunctionLike(n) || ts.isBlock(n) || ts.isForOfStatement(n) || ts.isForInStatement(n) || ts.isForStatement(n) || ts.isCatchClause(n))) return; // an inner scope's declarations are not ours
        ts.forEachChild(n, look);
      };
      if (ts.isFunctionLike(scope)) { for (const prm of scope.parameters) look(prm); if (!hit && scope.body) { if (ts.isBlock(scope.body)) for (const st of scope.body.statements) look(st); } }
      else if (ts.isForOfStatement(scope) || ts.isForInStatement(scope) || ts.isForStatement(scope)) { if (scope.initializer) look(scope.initializer); }
      else if (ts.isCatchClause(scope)) { if (scope.variableDeclaration) look(scope.variableDeclaration); }
      else if (ts.isBlock(scope) || ts.isSourceFile(scope)) for (const st of scope.statements) look(st);
      return hit;
    };
    let decl = null;
    for (let p = id.parent; p && !decl; p = p.parent) if (ts.isFunctionLike(p) || ts.isBlock(p) || ts.isForOfStatement(p) || ts.isForInStatement(p) || ts.isForStatement(p) || ts.isCatchClause(p) || ts.isSourceFile(p)) decl = declOf(p);
    if (!decl) return null;
    if (ts.isVariableDeclaration(decl)) {
      if (decl.initializer) { const v = literalName(unwrap(decl.initializer)); if (v !== null) return [v]; return null; }
      const p = decl.parent, fo = p && p.parent;
      if (fo && ts.isForOfStatement(fo) && fo.initializer === p) {
        const arr = unwrap(fo.expression);
        if (ts.isArrayLiteralExpression(arr)) { const vals = arr.elements.map((el) => literalName(unwrap(el))); if (vals.every((v) => v !== null)) return vals; }
      }
      return null;
    }
    if (ts.isParameter(decl)) {
      if (decl.type && ts.isUnionTypeNode(decl.type)) { const vals = decl.type.types.map((t) => ts.isLiteralTypeNode(t) && ts.isStringLiteral(t.literal) ? t.literal.text : null); if (vals.every((v) => v !== null)) return vals; return null; }
      if (decl.type && ts.isLiteralTypeNode(decl.type) && ts.isStringLiteral(decl.type.literal)) return [decl.type.literal.text];
      // a string-typed parameter: every direct call of the named function in this module passes a literal at this position
      const fn = decl.parent;
      if (!(decl.type && decl.type.kind === ts.SyntaxKind.StringKeyword)) return null;
      let fname = null;
      if (ts.isFunctionDeclaration(fn) && fn.name) fname = fn.name.text;
      else if ((ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) && ts.isVariableDeclaration(fn.parent) && ts.isIdentifier(fn.parent.name)) fname = fn.parent.name.text;
      if (!fname) return null;
      const at = fn.parameters.indexOf(decl);
      const vals = []; let calls = 0, bad = false;
      const seek = (n) => { if (ts.isCallExpression(n) && ts.isIdentifier(unwrap(n.expression)) && unwrap(n.expression).text === fname) { calls++; const a = n.arguments[at]; const v = a && literalName(unwrap(a)); if (v === null || v === undefined) { const inner = a && ts.isIdentifier(unwrap(a)) ? foldIdentifier(unwrap(a)) : null; if (inner) vals.push(...inner); else bad = true; } else vals.push(v); } if (ts.isIdentifier(n) && n !== fn.name && n.text === fname && !(n.parent && ts.isCallExpression(n.parent) && unwrap(n.parent.expression) === n)) bad = true; ts.forEachChild(n, seek); };
      seek(sf);
      if (bad || calls === 0) return null;
      return [...new Set(vals)];
    }
    return null;
  };
  /** The member name(s) an access reaches: a literal property, a bracketed literal, or a folded identifier; null when unknowable. */
  const memberNames = (acc) => {
    if (ts.isPropertyAccessExpression(acc)) return [acc.name.text];
    const a = unwrap(acc.argumentExpression);
    const lit = literalName(a);
    if (lit !== null) return [lit];
    if (opts.strictComputed) return null;
    if (ts.isIdentifier(a)) return foldIdentifier(a);
    return null;
  };
  const rootOf = (e) => { e = unwrap(e); while (ts.isPropertyAccessExpression(e) || ts.isElementAccessExpression(e) || ts.isCallExpression(e) || ts.isNonNullExpression(e) || ts.isParenthesizedExpression(e)) e = e.expression; return e; };
  /** Is `e` a loader call (require("x"), req("x"), import("x"))? Returns the resolved spec or null; refuses a non-literal. */
  const loaderCall = (e) => {
    e = unwrap(e);
    if (!ts.isCallExpression(e)) return null;
    const c = unwrap(e.expression);
    const isLoader = (ts.isIdentifier(c) && loaders.has(c.text)) || c.kind === ts.SyntaxKind.ImportKeyword;
    if (!isLoader) return null;
    const arg = e.arguments[0];
    const spec = arg && literalName(unwrap(arg));
    if (spec !== null && spec !== undefined) return resolveSpec(spec);
    const folded = arg && foldSpecifier(unwrap(arg), 0);
    if (!folded) { refuse(e, "a loader whose specifier is not a string literal and folds through no closed form (refused, on the safe side)"); return { kind: "refused" }; }
    return folded;
  };
  /** A non-literal specifier folded through closed forms: an identifier bound to a const (one level down, recursively), a
   *  path.resolve/path.join/pathToFileURL(...).href/new URL(...) call or a `+`/template concatenation whose literal pieces are
   *  read: such an expression is a filesystem path, which names a playwright package or the launcher only when one of its
   *  literal pieces does (over-inclusive, on the safe side); otherwise a local file. Anything else: null (refuse). */
  const foldSpecifier = (e, depth) => {
    if (depth > 4) return null;
    e = unwrap(e);
    const lit = literalName(e);
    if (lit !== null) return resolveSpec(lit);
    const pieces = [];
    const collect = (x) => {
      x = unwrap(x);
      const l = literalName(x); if (l !== null) { pieces.push(l); return true; }
      if (ts.isTemplateExpression(x)) { pieces.push(x.head.text); for (const sp of x.templateSpans) { if (!collect(sp.expression)) return false; pieces.push(sp.literal.text); } return true; }
      if (ts.isBinaryExpression(x) && x.operatorToken.kind === ts.SyntaxKind.PlusToken) return collect(x.left) && collect(x.right);
      if (ts.isIdentifier(x)) { const init = constInitializer(x.text); if (init === undefined) return false; if (init === null) { pieces.push("<" + x.text + ">"); return true; } return collect(init); }
      if (ts.isPropertyAccessExpression(x)) { const r = rootOf(x); if (ts.isIdentifier(r) && ["process", "import", "path", "os"].includes(r.text)) { pieces.push("<" + x.getText(sf) + ">"); return true; } if (x.name.text === "href" || x.name.text === "pathname") return collect(x.expression); return false; }
      if (ts.isMetaProperty(x)) { pieces.push("<import.meta>"); return true; }
      if (ts.isCallExpression(x)) {
        const c = unwrap(x.expression);
        const isPath = (ts.isPropertyAccessExpression(c) && ts.isIdentifier(c.expression) && c.expression.text === "path" && ["resolve", "join", "normalize", "dirname"].includes(c.name.text)) || (ts.isIdentifier(c) && ["pathToFileURL", "fileURLToPath", "resolve", "join"].includes(c.text)) || (ts.isPropertyAccessExpression(c) && ts.isIdentifier(c.expression) && c.expression.text === "process" && c.name.text === "cwd");
        if (!isPath) return false;
        for (const a of x.arguments) if (!collect(a)) return false;
        return true;
      }
      if (ts.isNewExpression(x) && ts.isIdentifier(x.expression) && x.expression.text === "URL") { for (const a of x.arguments || []) if (!collect(a)) return false; return true; }
      return false;
    };
    if (!collect(e)) return null;
    const text = pieces.join("/");
    if (PW_PACKAGES.some((p) => text.includes(p))) return { kind: "playwright", spec: text };
    if (text.includes("real-viewer-leg")) return { kind: "launcher", spec: text };
    return { kind: "local", spec: text };
  };
  /** The initializer of the one top-level or block const/let `name` in the module (undefined: not found or several; null: declared without one). */
  const constInitializer = (name) => {
    let hits = [];
    const visit = (n) => { if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === name) hits.push(n); ts.forEachChild(n, visit); };
    visit(sf);
    if (hits.length !== 1) return undefined;
    return hits[0].initializer === undefined ? null : hits[0].initializer;
  };
  /** Is `e` derived from playwright? Returns the chain of member names from the package root, or null. */
  const pwChain = (e) => {
    e = unwrap(e);
    const chain = [];
    for (;;) {
      if (ts.isPropertyAccessExpression(e) || ts.isElementAccessExpression(e)) {
        const names = memberNames(e);
        if (names === null) { if (isTrackedRoot(rootOf(e))) { refuse(e, "a computed member with a name the walker cannot fold on a playwright or launcher binding"); return { refused: true }; } return null; }
        chain.unshift(names); e = unwrap(e.expression); continue;
      }
      if (ts.isCallExpression(e)) { const l = loaderCall(e); if (l && l.kind === "playwright") return chain; if (l && l.kind === "refused") return { refused: true }; return null; }
      if (ts.isIdentifier(e)) {
        const b = bindings.get(e.text);
        if (b && b.module === "playwright") { if (b.member) chain.unshift([b.member]); return chain; }
        const d = pwDerived.get(e.text);
        if (d) { chain.unshift(...d.chain); return chain; }
        return null;
      }
      return null;
    }
  };
  const isTrackedRoot = (r) => ts.isIdentifier(r) && ((bindings.has(r.text) && ["playwright", "launcher"].includes(bindings.get(r.text).module)) || pwDerived.has(r.text));
  const noteChain = (chain) => { for (const names of chain) for (const n of names) if (ENGINES.has(n)) engines.add(n); };

  // pass 1: imports, loaders, declarations (source order; a second pass below picks up derived bindings declared before use)
  const bindName = (nm, module, member) => {
    if (ts.isIdentifier(nm)) bindings.set(nm.text, { module, member });
    else if (ts.isObjectBindingPattern(nm)) for (const el of nm.elements) { if (el.dotDotDotToken) { bindings.set(el.name.text, { module, member }); continue; } const prop = el.propertyName ? (ts.isIdentifier(el.propertyName) ? el.propertyName.text : literalName(el.propertyName)) : (ts.isIdentifier(el.name) ? el.name.text : null); if (prop === null) { refuse(el, "a destructured member with a name the walker cannot read"); continue; } if (ts.isIdentifier(el.name)) bindings.set(el.name.text, { module, member: member ? member + "." + prop : prop }); else refuse(el, "a nested destructuring the walker does not follow"); }
    else refuse(nm, "an array destructuring of a module the walker does not follow");
  };
  const walk1 = (n) => {
    if (ts.isImportDeclaration(n)) {
      const spec = literalName(n.moduleSpecifier);
      if (spec === null) refuse(n, "an import whose specifier is not a string literal (refused, on the safe side)");
      else {
        const r = resolveSpec(spec);
        if (r.kind === "playwright") playwright.add(spec);
        const c = n.importClause;
        if (r.kind === "launcher" && !(c && c.isTypeOnly)) launcherImported.push(lineOf(n));
        if (c && !c.isTypeOnly) {
          if (c.name) bindings.set(c.name.text, { module: r.kind, member: "default" });
          if (c.namedBindings) {
            if (ts.isNamespaceImport(c.namedBindings)) bindings.set(c.namedBindings.name.text, { module: r.kind, member: null });
            else for (const el of c.namedBindings.elements) if (!el.isTypeOnly) bindings.set(el.name.text, { module: r.kind, member: (el.propertyName || el.name).text });
          }
        }
      }
    } else if (ts.isImportEqualsDeclaration(n)) {
      if (ts.isExternalModuleReference(n.moduleReference)) { const spec = literalName(n.moduleReference.expression); if (spec === null) refuse(n, "an import = require whose specifier is not a string literal"); else { const r = resolveSpec(spec); if (r.kind === "playwright") playwright.add(spec); if (r.kind === "launcher") launcherImported.push(lineOf(n)); bindings.set(n.name.text, { module: r.kind, member: null }); } }
    } else if (ts.isExportDeclaration(n) && n.moduleSpecifier) {
      const spec = literalName(n.moduleSpecifier);
      if (spec === null) refuse(n, "an export from whose specifier is not a string literal"); else if (isPwPackage(spec)) playwright.add(spec);
    } else if (ts.isVariableDeclaration(n) && n.initializer) {
      const init = unwrap(n.initializer);
      // a createRequire(...) result is a loader
      if (ts.isCallExpression(init) && ((ts.isIdentifier(unwrap(init.expression)) && unwrap(init.expression).text === "createRequire") || (ts.isPropertyAccessExpression(unwrap(init.expression)) && unwrap(init.expression).name.text === "createRequire")) && ts.isIdentifier(n.name)) loaders.add(n.name.text);
    } else if (ts.isFunctionDeclaration(n) && n.name) declared.add(n.name.text);
    else if (ts.isClassDeclaration(n) && n.name) declared.add(n.name.text);
    ts.forEachChild(n, walk1);
  };
  walk1(sf);
  // launcher's own requireCjs export, imported by a leg, is a loader too
  for (const [name, b] of bindings) if (b.module === "launcher" && b.member === "requireCjs") loaders.add(name);

  // pass 2: loader-bound variables and assignments (declaration or assignment), playwright-derived bindings; to a fixpoint
  const bindLoaded = (target, valueExpr, holder) => {
    const v = unwrap(valueExpr);
    // a loader call, possibly through a member chain: require("x").y
    let e = v, members = [];
    while (ts.isPropertyAccessExpression(e) || ts.isElementAccessExpression(e)) { const names = memberNames(e); if (names === null) { members = null; break; } members.unshift(names); e = unwrap(e.expression); }
    const l = loaderCall(e);
    if (l && l.kind !== "refused") {
      if (l.kind === "playwright") playwright.add(l.spec);
      if (l.kind === "launcher") launcherImported.push(lineOf(holder));
      if (members === null) { refuse(holder, "a computed member with a name the walker cannot fold on a loaded module"); return true; }
      const member = members.length ? members.map((m) => m.join("|")).join(".") : null;
      if (l.kind === "playwright") { for (const m of members) for (const x of m) if (ENGINES.has(x)) engines.add(x); }
      if (ts.isIdentifier(target)) { if (!bindings.has(target.text)) { bindings.set(target.text, { module: l.kind, member }); return true; } return false; }
      let changed = false;
      const before = bindings.size; bindName(target, l.kind, member); changed = bindings.size !== before;
      if (l.kind === "playwright") for (const [, b] of bindings) if (b.module === "playwright" && b.member) for (const x of b.member.split(".")) if (ENGINES.has(x)) engines.add(x);
      return changed;
    }
    if (l && l.kind === "refused") return false;
    // derived from a playwright binding: const b = pw.firefox; const { launch } = pw.chromium; pw2 = pw
    const chain = pwChain(v);
    if (chain && !chain.refused) {
      let changed = false;
      if (ts.isIdentifier(target)) { if (!pwDerived.has(target.text) && !bindings.has(target.text)) { pwDerived.set(target.text, { chain }); changed = true; } }
      else if (ts.isObjectBindingPattern(target)) for (const el of target.elements) { const prop = el.propertyName ? (ts.isIdentifier(el.propertyName) ? el.propertyName.text : literalName(el.propertyName)) : (ts.isIdentifier(el.name) ? el.name.text : null); if (prop === null || !ts.isIdentifier(el.name)) { refuse(el, "a destructuring of a playwright expression the walker cannot read"); continue; } if (!pwDerived.has(el.name.text)) { pwDerived.set(el.name.text, { chain: [...chain, [prop]] }); changed = true; } if (LAUNCHES.has(prop)) launches.push({ line: lineOf(el), how: "destructured " + prop }); }
      else refuse(target, "an array destructuring of a playwright expression");
      noteChain(chain);
      return changed;
    }
    return false;
  };
  for (let pass = 0, changed = true; changed && pass < 8; pass++) {
    changed = false;
    const walk2 = (n) => {
      if (ts.isVariableDeclaration(n) && n.initializer) { if (bindLoaded(n.name, n.initializer, n)) changed = true; }
      else if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken) { if (bindLoaded(unwrap(n.left), n.right, n)) changed = true; }
      ts.forEachChild(n, walk2);
    };
    walk2(sf);
    if (pass === 7 && changed) refuse(sf, "the binding walk did not settle in 8 passes");
  }
  // the engines every playwright binding names by its member path (const { firefox } = require("playwright"))
  for (const [, b] of bindings) if (b.module === "playwright" && b.member) for (const x of b.member.split(".")) for (const y of x.split("|")) if (ENGINES.has(y)) engines.add(y);

  // shadowing: a local declaration (variable, function, class, parameter) with an import binding's name refuses
  const walkShadow = (n) => {
    if ((ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isFunctionDeclaration(n) || ts.isClassDeclaration(n)) && n.name && ts.isIdentifier(n.name)) {
      const b = bindings.get(n.name.text);
      if (b && ((b.module === "launcher" && (b.member === "inBrowser" || b.member === null)) || b.module === "playwright")) { const init = ts.isVariableDeclaration(n) && n.initializer ? unwrap(n.initializer) : null; const viaLoader = init && (loaderCall(init) || pwChain(init)); const isBinderItself = ts.isVariableDeclaration(n) && (viaLoader || (init === null && n.initializer === undefined)); if (!isBinderItself && !(ts.isVariableDeclaration(n) && n.initializer && (literalName(init) === null && (init.kind === ts.SyntaxKind.NullKeyword || init.kind === ts.SyntaxKind.UndefinedKeyword)))) refuse(n, "a local declaration shadows an import binding of the launcher or of playwright (the walker cannot tell which one a later use reaches)"); }
    }
    ts.forEachChild(n, walkShadow);
  };
  walkShadow(sf);

  // pass 3: calls and references
  const inTryWithCatch = (n) => { for (let p = n.parent; p; p = p.parent) { if (ts.isTryStatement(p) && p.catchClause && p.tryBlock.pos <= n.pos && n.end <= p.tryBlock.end) return true; if (ts.isFunctionLike(p)) return false; } return false; };
  const walk3 = (n) => {
    if (ts.isCallExpression(n)) {
      let c = unwrap(n.expression);
      // .call / .apply / .bind on the callee
      let viaCall = false;
      if ((ts.isPropertyAccessExpression(c)) && ["call", "apply", "bind"].includes(c.name.text)) { c = unwrap(c.expression); viaCall = true; }
      if (ts.isIdentifier(c)) {
        const b = bindings.get(c.text);
        if (b && b.module === "launcher" && b.member === "inBrowser") { sharedCalls++; if (inTryWithCatch(n)) swallow.push(lineOf(n)); }
        const d = pwDerived.get(c.text);
        if (d) { const last = d.chain[d.chain.length - 1] || []; if (last.some((x) => LAUNCHES.has(x))) launches.push({ line: lineOf(n), how: "call of destructured " + last.join("|") + (viaCall ? " via .call/.apply" : "") }); }
        if (b && b.module === "playwright" && b.member && LAUNCHES.has(b.member.split(".").pop())) launches.push({ line: lineOf(n), how: "call of imported " + b.member });
      } else if (ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c)) {
        const names = memberNames(c);
        const obj = unwrap(c.expression);
        if (names === null) { if (isTrackedRoot(rootOf(c))) refuse(c, "a computed member with a name the walker cannot fold on a playwright or launcher binding"); }
        else {
          if (names.some((x) => x === "skip" || x === "todo")) skipTodo.push({ line: lineOf(n), what: "." + names.join("|") + "(" });
          // launcher namespace: leg.inBrowser(...)
          if (ts.isIdentifier(obj)) { const b = bindings.get(obj.text); if (b && b.module === "launcher" && b.member === null && names.includes("inBrowser")) { sharedCalls++; if (inTryWithCatch(n)) swallow.push(lineOf(n)); } }
          if (names.some((x) => LAUNCHES.has(x))) { const chain = pwChain(obj); if (chain && !chain.refused) { noteChain(chain); launches.push({ line: lineOf(n), how: "." + names.join("|") + "(" + (viaCall ? " via .call/.apply" : "") }); } }
          const chain = pwChain(c); if (chain && !chain.refused) noteChain(chain);
        }
      }
      // { skip: ..., todo: ... } option properties in an argument object literal
      for (const a of n.arguments) if (ts.isObjectLiteralExpression(unwrap(a))) for (const p of unwrap(a).properties) { const nm = p.name && (ts.isIdentifier(p.name) ? p.name.text : literalName(p.name)); if (nm === "skip" || nm === "todo") skipTodo.push({ line: lineOf(p), what: "{ " + nm + ": } option" }); }
    } else if (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) {
      // an engine read that is not a call: const b = pw.firefox (bound above), or await pw.firefox.launch handled at the call
      if (!(n.parent && (ts.isCallExpression(n.parent) && n.parent.expression === n))) { const chain = pwChain(n); if (chain && !chain.refused) noteChain(chain); }
    } else if (ts.isIdentifier(n)) {
      // a reference to the inBrowser binding that is not a callee, a declaration name, a property name or an import clause: refuse
      const b = bindings.get(n.text);
      if (b && b.module === "launcher" && b.member === "inBrowser") {
        const p = n.parent;
        const isCallee = p && ts.isCallExpression(p) && unwrap(p.expression) === n;
        const isDecl = p && (ts.isImportSpecifier(p) || ts.isBindingElement(p) || ts.isVariableDeclaration(p) || ts.isImportClause(p) || (ts.isBinaryExpression(p) && p.left === n));
        const isPropName = p && (ts.isPropertyAccessExpression(p) && p.name === n) || (p && ts.isPropertyAssignment(p) && p.name === n);
        if (!isCallee && !isDecl && !isPropName) refuse(n, "the launcher's inBrowser binding used as a value, not called (the walker cannot follow where it is called from)");
      }
    }
    ts.forEachChild(n, walk3);
  };
  walk3(sf);

  // a string or template literal whose TEXT names a playwright package or the launcher: source for a child process (a driver),
  // a source pin, or a message; the module's own code reaches no browser through it, so it is reported as its own class
  const embedded = [];
  const walkStr = (n) => {
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n)) {
      const t = n.text;
      if (/(require|import)\s*\(\s*["'`](playwright(-core)?|@playwright\/test)["'`]|from\s+["'`](playwright(-core)?|@playwright\/test)["'`]/.test(t)) embedded.push({ line: lineOf(n), what: "playwright loaded by source held in a string (a child-process driver)" });
    }
    ts.forEachChild(n, walkStr);
  };
  walkStr(sf);
  const seenL = new Set(); const launchesU = launches.filter((l) => { const k = l.line + "|" + l.how; if (seenL.has(k)) return false; seenL.add(k); return true; }); launches.length = 0; launches.push(...launchesU);
  const reaches = sharedCalls > 0 || playwright.size > 0 || embedded.length > 0;
  return { rel, refusals, launcherImported: launcherImported.length > 0, sharedCalls, embedded, playwright: [...playwright].sort(), engines: [...engines].sort(), launches, skipTodo, swallow, reaches };
}

const bundleOf = (dir, f) => "out-tests/" + dir + "/" + f.replace(/\.test\.ts$/, ".test.js");

/** The census over a tree: { legs: [bundle...] sorted, byBundle: Map bundle -> classify record (every module read, leg or
 *  not), refusals: [...] }. */
export function census(root = REPO, opts = {}) {
  root = path.resolve(root);
  const ts = loadTypescript();
  const legs = [], byBundle = new Map(), refusals = [];
  for (const dir of LEG_DIRS) {
    const abs = path.join(root, dir);
    if (!fs.existsSync(abs)) continue;
    for (const f of fs.readdirSync(abs).filter((f) => f.endsWith(".test.ts")).sort()) {
      const file = path.join(abs, f);
      const r = classify(ts, file, fs.readFileSync(file, "utf8"), { ...opts, root });
      const bundle = bundleOf(dir, f);
      byBundle.set(bundle, r);
      if (r.refusals.length) refusals.push(...r.refusals);
      if (r.reaches) legs.push(bundle);
    }
  }
  return { legs: legs.sort(), byBundle, refusals };
}

/** The gap between a leg and the roster gate, or null when it passes: the sentence both readers print. */
export function rosterGap(r) {
  if (r.sharedCalls === undefined) return "refused by the census (above)";
  if (r.sharedCalls === 0) {
    if (r.embedded.length && !r.playwright.length) return "drives playwright from a child process whose source is held in a string (line " + r.embedded[0].line + "), which the switch never reaches";
    if (r.launcherImported) return "imports ui/webview/real-viewer-leg.ts and never calls its inBrowser through that import: call it, or remove the line";
    return "never imports the shared launcher, ui/webview/real-viewer-leg.ts";
  }
  if (r.playwright.length) return "loads playwright itself (" + r.playwright.join(", ") + "): inBrowser owns the one playwright read a rostered leg needs";
  if (r.launches.length) return "holds a launch of its own (line " + r.launches[0].line + ": " + r.launches[0].how + ")";
  if (r.embedded.length) return "drives playwright from a child process whose source is held in a string (line " + r.embedded[0].line + "), which the switch never reaches";
  if (r.skipTodo.length) return "holds a skip or todo of its own (line " + r.skipTodo[0].line + ": " + r.skipTodo[0].what + ")";
  return null;
}
/** The engines other than Chromium a leg reaches, as the exclusions reasons spell them: ["Firefox", "WebKit"] or a subset. */
export function engineNames(r) {
  const out = [], eng = r.engines || [];
  if (eng.includes("firefox")) out.push("Firefox");
  if (eng.includes("webkit")) out.push("WebKit");
  return out;
}
/** A leg's class: shared (the launcher alone), own (its own playwright alone), both, embedded (a driver string alone); none for a
 *  module that is not a leg. */
export function classOf(r) {
  if (r.sharedCalls === undefined) return "refused";
  const shared = r.sharedCalls > 0, own = r.playwright.length > 0;
  if (shared && own) return "both";
  if (shared) return "shared";
  if (own) return "own";
  if (r.embedded.length) return "embedded";
  return "none";
}
/** The sentence an exclusions reason carries for a leg of the embedded class, and no other leg's reason does. */
export const EMBEDDED_PHRASE = "loads playwright in a child process it drives from a string; the switch never reaches it";
/** The phrase an exclusions reason that names an engine carries, why the gating job cannot run the leg: the reason reads
 *  "launches <Firefox and/or WebKit>; <this phrase>". The census test holds every engine reason to it and quotes it in the red. */
export const ENGINE_PHRASE = "the gating job installs Chromium only";

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const strict = args.includes("--strict-computed");
  const mode = args.includes("--json") ? "json" : args.includes("--tsv") ? "tsv" : "list";
  const root = args.find((a) => !a.startsWith("--")) || REPO;
  let c;
  try { c = census(root, { strictComputed: strict }); }
  catch (e) { process.stderr.write(String(e && e.message) + "\n"); process.exit(1); }
  if (mode === "json") {
    const out = { legs: c.legs, refusals: c.refusals, modules: {} };
    for (const [b, r] of c.byBundle) out.modules[b] = { ...r, gap: r.sharedCalls !== undefined && (r.reaches || r.launcherImported) ? rosterGap(r) : null, engineNames: engineNames(r), class: classOf(r) };
    process.stdout.write(JSON.stringify(out, null, 1) + "\n");
  } else if (mode === "tsv") {
    for (const [b, r] of c.byBundle) if (r.sharedCalls !== undefined) process.stdout.write([b, r.reaches ? "1" : "0", (r.reaches || r.launcherImported ? rosterGap(r) : null) || "-", engineNames(r).join(" and ") || "-", classOf(r)].join("\t") + "\n");
  } else {
    for (const l of c.legs) process.stdout.write(l + "\n");
  }
  for (const r of c.refusals) process.stderr.write("browser-legs-census: REFUSED " + r + "\n");
  if (c.refusals.length) { process.stderr.write("browser-legs-census: " + c.refusals.length + " refusal(s) above, each with file and line: the census judges no tree it cannot classify\n"); process.exit(2); }
}
