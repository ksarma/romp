// The browser-legs census: which test modules reach a browser, read from the TypeScript compiler's tree of each module, not
// from its spelling. One module, two readers: ui/webview/ci-browser-legs-census.test.ts (the vscode-extension job's test leg,
// which holds the roster plus the exclusions to this census and runs the planted forms) and scripts/ci-browser-legs.sh (the
// step's pre-run check, in the same job after its npm ci). The compiler is loaded from vscode-extension/node_modules and
// nowhere else, so CI's Shell job, which installs nothing, never runs this: its tools/ci-browser-legs.test.mjs holds the
// parse-free checks (file shape, duplicates, both files, reasons, the ci.yml pins) and says so in its messages. Without the
// compiler this module exits 1 naming that job and judges nothing.
//
// For every test module esbuild's test build bundles (a .test.ts directly in vscode-extension/src, ui or ui/webview: LEG_DIRS,
// the list's one home, which ui/webview/ci-browser-legs-census.test.ts holds equal to the directories esbuild.js testBuild
// compiles by building that config's entry points with a metafile and comparing, in both directions, with what census() read)
// it derives:
//   launcher:  the module imports ui/webview/real-viewer-leg.ts by RESOLVED path (relative to the module, .js read as .ts, the
//              suffix added when absent) under any binding form (named, aliased, namespace, default, import-equals, require(),
//              await import(), a createRequire-bound loader or the launcher's own exported requireCjs, by its named import, as a
//              member of a whole-module or default launcher binding or of the launcher loaded where it stands, or destructured
//              from a load of the launcher, declared or assigned,
//              destructured or whole) and calls that module's inBrowser THROUGH the binding (an identifier bound to the
//              export, or a literal inBrowser member of a namespace or default binding, or of the loader call's own result,
//              `require("./real-viewer-leg").inBrowser(...)`; through parentheses, !, as, .call/.apply; .bind makes no call,
//              so a bound reference is a value use, refused). The call arm and the value-use refusal read ONE record of the
//              identifier the call resolved through, so the two agree by construction. A type-only import binds nothing and is
//              recorded (typeOnly). The import without a call is recorded (launcherImported) and is not a leg. An ENGINE
//              passed to inBrowser as its third argument (the launcher's engine parameter; .call passes it fourth, .apply in
//              its array literal) is read into the engines the leg reaches: a literal, or a name FOLDED through the closed
//              forms under `playwright` below; an argument outside them, one naming no engine, or a spread element at or before
//              the engine position (the list the walker cannot read may carry an engine), is REFUSED with the line,
//              never read as no engine. A call with no third argument passes nothing and the record says nothing of it.
//              A name is read at its USE SITE by lexical scope: a use reaches the innermost enclosing declaration of that name,
//              so a destructured parameter, a catch variable or a local const of an inner scope that reuses the name is not
//              the import or the loader-bound variable, and a use in the scope that binds them is. A `var` is declared at the
//              nearest enclosing function or the module, not at the block, for head or catch clause that spells it (JavaScript
//              hoists it there), so a use outside that block reaches it.
//   loaded:    every module of the tree the test loads by a relative specifier (an import, an export from, import =, require(),
//              await import(), a loader bound by createRequire or a createRequire(...) call applied directly; a specifier that
//              names no file beside the module resolves
//              against the repo root and vscode-extension/, the bases loaders in this tree are anchored to, under the root alone:
//              a candidate outside it is never looked up, so a sibling directory beside the checkout is neither read nor an
//              ambiguity) is read by this same
//              walker, transitively, for what it BINDS OR CALLS: a module that binds the launcher's inBrowser (imports it,
//              imports the launcher whole, or re-exports it) or calls it (on a binding, or on a load where it stands) while the
//              test itself never calls inBrowser, names a playwright package, holds a driver string, or holds a form the walker
//              refuses, REFUSES the test at its import line with the chain. The
//              walker follows nothing THROUGH such a module (it does not read what the test calls on it), so the verdict is a
//              refusal with the remedy, never a silent non-leg. A file under node_modules is a package and binds nothing of
//              the tree; a json or css file is not a script.
//   playwright: the module names a playwright package (playwright, playwright-core, @playwright/test, or a subpath) by any
//              specifier form, either quote, in any position (an import, a loader call bound to a name, or a loader call whose
//              result is used where it stands: `require("playwright").chromium.launch()`, `(await import("playwright"))`,
//              `import("playwright").then(...)`), other than a type-only import or export (`import type`, `export type ... from`,
//              or named bindings every one inline type-only, `import { type Page }`: erased at build time, it binds nothing and
//              is carried by typeOnly, not a leg; a default or namespace binding beside an inline type is a value binding and
//              stays a load; an empty clause, `import {} from`, and a value import whose bindings are used in type positions
//              only are also erased by the bundler and still read as loads here, on the safe side); the engines it reaches from
//              a playwright-derived expression (chromium, firefox,
//              webkit: a property, a bracketed literal, a destructured binding, a named import, or a computed name FOLDED by
//              lexical scope through four closed forms: a const bound to a literal (a let or var too, when no statement of the
//              module writes to it: an assignment with the name as its target or inside a destructuring target, a for-of or
//              for-in head over it, assigning it or redeclaring it with var, ++ or --, or a second var declaration of it with
//              an initializer), a for-of over an array
//              literal, a parameter
//              typed as a union of string literals, a string-typed parameter whose every direct call site in the module passes a
//              literal; and two the launcher's own exports supply, read from its source by resolved path: a for-of over a name
//              imported from the launcher whose export is a const array literal of literals, and a parameter typed by a type
//              alias the launcher exports as a union of string literals); a launch of its own (launch, launchPersistentContext, launchServer, connect, connectOverCDP on a
//              playwright-derived expression, by property, bracket, destructuring or .call/.apply). Derivation stops at a call
//              that is not a loader: a browser returned by launch() or a wrapper's return value is not the package.
//   skipTodo:  every .skip( and .todo( call and every { skip: } or { todo: } option property, with its line, read from the tree,
//              so one held in a comment or a string is not one.
//   swallow:   a shared inBrowser call inside a try statement that has a catch clause, with its line: REPORTED, not refused
//              (such a leg is admitted to the roster; the count over the tree is printed by the census test).
//   embedded:  a string or template literal whose TEXT loads a playwright package (a child-process driver's source): counted
//              as reaching a browser, on the safe side, and never rosterable (the switch never reaches a child process). A
//              template with substitutions and a `+` concatenation are FOLDED before the text is read (a substitution that is
//              an identifier bound to one const literal takes its value; any other piece a placeholder), so a driver assembled
//              from pieces is read; a piece the fold cannot take (a value from the environment) is the third residual below.
//   REFUSALS:  a form the walker cannot classify refuses with file and line, never reports it absent: an import or loader
//              specifier that is not a string literal and folds through no closed form; a computed member with a name it
//              cannot fold on a playwright or launcher binding or load (`require("playwright")[k]` where k folds through no
//              closed form, bound or where it stands); the inBrowser binding used as a value, not called (an
//              initializer `const f = inBrowser` and a default value `{ x = inBrowser }` included; the exempt uses are the
//              NAME position of a declaration or import specifier and an assignment's target); the launcher's whole-module or
//              default binding handed on as a value (aliased, destructured, passed as an argument, called as a function or
//              constructed with new, which the launcher's module is not, read for inBrowser
//              without a call, `.bind` included, handed to a promise callback through .then, .catch or .finally, read for a
//              default member, awaited into a name, or read as an operand of a conditional, logical or other binary expression
//              on either side, `leg ?? null`, `null ?? leg`, `leg !== null`, where an assignment's target is the one exempt
//              operand position; reading another member off it is not a hand-on, and the refusal names
//              the position the line holds); the launcher loaded where it stands and handed on through .then, .catch,
//              .finally or .default; the launcher's requireCjs loader handed on as a value, not called (the named import
//              aliased to a name, or the member read off a whole-module or default binding or off the load where it stands
//              without a call: a load made through the alias elsewhere is unread); a playwright load or binding, or a load of
//              the launcher, read through a conditional or logical expression (`cond ? require("playwright") : null`, `?? null`,
//              `|| null`, `ok && require(...)`, as a binding's initializer, an assignment's right side or a member chain's root:
//              the walker does not follow which branch the value takes, so the engines and launches read through it, or where
//              inBrowser is called from, are unread); a local declaration
//              shadowing a launcher or playwright binding; a parse diagnostic; a loaded module of the tree as the `loaded`
//              clause states, or a relative specifier that names no file, or two; and THE INVARIANT's refusal, below. The CLI
//              exits 2 on any refusal.
// THE INVARIANT (the parse's own state against its record; run at the end of every classify, so census() holds it over every
// module it reads, test modules and the modules they load alike, whatever the class): the census may not resolve a tracked
// specifier or a launcher binding and return a record that carries nothing of it. Three clauses. (1) A playwright package the
// parse resolved (an import, an export from, import =, a loader call in ANY position) is in `playwright`, or, for a type-only
// import or export, in typeOnly. (2) The launcher the
// parse resolved is carried as an import (launcherImported), a type-only import (typeOnly), or a FOLLOWED load: a loader call
// bound by a binding's initializer or an assignment's right side, standing as a statement of its own, or the object of a
// member the walker read (`require(launcher).inBrowser(...)` counted as a shared call, another member read as an import,
// where then, catch, finally and default are not another member: they hand the load on, and the call arm refuses the
// promise members by name); a load in any other position (returned from a wrapper, passed as an argument, held in a class
// field, an object property or an array, read for inBrowser without a call, read for a default member) is refused naming
// the line and the position. (3) Every reference to a launcher binding that can carry inBrowser onward (the inBrowser
// binding, the whole module, its default) is one the walker READ: a call it counted, the name position of a declaration, a
// property name, a type position, the object of a member other than inBrowser, then, catch, finally or default, or a
// computed member it refused by name; a reference in any other position is refused as a value use by the
// walker, and one the walker classified as neither is refused by the invariant itself. Each refusal names the line and what
// was resolved. The invariant compares two states of the parse (what it resolved, what it recorded), so no string trips it
// and no module need cooperate: a module that names playwright or the launcher in a string, a test title, a regex or a file
// read resolves nothing and is class none without a refusal; a resolution the parse never makes (the residuals below) is
// outside it. The bound of that comparison, stated: the invariant compares the loads the parse RESOLVED against what the record
// carries, so it cannot see a load that never resolves (a callee the walker does not know as a loader), and a playwright load it
// resolves is recorded in the same call, so clause 1 holds by construction whatever the walker then fails to read through the
// value (a conditional or logical root, a computed member on the unbound load) or in the call's other arguments (a spread before
// the engine). Those four forms are closed, each with a refusal by name, where the walker meets them instead: in loaderCall (the
// launcher's requireCjs reached as a member callee), in pwChain, which bindLoaded and the call walk read every chain through (the
// conditional or logical root, the computed member on a load), and in readEngineArg (the spread); their plants are the p89 to p120
// rows of the census test. Its plants under tests/fixtures/browser-legs-plants record the outcome of every road it closes, and the census
// test (ui/webview/ci-browser-legs-census.test.ts) runs one mutation of the walker per clause over them and holds the
// invariant to refusing what the mutation silenced.
// THE CENSUS RULE: a module is a browser leg when it calls the shared launcher through its binding, names a playwright
// package, or holds a driver string that does. THE ROSTER GATE (rosterGap, null when the leg passes): a shared call, no
// playwright package of its own, no launch of its own, no driver string, no skip or todo; the engines it names are a separate
// verdict (engineNames: the gating job installs Chromium only). A leg's class (classOf): shared, own, both, embedded.
// Three residuals, stated: the fold of a string-typed parameter reads the module's own call sites only (no module imports a
// .test.ts, so a caller from another module does not arise); derivation stops at a non-loader call, so a launch made on a
// wrapper function's return value is not a launch to the walker; and the census reads a browser only through the playwright
// packages it names (PW_PACKAGES, and a subpath) and the shared launcher, so a module that reaches one without spelling either
// (another driver package such as puppeteer, a browser binary it spawns, a driver source whose package name arrives at run
// time, `${process.env.PKG}`) is unread by the walker: class none, no refusal; the owner names the package in the source or
// adds it to PW_PACKAGES. None is a spelling list: each is a rule with a stated boundary, planted with its outcome recorded
// (tests/fixtures/browser-legs-plants), and the census test prints the counts the tree gives them (and how many modules of
// the tree the test modules load it read).
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
// members that hand a launcher module (or its load) on rather than reading an export of it: a promise callback receives the
// module where the walker does not follow, and a default member is not one of the launcher's exports (it has none)
const HANDOFF = new Set(["then", "catch", "finally", "default"]);

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
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, /\.[cm]?js$/.test(file) ? ts.ScriptKind.JS : ts.ScriptKind.TS);
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

  // bindings: the DECLARATION that binds a tracked module -> { name, module: "launcher"|"playwright"|..., member: null (whole
  // module) | "inBrowser" | "chromium" | ... }. The key is an import's specifier, default clause or namespace node, the variable
  // declaration or binding element a loader call initializes, or the declaration an assignment's target resolves to by scope;
  // a name no declaration binds keys as the string "global:<name>". A use of a name is resolved to its declaration by lexical
  // scope (declOfUse) before it is read here, so a same-named binding of an inner scope (a destructured parameter, a local
  // const, a catch variable) is not the tracked one, and a use in the scope the import or loader binds is.
  const bindings = new Map();
  const loaders = new Set(["require"]); // identifiers that load a module when called with a string: require, createRequire results
  const pwDerived = new Map();          // the same keys -> { name, chain } for expressions derived from playwright
  const trackedNames = new Set();       // every name an entry of bindings or pwDerived carries: a use of any other name reaches no entry, so it is not resolved
  const track = (map, key, value) => { map.set(key, value); trackedNames.add(value.name); };
  const keyOf = (id) => declOfUse(id) || ("global:" + id.text);
  const bindingAt = (id) => (trackedNames.has(id.text) && bindings.get(keyOf(id))) || null;   // the tracked binding an identifier reaches, or null
  const derivedAt = (id) => (trackedNames.has(id.text) && pwDerived.get(keyOf(id))) || null;
  const bindingsNamed = (name) => [...bindings].filter(([, b]) => b.name === name);
  const engines = new Set(), launches = [], skipTodo = [], swallow = [];
  let sharedCalls = 0;
  const playwright = new Set();
  const launcherImported = [];
  const typeOnly = [];                 // { line, spec }: a type-only import or export of the launcher or a playwright package: resolved, binds nothing, recorded so the record carries it
  const localImports = [];             // { line, spec, text }: every module of the tree this module loads by a relative specifier (census() reads them)
  let launcherReexport = false;        // export { inBrowser } from / export * from the launcher: the module hands inBrowser on
  const noteLocal = (n, r) => { if (r && r.kind === "local") localImports.push({ line: lineOf(n), spec: r.spec, folded: r.abs === undefined, text: n.getText(sf).split("\n")[0].slice(0, 120) }); };

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
  /** The scopes a name is looked up through, innermost first: a function (its parameters and its block body), a block, a
   *  for/for-of/for-in head, a catch clause, the source file. */
  const isScope = (n) => ts.isFunctionLike(n) || ts.isBlock(n) || ts.isForOfStatement(n) || ts.isForInStatement(n) || ts.isForStatement(n) || ts.isCatchClause(n) || ts.isSourceFile(n);
  /** The declarations a scope holds ITSELF (an inner scope's are not its own): name -> the first node in source order that
   *  declares it, a variable declaration, a parameter, a binding element (a destructured declaration or parameter, an array
   *  pattern's element included), a function or class declaration, a catch variable; at the source file an import's binding too
   *  (a named specifier, the default clause, a namespace import, an import =). A `var` (a declaration list with neither the
   *  let nor the const flag, a destructured var's binding elements included) is hoisted: it is held by the nearest enclosing
   *  function or the source file, whatever block, for head or catch clause spells it, and never by that block. Read once per
   *  scope and kept for the life of this classify call: every lookup of a tracked name resolves through it. */
  const scopeDecls = new Map();
  const hoisted = (n) => { let d = n; while (d && (ts.isBindingElement(d) || ts.isObjectBindingPattern(d) || ts.isArrayBindingPattern(d))) d = d.parent; return !!(d && ts.isVariableDeclaration(d) && d.parent && ts.isVariableDeclarationList(d.parent) && !(d.parent.flags & (ts.NodeFlags.Let | ts.NodeFlags.Const))); };
  const declsOf = (scope) => {
    let m = scopeDecls.get(scope);
    if (m) return m;
    m = new Map();
    const holdsVars = ts.isFunctionLike(scope) || ts.isSourceFile(scope);
    const note = (n) => { if (!m.has(n.name.text)) m.set(n.name.text, n); };
    // `inner`: the walk has crossed into an inner block, for head or catch clause, whose own declarations are not this
    // scope's; a var found there still is (hoisted), when this scope is the kind that holds vars
    const look = (n, inner) => {
      if ((ts.isVariableDeclaration(n) || ts.isBindingElement(n)) && n.name && ts.isIdentifier(n.name)) { if (hoisted(n) ? holdsVars : !inner) note(n); }
      else if (!inner && (ts.isParameter(n) || ts.isFunctionDeclaration(n) || ts.isClassDeclaration(n)) && n.name && ts.isIdentifier(n.name)) note(n);
      else if (!inner && (ts.isImportSpecifier(n) || ts.isNamespaceImport(n) || ts.isImportEqualsDeclaration(n))) note(n);
      else if (!inner && ts.isImportClause(n) && n.name) note(n);
      if (n !== scope && isScope(n)) { if (ts.isFunctionLike(n) || !holdsVars) return; ts.forEachChild(n, (c) => look(c, true)); return; } // an inner function's declarations are never ours; an inner block's vars are, when we hold vars
      ts.forEachChild(n, (c) => look(c, inner));
    };
    if (ts.isFunctionLike(scope)) { for (const prm of scope.parameters) look(prm, false); if (scope.body && ts.isBlock(scope.body)) for (const st of scope.body.statements) look(st, false); }
    else if (ts.isForOfStatement(scope) || ts.isForInStatement(scope) || ts.isForStatement(scope)) { if (scope.initializer) look(scope.initializer, false); }
    else if (ts.isCatchClause(scope)) { if (scope.variableDeclaration) look(scope.variableDeclaration, false); }
    else if (ts.isBlock(scope) || ts.isSourceFile(scope)) for (const st of scope.statements) look(st, false);
    scopeDecls.set(scope, m);
    return m;
  };
  /** The node that declares `name` in `scope` itself, or null. Shared by foldIdentifier (a folded name) and by every lookup of a
   *  tracked binding (a playwright or launcher name at its use site). */
  const declOfName = (scope, name) => declsOf(scope).get(name) || null;
  /** The declaration an identifier reaches by lexical scope: from the identifier upward, the first enclosing scope that declares
   *  its name decides (an identifier in a declaration's own name position reaches that declaration). null: no enclosing scope
   *  declares the name (a global, or a name the module assigns without declaring). Kept per identifier node for this call. */
  const useDecl = new Map();
  const declOfUse = (id) => {
    if (useDecl.has(id)) return useDecl.get(id);
    let d = null;
    for (let p = id.parent; p && !d; p = p.parent) if (isScope(p)) d = declOfName(p, id.text);
    useDecl.set(id, d);
    return d;
  };
  const foldIdentifier = (id) => {
    const name = id.text;
    const decl = declOfUse(id);
    if (!decl) return null;
    if (ts.isVariableDeclaration(decl)) {
      // a let or var the module writes to elsewhere (assignedSomewhere: an assignment with the name as its target or inside a
      // destructuring target, a for-of or for-in head over it or redeclaring it with var, ++ or --, a second var declaration with
      // an initializer) is not bound to its initializer: null
      if (!(decl.parent && ts.isVariableDeclarationList(decl.parent) && (decl.parent.flags & ts.NodeFlags.Const)) && assignedSomewhere(name, decl)) return null;
      if (decl.initializer) { const v = literalName(unwrap(decl.initializer)); if (v !== null) return [v]; return null; }
      const p = decl.parent, fo = p && p.parent;
      if (fo && ts.isForOfStatement(fo) && fo.initializer === p) {
        const arr = unwrap(fo.expression);
        if (ts.isArrayLiteralExpression(arr)) { const vals = arr.elements.map((el) => literalName(unwrap(el))); if (vals.every((v) => v !== null)) return vals; }
        if (ts.isIdentifier(arr)) return launcherExportLiterals(arr, "const");   // for (const engine of ENGINES), ENGINES imported from the launcher
      }
      return null;
    }
    if (ts.isParameter(decl)) {
      if (decl.type && ts.isUnionTypeNode(decl.type)) { const vals = decl.type.types.map((t) => ts.isLiteralTypeNode(t) && ts.isStringLiteral(t.literal) ? t.literal.text : null); if (vals.every((v) => v !== null)) return vals; return null; }
      if (decl.type && ts.isLiteralTypeNode(decl.type) && ts.isStringLiteral(decl.type.literal)) return [decl.type.literal.text];
      if (decl.type && ts.isTypeReferenceNode(decl.type) && ts.isIdentifier(decl.type.typeName)) return launcherExportLiterals(decl.type.typeName, "type");   // (engine: Engine), Engine imported from the launcher
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
  /** The string literals the launcher's export named by `id` holds, when `id` is a name imported from the launcher (by scope) and
   *  the launcher's source, read once per classify by its resolved path, exports it as a const array literal of literals
   *  (`kind` "const": `export const ENGINES = ["chromium", ...]`, `as const` or typed) or as a type alias that is a union of
   *  string literal types (`kind` "type": `export type Engine = "chromium" | ...`). null otherwise (refuse). */
  let launcherExports = null;
  const launcherExportLiterals = (id, kind) => {
    const d = declOfUse(id);
    if (!d || !ts.isImportSpecifier(d)) return null;
    const imp = d.parent && d.parent.parent && d.parent.parent.parent;
    if (!imp || !ts.isImportDeclaration(imp)) return null;
    const spec = literalName(imp.moduleSpecifier);
    if (spec === null || resolveSpec(spec).kind !== "launcher") return null;
    if (launcherExports === null) {
      launcherExports = new Map();
      let text = null; try { text = fs.readFileSync(launcherAbs, "utf8"); } catch { text = null; }
      if (text !== null) {
        const lsf = ts.createSourceFile(launcherAbs, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
        const exported = (st) => (ts.canHaveModifiers(st) ? ts.getModifiers(st) || [] : []).some((m) => m.kind === ts.SyntaxKind.ExportKeyword);
        for (const st of lsf.statements) {
          if (ts.isVariableStatement(st) && exported(st)) for (const vd of st.declarationList.declarations) if (ts.isIdentifier(vd.name) && vd.initializer) launcherExports.set("const:" + vd.name.text, vd.initializer);
          if (ts.isTypeAliasDeclaration(st) && exported(st)) launcherExports.set("type:" + st.name.text, st.type);
        }
      }
    }
    const node = launcherExports.get(kind + ":" + (d.propertyName || d.name).text);
    if (!node) return null;
    if (kind === "const") { const arr = unwrap(node); if (!ts.isArrayLiteralExpression(arr)) return null; const vals = arr.elements.map((el) => literalName(unwrap(el))); return vals.every((v) => v !== null) ? vals : null; }
    if (!ts.isUnionTypeNode(node)) return ts.isLiteralTypeNode(node) && ts.isStringLiteral(node.literal) ? [node.literal.text] : null;
    const vals = node.types.map((t) => ts.isLiteralTypeNode(t) && ts.isStringLiteral(t.literal) ? t.literal.text : null);
    return vals.every((v) => v !== null) ? vals : null;
  };
  /** Does any statement in the module WRITE to the identifier `name`, so that a let or var is not bound to its initializer? A
   *  write is (a) the name in a BINDING position of an assignment's target: the target itself (=, or a compound assignment) or,
   *  under =, inside an array or object literal target at any depth (an element, a spread, a default's left side, a shorthand
   *  property, a property assignment's value, a spread assignment, through parentheses); (b) a for-of or for-in head whose
   *  initializer is not a declaration list and holds the name in such a position; (c) ++ or --; (d) a second var declaration of
   *  the name (the identifier, or one inside its binding pattern) that resolves, by scope, to the declaration the use reaches
   *  (`decl`, the first in source order, the one declsOf keeps) and either carries an initializer or is the declaration of a
   *  for-of or for-in head (`for (var name of xs)`, `for (var [name] of xs)`: the head writes it on every pass); a same-named let
   *  or const of an inner block or of a for head is its own declaration and no write to this one. A member access on the name
   *  (`o[name] = 1`, `name.x = y`) is a read of it, not a write. The predicate is the rule, not a list of spellings: the plants
   *  p31, p133 to p141 and p151 to p155 record its outcomes. */
  const isAssignmentOp = (e) => e.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && e.operatorToken.kind <= ts.SyntaxKind.LastAssignment;   // =, a compound assignment, ??=, ||=, &&=
  const assignedSomewhere = (name, decl) => {
    const bindsName = (t) => {
      t = unwrap(t);
      if (ts.isIdentifier(t)) return t.text === name;
      if (ts.isArrayLiteralExpression(t)) return t.elements.some(bindsName);
      if (ts.isObjectLiteralExpression(t)) return t.properties.some((q) => ts.isShorthandPropertyAssignment(q) ? q.name.text === name : ts.isPropertyAssignment(q) ? bindsName(q.initializer) : ts.isSpreadAssignment(q) ? bindsName(q.expression) : false);
      if (ts.isSpreadElement(t)) return bindsName(t.expression);
      if (ts.isBinaryExpression(t) && t.operatorToken.kind === ts.SyntaxKind.EqualsToken) return bindsName(t.left);   // a default inside a pattern: [name = "x"] = arr
      return false;   // a member access or any other target: no write to the name
    };
    // (d): a declaration whose name (an identifier, or one inside a binding pattern) is `name` and resolves by scope to `decl`
    // (a `var`: hoisted to decl's scope); a let or const in a for head or a block is a declaration of its own scope, resolves to
    // itself and is no write to `decl`
    const redeclares = (bn) => ts.isIdentifier(bn) ? bn.text === name && declOfUse(bn) === decl : (ts.isArrayBindingPattern(bn) || ts.isObjectBindingPattern(bn)) && bn.elements.some((el) => ts.isBindingElement(el) && redeclares(el.name));
    const forHead = (n) => !!(n.parent && ts.isVariableDeclarationList(n.parent) && n.parent.parent && (ts.isForOfStatement(n.parent.parent) || ts.isForInStatement(n.parent.parent)) && n.parent.parent.initializer === n.parent);
    let hit = false;
    const look = (n) => {
      if (hit) return;
      if (ts.isBinaryExpression(n) && isAssignmentOp(n) && bindsName(n.left)) { hit = true; return; }
      if ((ts.isForOfStatement(n) || ts.isForInStatement(n)) && !ts.isVariableDeclarationList(n.initializer) && bindsName(n.initializer)) { hit = true; return; }
      if ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken) && ts.isIdentifier(n.operand) && n.operand.text === name) { hit = true; return; }
      if (decl && ts.isVariableDeclaration(n) && n !== decl && (n.initializer || forHead(n)) && redeclares(n.name)) { hit = true; return; }
      ts.forEachChild(n, look);
    };
    look(sf);
    return hit;
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
  // the root of a member chain, unwrapped at EVERY step (a cast or a non-null assertion on the object, `(pw as any)[k]`, the
  // spelling strict TypeScript forces for a computed index on a typed namespace, hides the root otherwise)
  const rootOf = (e) => { e = unwrap(e); while (ts.isPropertyAccessExpression(e) || ts.isElementAccessExpression(e) || ts.isCallExpression(e) || ts.isNonNullExpression(e) || ts.isParenthesizedExpression(e)) e = unwrap(e.expression); return e; };
  const isCreateRequireCall = (x) => ts.isCallExpression(x) && ((ts.isIdentifier(unwrap(x.expression)) && unwrap(x.expression).text === "createRequire") || (ts.isPropertyAccessExpression(unwrap(x.expression)) && unwrap(x.expression).name.text === "createRequire"));
  // THE INVARIANT's state: every tracked specifier the parse resolved (a playwright package or the launcher), by the node that
  // resolved it, with what accounts for it: an import's line is accounted by launcherImported or typeOnly; a loader call by
  // `followed` (bound, standing as a statement, or the object of a member the walker read)
  const resolved = new Map();           // node -> { kind: "playwright"|"launcher", spec, line, how: "import"|"load" }
  const noteResolved = (n, kind, spec, how) => { if (["playwright", "launcher"].includes(kind) && !resolved.has(n)) resolved.set(n, { kind, spec, line: lineOf(n), how }); };
  const followed = new Set();           // loader call nodes the walker read
  /** Is `e` a loader call (require("x"), req("x"), import("x"), createRequire(...)("x"))? Returns the resolved spec or null;
   *  refuses a non-literal. A load of a playwright package is recorded HERE, wherever the call sits (bound or not), so an unbound
   *  `require("playwright").chromium.launch()` is a leg; a load of the launcher is recorded for the self-check. */
  /** The launcher's exported requireCjs reached as a MEMBER: of a whole-module or default launcher binding (`leg.requireCjs(...)`),
   *  or of the launcher loaded where it stands (`require(launcher).requireCjs(...)`, the load FOLLOWED and counted as an import):
   *  a loader callee, as the named import is (the header lists the launcher's own exported requireCjs among the loader forms). The
   *  local is `ld`, not `l`: the census test's mutation anchors read walk3's `const l = loaderCall(obj)` idiom once. */
  const isLauncherRequireCjs = (c) => {
    if (!(ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c))) return false;
    const names = memberNames(c);
    if (names === null || !names.includes("requireCjs")) return false;
    const obj = unwrap(c.expression);
    if (ts.isIdentifier(obj)) { const b = bindingAt(obj); return b !== null && b.module === "launcher" && (b.member === null || b.member === "default"); }
    if (ts.isCallExpression(obj)) { const ld = loaderCall(obj); if (ld && ld.kind === "launcher") { followed.add(obj); launcherImported.push(lineOf(c)); return true; } }
    return false;
  };
  const loaderCall = (e) => {
    e = unwrap(e);
    if (!ts.isCallExpression(e)) return null;
    const c = unwrap(e.expression);
    const isLoader = (ts.isIdentifier(c) && loaders.has(c.text)) || c.kind === ts.SyntaxKind.ImportKeyword || isCreateRequireCall(c) || isLauncherRequireCjs(c);
    if (!isLoader) return null;
    const arg = e.arguments[0];
    const spec = arg && literalName(unwrap(arg));
    const r = (spec !== null && spec !== undefined) ? resolveSpec(spec) : (arg && foldSpecifier(unwrap(arg), 0));
    if (!r) { refuse(e, "a loader whose specifier is not a string literal and folds through no closed form (refused, on the safe side)"); return { kind: "refused" }; }
    if (r.kind === "playwright") playwright.add(r.spec);
    noteResolved(e, r.kind, r.spec, "load");
    return r;
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
  /** The branches of a ConditionalExpression or of a ??, || or && BinaryExpression, unwrapped and flattened through nested ones;
   *  null for any other node. */
  const isLogical = (e) => ts.isBinaryExpression(e) && [ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.BarBarToken, ts.SyntaxKind.AmpersandAmpersandToken].includes(e.operatorToken.kind);
  const condBranches = (e) => {
    e = unwrap(e);
    if (!(ts.isConditionalExpression(e) || isLogical(e))) return null;
    const out = [];
    const add = (x) => { x = unwrap(x); const inner = condBranches(x); if (inner) out.push(...inner); else out.push(x); };
    if (ts.isConditionalExpression(e)) { add(e.whenTrue); add(e.whenFalse); } else { add(e.left); add(e.right); }
    return out;
  };
  /** A chain whose ROOT is a conditional or logical expression with a tracked branch (a playwright load, a playwright binding or
   *  derived name, a chain on one, a load of the launcher): the walker does not follow which branch the value takes, so it REFUSES
   *  by name, one site for every shape (a binding's initializer, an assignment's right side, a bound or unbound chain's root). A
   *  launcher load in a branch is marked followed by the refusal, so THE INVARIANT does not refuse it a second time; a launcher
   *  BINDING in a branch is left to the value-use arm, whose handedHow names the form. Returns true when it refused. */
  const refuseCondRoot = (e) => {
    const br = condBranches(e);
    if (!br) return false;
    let pw = false, launcher = null;
    for (const b of br) {
      const ld = ts.isCallExpression(b) ? loaderCall(b) : null;
      if (ld && ld.kind === "playwright") pw = true;
      else if (ld && ld.kind === "launcher") launcher = b;
      else if (ts.isIdentifier(b) && (derivedAt(b) !== null || (bindingAt(b) !== null && bindingAt(b).module === "playwright"))) pw = true;
      else if (!ld && !ts.isIdentifier(b)) { const c = pwChain(b); if (c && !c.refused) pw = true; }
    }
    if (pw) refuse(e, "a playwright load or binding read through a conditional or logical expression the walker does not follow (the engines and launches read through it are unread): bind the load in a statement of its own");
    if (launcher) { followed.add(launcher); refuse(e, "the shared launcher loaded inside a conditional or logical expression the walker does not follow, so where inBrowser is called from is unread: bind the load in a statement of its own"); }
    return pw || launcher !== null;
  };
  /** Is `e` derived from playwright? Returns the chain of member names from the package root, or null; { refused: true } when the
   *  chain holds a form the walker refused by name (a conditional or logical root with a tracked branch, a computed member it
   *  cannot fold on a tracked binding or a playwright load). */
  const pwChain = (e) => {
    e = unwrap(e);
    const chain = [];
    for (;;) {
      if (condBranches(e)) { if (refuseCondRoot(e)) return { refused: true }; return null; }
      if (ts.isPropertyAccessExpression(e) || ts.isElementAccessExpression(e)) {
        const names = memberNames(e);
        if (names === null) { const r = rootOf(e); if (isTrackedRoot(r) || (loadRoot(e) || {}).kind === "playwright") { refuse(e, "a computed member with a name the walker cannot fold on a playwright or launcher binding or load"); refusedRoots.add(r); return { refused: true }; } return null; }
        chain.unshift(names); e = unwrap(e.expression); continue;
      }
      if (ts.isCallExpression(e)) { const l = loaderCall(e); if (l && l.kind === "playwright") return chain; if (l && l.kind === "refused") return { refused: true }; return null; }
      if (ts.isIdentifier(e)) {
        const b = bindingAt(e);
        if (b && b.module === "playwright") { if (b.member) chain.unshift([b.member]); return chain; }
        const d = derivedAt(e);
        if (d) { chain.unshift(...d.chain); return chain; }
        return null;
      }
      return null;
    }
  };
  const refusedRoots = new Set();       // identifier nodes under a computed member the walker refused by name (the reference was read)
  /** The loader call a member chain stands on (`require("playwright")[k]`: through property and element access to a call, never
   *  through a non-loader call, the stated residual), resolved by loaderCall; null when the chain stands on no call. The playwright
   *  kind alone reaches the computed-member refusal: a computed member on the launcher loaded where it stands leaves the load
   *  unfollowed, and THE INVARIANT's clause 2 refuses it. */
  const loadRoot = (x) => { x = unwrap(x); while (ts.isPropertyAccessExpression(x) || ts.isElementAccessExpression(x)) x = unwrap(x.expression); return ts.isCallExpression(x) ? loaderCall(x) : null; };
  const isTrackedRoot = (r) => { if (!ts.isIdentifier(r)) return false; const b = bindingAt(r); return (b !== null && ["playwright", "launcher"].includes(b.module)) || derivedAt(r) !== null; };
  const noteChain = (chain) => { for (const names of chain) for (const n of names) if (ENGINES.has(n)) engines.add(n); };

  // pass 1: imports, loaders, declarations (source order; a second pass below picks up derived bindings declared before use)
  /** The kind of a bind target that is neither an identifier nor an object binding pattern, for the refusal that names it: the
   *  sentence says what the line holds (a property assignment `o.pw = pw`, an element assignment `o[0] = pw`, an array
   *  destructuring `const [x] = pw`, an object destructuring by assignment `({ x } = pw)`), and names the node's kind for any other. */
  const targetKind = (t) => ts.isArrayBindingPattern(t) || ts.isArrayLiteralExpression(t) ? "an array destructuring" : ts.isPropertyAccessExpression(t) ? "a property assignment" : ts.isElementAccessExpression(t) ? "an element assignment" : ts.isObjectLiteralExpression(t) ? "an object destructuring by assignment" : "a bind target of a kind the walker does not read (" + ts.SyntaxKind[t.kind] + ")";
  const bindName = (nm, module, member) => {
    if (ts.isIdentifier(nm)) track(bindings, keyOf(nm), { name: nm.text, module, member });
    else if (ts.isObjectBindingPattern(nm)) for (const el of nm.elements) { if (el.dotDotDotToken) { track(bindings, el, { name: el.name.text, module, member }); continue; } const prop = el.propertyName ? (ts.isIdentifier(el.propertyName) ? el.propertyName.text : literalName(el.propertyName)) : (ts.isIdentifier(el.name) ? el.name.text : null); if (prop === null) { refuse(el, "a destructured member with a name the walker cannot read"); continue; } if (ts.isIdentifier(el.name)) track(bindings, el, { name: el.name.text, module, member: member ? member + "." + prop : prop }); else refuse(el, "a nested destructuring the walker does not follow"); }
    else refuse(nm, targetKind(nm) + " of a loaded module the walker does not follow");
  };
  const walk1 = (n) => {
    if (ts.isImportDeclaration(n)) {
      const spec = literalName(n.moduleSpecifier);
      if (spec === null) refuse(n, "an import whose specifier is not a string literal (refused, on the safe side)");
      else {
        const r = resolveSpec(spec);
        noteResolved(n, r.kind, spec, "import");
        const c = n.importClause;
        // a clause that binds nothing at run time, erased by the bundler: `import type ...`, or named bindings every one inline
        // type-only (`import { type Page }`); a default or namespace binding beside an inline type is a value binding, so
        // `import pw, { type Page }` stays a load. One predicate, read by the playwright add, the typeOnly record and
        // launcherImported, so the three agree (a bare `import "x"` has no clause and is a load)
        const clauseTypeOnly = !!c && (!!c.isTypeOnly || (!c.name && !!c.namedBindings && ts.isNamedImports(c.namedBindings) && c.namedBindings.elements.length > 0 && c.namedBindings.elements.every((el) => el.isTypeOnly)));
        if (r.kind === "playwright" && !clauseTypeOnly) playwright.add(spec);
        if (r.kind === "launcher" && !clauseTypeOnly) launcherImported.push(lineOf(n));
        if (clauseTypeOnly && ["launcher", "playwright"].includes(r.kind)) typeOnly.push({ line: lineOf(n), spec });
        if (!clauseTypeOnly) noteLocal(n, r);
        if (c && !clauseTypeOnly) {
          if (c.name) track(bindings, c, { name: c.name.text, module: r.kind, member: "default" });
          if (c.namedBindings) {
            if (ts.isNamespaceImport(c.namedBindings)) track(bindings, c.namedBindings, { name: c.namedBindings.name.text, module: r.kind, member: null });
            else for (const el of c.namedBindings.elements) if (!el.isTypeOnly) track(bindings, el, { name: el.name.text, module: r.kind, member: (el.propertyName || el.name).text });
          }
        }
      }
    } else if (ts.isImportEqualsDeclaration(n)) {
      if (ts.isExternalModuleReference(n.moduleReference)) { const spec = literalName(n.moduleReference.expression); if (spec === null) refuse(n, "an import = require whose specifier is not a string literal"); else { const r = resolveSpec(spec); noteResolved(n, r.kind, spec, "import"); if (r.kind === "playwright") playwright.add(spec); if (r.kind === "launcher") launcherImported.push(lineOf(n)); noteLocal(n, r); track(bindings, n, { name: n.name.text, module: r.kind, member: null }); } }
    } else if (ts.isExportDeclaration(n) && n.moduleSpecifier) {
      const spec = literalName(n.moduleSpecifier);
      if (spec === null) refuse(n, "an export from whose specifier is not a string literal");
      else {
        const r = resolveSpec(spec);
        noteResolved(n, r.kind, spec, "import");
        const ec = n.exportClause;
        // `export type { X } from`, or named exports every one inline type-only: erased by the bundler, binds nothing, recorded
        const exportTypeOnly = !!n.isTypeOnly || (!!ec && ts.isNamedExports(ec) && ec.elements.length > 0 && ec.elements.every((el) => el.isTypeOnly));
        if (r.kind === "playwright" && !exportTypeOnly) playwright.add(spec);
        if (exportTypeOnly && ["launcher", "playwright"].includes(r.kind)) typeOnly.push({ line: lineOf(n), spec });
        if (!exportTypeOnly) {
          noteLocal(n, r);
          // export * from the launcher, export * as ns from it, or a named export of inBrowser: the module hands inBrowser on
          if (r.kind === "launcher") { launcherImported.push(lineOf(n)); if (!ec || ts.isNamespaceExport(ec) || ec.elements.some((el) => !el.isTypeOnly && (el.propertyName || el.name).text === "inBrowser")) launcherReexport = true; }
        }
      }
    } else if (ts.isVariableDeclaration(n) && n.initializer) {
      const init = unwrap(n.initializer);
      // a createRequire(...) result is a loader
      if (ts.isCallExpression(init) && ((ts.isIdentifier(unwrap(init.expression)) && unwrap(init.expression).text === "createRequire") || (ts.isPropertyAccessExpression(unwrap(init.expression)) && unwrap(init.expression).name.text === "createRequire")) && ts.isIdentifier(n.name)) loaders.add(n.name.text);
    }
    ts.forEachChild(n, walk1);
  };
  walk1(sf);

  // pass 2: loader-bound variables and assignments (declaration or assignment), playwright-derived bindings; to a fixpoint
  const bindLoaded = (target, valueExpr, holder) => {
    const v = unwrap(valueExpr);
    // a loader call, possibly through a member chain: require("x").y
    let e = v, members = [];
    while (ts.isPropertyAccessExpression(e) || ts.isElementAccessExpression(e)) { const names = memberNames(e); if (names === null) { members = null; break; } members.unshift(names); e = unwrap(e.expression); }
    const l = loaderCall(e);
    if (l) followed.add(e);   // bound, or refused below: the walker read this load
    if (l && l.kind !== "refused") {
      // a package or local load binds nothing the walker reads (every arm that reads a binding's module filters on launcher or
      // playwright, and a local module is read transitively by census() through localImports, not through its binding), so its
      // target is not read here: an array or nested destructuring of `require("node:os")` is no form to refuse
      if (!["playwright", "launcher"].includes(l.kind)) return false;
      if (l.kind === "launcher") launcherImported.push(lineOf(holder));
      // members is never null here: a computed member the walker cannot fold breaks the peel with e at the access node, so l is
      // null and the value falls through to pwChain below, whose computed-member arm refuses it by name when the chain stands on
      // a tracked binding or a playwright load
      const member = members.length ? members.map((m) => m.join("|")).join(".") : null;
      if (l.kind === "playwright") { for (const m of members) for (const x of m) if (ENGINES.has(x)) engines.add(x); }
      if (ts.isIdentifier(target)) { const k = keyOf(target); if (!bindings.has(k)) { track(bindings, k, { name: target.text, module: l.kind, member }); return true; } return false; }
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
      if (ts.isIdentifier(target)) { const k = keyOf(target); if (!pwDerived.has(k) && !bindings.has(k)) { track(pwDerived, k, { name: target.text, chain }); changed = true; } }
      else if (ts.isObjectBindingPattern(target)) for (const el of target.elements) { const prop = el.propertyName ? (ts.isIdentifier(el.propertyName) ? el.propertyName.text : literalName(el.propertyName)) : (ts.isIdentifier(el.name) ? el.name.text : null); if (prop === null || !ts.isIdentifier(el.name)) { refuse(el, "a destructuring of a playwright expression the walker cannot read"); continue; } if (!pwDerived.has(el)) { track(pwDerived, el, { name: el.name.text, chain: [...chain, [prop]] }); changed = true; } if (LAUNCHES.has(prop)) launches.push({ line: lineOf(el), how: "destructured " + prop }); }
      else refuse(target, targetKind(target) + " of a playwright expression the walker does not follow");
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
    // the launcher's own requireCjs export, imported by a leg or destructured from a load of the launcher (a binding this pass
    // made), is a loader too: it joins here, inside the fixpoint, so the next pass binds what is loaded through it
    for (const [, b] of bindings) if (b.module === "launcher" && b.member === "requireCjs" && !loaders.has(b.name)) { loaders.add(b.name); changed = true; }
    if (pass === 7 && changed) refuse(sf, "the binding walk did not settle in 8 passes");
  }
  // the engines every playwright binding names by its member path (const { firefox } = require("playwright"))
  for (const [, b] of bindings) if (b.module === "playwright" && b.member) for (const x of b.member.split(".")) for (const y of x.split("|")) if (ENGINES.has(y)) engines.add(y);

  // shadowing: a local declaration (variable, function, class, parameter) with a tracked binding's name refuses. A use of the
  // name reaches the local (resolution is by scope), so the refusal is not for ambiguity: it is so that an import a shadow leaves
  // uncalled, or whose launches a shadow hides, does not read as an ordinary non-leg without notice.
  const walkShadow = (n) => {
    if ((ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isFunctionDeclaration(n) || ts.isClassDeclaration(n)) && n.name && ts.isIdentifier(n.name)) {
      const b = bindingsNamed(n.name.text).some(([k, x]) => k !== n && ((x.module === "launcher" && (x.member === "inBrowser" || x.member === null)) || x.module === "playwright"));
      if (b) { const init = ts.isVariableDeclaration(n) && n.initializer ? unwrap(n.initializer) : null; const viaLoader = init && (loaderCall(init) || pwChain(init)); const isBinderItself = ts.isVariableDeclaration(n) && (viaLoader || (init === null && n.initializer === undefined)); if (!isBinderItself && !(ts.isVariableDeclaration(n) && n.initializer && (literalName(init) === null && (init.kind === ts.SyntaxKind.NullKeyword || init.kind === ts.SyntaxKind.UndefinedKeyword)))) refuse(n, "a local declaration shadows an import binding of the launcher or of playwright (a use inside the local's scope reaches the local, not the import; the shadow is refused so an import it leaves uncalled, or whose launches it hides, is not read as an ordinary non-leg without notice: rename the local)"); }
    }
    ts.forEachChild(n, walkShadow);
  };
  walkShadow(sf);

  // pass 3: calls and references
  const inTryWithCatch = (n) => { for (let p = n.parent; p; p = p.parent) { if (ts.isTryStatement(p) && p.catchClause && p.tryBlock.pos <= n.pos && n.end <= p.tryBlock.end) return true; if (ts.isFunctionLike(p)) return false; } return false; };
  // the identifier nodes the call arm resolved a shared call through (the callee, or the object of the inBrowser member it
  // called): the value-use arm below reads this record, so a wrapped call (parentheses, !, as, .call/.apply) is never also a
  // value use, by construction; `refRead` is every reference to a launch-carrying launcher binding the walker classified as
  // read, `refRefused` every one it refused: THE INVARIANT holds every such reference to one of the two
  const calledThrough = new Set();
  const refRead = new Set(), refRefused = new Set();
  /** The engine a shared call passes (inBrowser's third argument; fourth through .call; the array literal's third through .apply),
   *  folded into `engines`; nothing when the call passes none; a refusal when the argument folds through no closed form, names no
   *  engine, or sits in an .apply list the walker cannot read. */
  const readEngineArg = (call, via) => {
    // a spread element at or before the engine position: the fixed-index read below would pass the call as no engine while the
    // spread may carry one, so the list is refused by name for each call form
    const SPREAD = "a spread element at or before the engine position, an argument list the walker cannot read (an engine may be passed in it): spell each argument out";
    let arg;
    if (!via) { if (call.arguments.slice(0, 3).some((a) => ts.isSpreadElement(a))) { refuse(call, "the shared launcher called with " + SPREAD); return; } arg = call.arguments[2]; }
    else if (via === "call") { if (call.arguments.slice(0, 4).some((a) => ts.isSpreadElement(a))) { refuse(call, "the shared launcher called through .call with " + SPREAD); return; } arg = call.arguments[3]; }
    else { const list = call.arguments[1] && unwrap(call.arguments[1]); if (list && ts.isArrayLiteralExpression(list)) { if (list.elements.slice(0, 3).some((a) => ts.isSpreadElement(a))) { refuse(call, "the shared launcher applied to " + SPREAD); return; } arg = list.elements[2]; } else if (list) { refuse(call, "the shared launcher applied to an argument list the walker cannot read (an engine may be passed in it)"); return; } }
    if (!arg) return;
    const a = unwrap(arg);
    const lit = literalName(a);
    const vals = lit !== null ? [lit] : ts.isIdentifier(a) ? foldIdentifier(a) : null;
    if (!vals) { refuse(arg, "an engine argument to the shared launcher the walker cannot fold (the closed forms: a literal; a const bound to one; a for-of over an array literal or over the launcher's exported const array; a parameter typed as a literal union or as the launcher's exported alias; a string parameter whose call sites pass literals), so the engine the leg reaches is unread: spell it through one of them"); return; }
    for (const v of vals) { if (ENGINES.has(v)) engines.add(v); else refuse(arg, "an engine argument to the shared launcher that names no engine (" + v + "; the engines are chromium, firefox and webkit)"); }
  };
  const carriesInBrowser = (b) => b !== null && b.module === "launcher" && (b.member === "inBrowser" || b.member === null || b.member === "default");
  /** The position a launcher binding is handed on in, for the refusal's parenthetical: read from the reference's parent so the
   *  sentence says what the line holds (a wording the round-2 review ruled on for another refusal: a message names what it
   *  refuses, not a list of forms the line may lack). `q` is the reference up through parentheses, ! and as; `pp` its parent. */
  const handedHow = (q, pp) => {
    if (!pp) return "in a position the walker does not read";
    if (ts.isPropertyAccessExpression(pp) || ts.isElementAccessExpression(pp)) {
      const names = memberNames(pp) || [];
      if (names.includes("default")) return "read for a default member, which is not an export of the launcher";
      if (names.some((x) => x === "then" || x === "catch" || x === "finally")) return "handed to a promise callback through ." + names.find((x) => x === "then" || x === "catch" || x === "finally") + ", where inBrowser is called from is unread: await the load where it is made and call inBrowser on the result";
      if (names.includes("requireCjs")) return "read for requireCjs without a call, so a load made through it elsewhere is unread: call requireCjs where the load is made";
      return "read for inBrowser without a call" + (pp.parent && ts.isPropertyAccessExpression(pp.parent) && pp.parent.name.text === "bind" ? " (.bind makes no call)" : "");
    }
    if (ts.isAwaitExpression(pp)) return "awaited into a name the walker does not bind: await the import where it is loaded and call inBrowser on the result";
    if (ts.isConditionalExpression(pp) || isLogical(pp)) return "read through a conditional or logical expression the walker does not follow: bind the module in a statement of its own";
    if (ts.isVariableDeclaration(pp) && pp.initializer === q) return ts.isIdentifier(pp.name) ? "aliased by a declaration" : "destructured";
    if (ts.isBinaryExpression(pp) && isAssignmentOp(pp) && pp.right === q) return "aliased by an assignment";
    // any other binary operator, either side (`leg !== null`, `null !== leg`; a logical one is named above, and the left side of an
    // assignment is the one exempt operand position, read by the value-use arm as a declaration): the binding is read as a value
    if (ts.isBinaryExpression(pp)) return "read as an operand of " + ts.tokenToString(pp.operatorToken.kind) + ", a value use the walker does not follow: use the binding only to call inBrowser";
    if (ts.isNewExpression(pp)) return pp.expression === q ? "constructed with new, which the launcher's module is not: call its inBrowser" : "passed as an argument";
    if (ts.isCallExpression(pp)) return pp.expression === q ? "called as a function, which the launcher's module is not: call its inBrowser" : "passed as an argument";
    if (ts.isArrayLiteralExpression(pp) || ts.isPropertyAssignment(pp) || ts.isShorthandPropertyAssignment(pp)) return "held in an array or an object literal";
    if (ts.isReturnStatement(pp) || ts.isArrowFunction(pp)) return "returned from a function";
    return "in a position the walker does not read (" + ts.SyntaxKind[pp.kind] + ")";
  };
  const walk3 = (n) => {
    if (ts.isCallExpression(n)) {
      {
        const l = loaderCall(n);
        if (l && l.kind === "local") noteLocal(n, l);
        else if (l && l.kind === "launcher") {
          // the launcher loaded as a statement of its own (`require(launcher);`): FOLLOWED, an import that calls nothing. A
          // binder position is bindLoaded's; the object of a member is followed below where the member is read; any other
          // position stays unfollowed and THE INVARIANT refuses it
          let q = n; while (q.parent && (ts.isParenthesizedExpression(q.parent) || ts.isAwaitExpression(q.parent) || ts.isAsExpression(q.parent) || ts.isNonNullExpression(q.parent))) q = q.parent;
          if (q.parent && ts.isExpressionStatement(q.parent)) { followed.add(unwrap(n)); launcherImported.push(lineOf(n)); }
        }
      }
      let c = unwrap(n.expression);
      // .call / .apply on the callee (.bind makes no call: a bound reference is read as a value use below)
      let viaCall = false;
      if ((ts.isPropertyAccessExpression(c)) && ["call", "apply"].includes(c.name.text)) { viaCall = c.name.text; c = unwrap(c.expression); }
      if (ts.isIdentifier(c)) {
        const b = bindingAt(c);
        if (b && b.module === "launcher" && b.member === "inBrowser") { sharedCalls++; calledThrough.add(c); readEngineArg(n, viaCall); if (inTryWithCatch(n)) swallow.push(lineOf(n)); }
        const d = derivedAt(c);
        if (d) { const last = d.chain[d.chain.length - 1] || []; if (last.some((x) => LAUNCHES.has(x))) launches.push({ line: lineOf(n), how: "call of destructured " + last.join("|") + (viaCall ? " via .call/.apply" : "") }); }
        if (b && b.module === "playwright" && b.member && LAUNCHES.has(b.member.split(".").pop())) launches.push({ line: lineOf(n), how: "call of imported " + b.member });
      } else if (ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c)) {
        const names = memberNames(c);
        const obj = unwrap(c.expression);
        if (names === null) { const r = rootOf(c); if (isTrackedRoot(r) || (loadRoot(c) || {}).kind === "playwright") { refuse(c, "a computed member with a name the walker cannot fold on a playwright or launcher binding or load"); refusedRoots.add(r); } }
        else {
          if (names.some((x) => x === "skip" || x === "todo")) skipTodo.push({ line: lineOf(n), what: "." + names.join("|") + "(" });
          // launcher namespace or default binding: leg.inBrowser(...); or the loader call's own result: require(launcher).inBrowser(...)
          if (ts.isIdentifier(obj)) { const b = bindingAt(obj); if (b && b.module === "launcher" && (b.member === null || b.member === "default") && names.includes("inBrowser")) { sharedCalls++; calledThrough.add(obj); readEngineArg(n, viaCall); if (inTryWithCatch(n)) swallow.push(lineOf(n)); } }
          else {
            // the loader call's own result as the object: `require(launcher).inBrowser(...)` is a shared call and any other export
            // read is an import; `.then(cb)` (or .catch, .finally) hands the module to a callback the walker does not follow, and
            // `.default` is no export of the launcher: refused by name, the load read (followed) by that refusal
            const l = loaderCall(obj); if (l && l.kind === "launcher") { followed.add(unwrap(obj)); if (names.some((x) => HANDOFF.has(x))) refuse(n, "the launcher loaded where it stands and handed on through a member the walker does not follow (a promise callback through .then, .catch or .finally, or a default member), so where inBrowser is called from is unread: await the load and call inBrowser on the result"); else { launcherImported.push(lineOf(n)); if (names.includes("inBrowser")) { sharedCalls++; readEngineArg(n, viaCall); if (inTryWithCatch(n)) swallow.push(lineOf(n)); } } }
          }
          if (names.some((x) => LAUNCHES.has(x))) { const chain = pwChain(obj); if (chain && !chain.refused) { noteChain(chain); launches.push({ line: lineOf(n), how: "." + names.join("|") + "(" + (viaCall ? " via .call/.apply" : "") }); } }
          const chain = pwChain(c); if (chain && !chain.refused) noteChain(chain);
        }
      }
      // { skip: ..., todo: ... } option properties in an argument object literal
      for (const a of n.arguments) if (ts.isObjectLiteralExpression(unwrap(a))) for (const p of unwrap(a).properties) { const nm = p.name && (ts.isIdentifier(p.name) ? p.name.text : literalName(p.name)); if (nm === "skip" || nm === "todo") skipTodo.push({ line: lineOf(p), what: "{ " + nm + ": } option" }); }
    } else if (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) {
      // an engine read that is not a call: const b = pw.firefox (bound above), or await pw.firefox.launch handled at the call
      if (!(n.parent && (ts.isCallExpression(n.parent) && n.parent.expression === n))) { const chain = pwChain(n); if (chain && !chain.refused) noteChain(chain); }
      // a member read off the launcher loaded where it stands, not a call (`require(launcher).EXT`; the call form is above):
      // FOLLOWED as an import when the member is another export; a read of inBrowser without a call, of a promise member or
      // of a default member hands it on and stays unfollowed, so THE INVARIANT refuses it
      // (a requireCjs member is a loader callee when called, through parentheses, ! and as too, read by loaderCall; read without a
      // call it hands the loader on, and a load made through it elsewhere is unread: refused by name, the load followed by that refusal)
      if (!(n.parent && ts.isCallExpression(n.parent) && n.parent.expression === n)) { const obj = unwrap(n.expression); const l = !ts.isIdentifier(obj) && loaderCall(obj); if (l && l.kind === "launcher") { const names = memberNames(n); let q = n; while (q.parent && (ts.isParenthesizedExpression(q.parent) || ts.isNonNullExpression(q.parent) || ts.isAsExpression(q.parent))) q = q.parent; const isCallee = q.parent && ts.isCallExpression(q.parent) && q.parent.expression === q; if (names !== null && names.includes("requireCjs")) { if (!isCallee) { followed.add(unwrap(obj)); refuse(n, "the launcher loaded where it stands and read for requireCjs without a call, so a load made through it elsewhere is unread: call requireCjs on the load where it is made"); } } else if (names !== null && !names.includes("inBrowser") && !names.some((x) => HANDOFF.has(x))) { followed.add(unwrap(obj)); launcherImported.push(lineOf(n)); } } }
    } else if (ts.isIdentifier(n)) {
      // a reference to a launcher binding (inBrowser, the whole module or its default) that the call arm did not resolve a call
      // through (calledThrough), and that is not a declaration name, a property name or an import clause: a value use, refused
      const b = bindingAt(n);
      if (b !== null && b.module === "launcher" && b.member === "requireCjs") {
        // the loader binding itself (the named import, or the member destructured from a load): read as a callee (loaderCall, through
        // parentheses, ! and as) or in a name, property or type position; any other use hands the loader on (`const r = requireCjs`),
        // and a load made through the alias is unread by the walker: refused by name
        const p = n.parent;
        let q = n; while (q.parent && (ts.isParenthesizedExpression(q.parent) || ts.isNonNullExpression(q.parent) || ts.isAsExpression(q.parent))) q = q.parent;
        const called = q.parent && ts.isCallExpression(q.parent) && q.parent.expression === q;
        const isDecl = p && (ts.isImportSpecifier(p) || (ts.isBindingElement(p) && (p.name === n || p.propertyName === n)) || (ts.isVariableDeclaration(p) && p.name === n) || (ts.isBinaryExpression(p) && p.left === n && isAssignmentOp(p)));
        const isPropName = p && ((ts.isPropertyAccessExpression(p) && p.name === n) || (ts.isPropertyAssignment(p) && p.name === n));
        const isType = p && (ts.isTypeQueryNode(p) || ts.isTypeReferenceNode(p));
        if (!(called || isDecl || isPropName || isType)) refuse(n, "the launcher's requireCjs loader handed on as a value, not called (a load made through the alias is unread by the walker: call requireCjs where the load is made)");
      }
      if (carriesInBrowser(b)) {
        const p = n.parent;
        // the NAME position of a declaration is exempt, never its initializer: `const f = inBrowser` and `const { x = inBrowser } = o`
        // hand the binding on as a value and are refused; a type position (`typeof inBrowser`, a type reference) binds nothing;
        // of a binary expression only an ASSIGNMENT's left side is a name position (`leg ?? null` and `leg !== null` read the
        // binding as a value and fall through to the refusals below: an exemption on any left operand left them silent)
        const isDecl = p && (ts.isImportSpecifier(p) || ts.isNamespaceImport(p) || ts.isImportClause(p) || ts.isImportEqualsDeclaration(p) || (ts.isBindingElement(p) && (p.name === n || p.propertyName === n)) || (ts.isVariableDeclaration(p) && p.name === n) || (ts.isBinaryExpression(p) && p.left === n && isAssignmentOp(p)));
        const isPropName = p && ((ts.isPropertyAccessExpression(p) && p.name === n) || (ts.isPropertyAssignment(p) && p.name === n));
        const isType = p && (ts.isTypeQueryNode(p) || ts.isTypeReferenceNode(p));
        if (calledThrough.has(n) || isDecl || isPropName || isType) refRead.add(n);
        else if (b.member === "inBrowser") { refuse(n, "the launcher's inBrowser binding used as a value, not called (the walker cannot follow where it is called from)"); refRefused.add(n); }
        else {
          // the whole module or its default: up through parentheses, ! and as, then the object of a member access is read when
          // the member is another export (not inBrowser, not then/catch/finally, not default) or when the computed-member arm
          // refused it by name (refusedRoots); an inBrowser member here was not called (else the call arm recorded this node),
          // so the binding is handed on: refused, the message naming the position the line holds (handedHow)
          let q = n; while (q.parent && (ts.isParenthesizedExpression(q.parent) || ts.isNonNullExpression(q.parent) || ts.isAsExpression(q.parent))) q = q.parent;
          const pp = q.parent;
          let read = false, handed = true;
          // (a requireCjs member is read when called, through parentheses, ! and as, the loader callee loaderCall accepts; read without
          // a call it hands the loader on, and handedHow names that form)
          if (pp && (ts.isPropertyAccessExpression(pp) || ts.isElementAccessExpression(pp)) && pp.expression === q) { const names = memberNames(pp); if (names === null) { read = refusedRoots.has(n); handed = false; } else { let qq = pp; while (qq.parent && (ts.isParenthesizedExpression(qq.parent) || ts.isNonNullExpression(qq.parent) || ts.isAsExpression(qq.parent))) qq = qq.parent; const calledMember = qq.parent && ts.isCallExpression(qq.parent) && qq.parent.expression === qq; read = !names.includes("inBrowser") && !names.some((x) => HANDOFF.has(x)) && !(names.includes("requireCjs") && !calledMember); handed = !read; } }
          if (read) refRead.add(n);
          else if (handed) { refuse(n, "the launcher's module binding handed on as a value (" + handedHow(q, pp) + "), so the walker cannot follow where inBrowser is called from"); refRefused.add(n); }
          // a computed member no arm refused: left to THE INVARIANT below
        }
      }
    }
    ts.forEachChild(n, walk3);
  };
  walk3(sf);

  // a string or template literal whose TEXT names a playwright package or the launcher: source for a child process (a driver),
  // a source pin, or a message; the module's own code reaches no browser through it, so it is reported as its own class
  const embedded = [];
  const DRIVER_RE = /(require|import)\s*\(\s*["'`](playwright(-core)?|@playwright\/test)["'`]|from\s+["'`](playwright(-core)?|@playwright\/test)["'`]/;
  /** The text of a string built from pieces, folded before the driver regex reads it: a literal; a template whose substitutions
   *  are identifiers bound to one const literal (any other substitution a <placeholder>, which matches nothing: the third
   *  residual); a + chain of such. */
  const foldText = (x) => {
    x = unwrap(x);
    const l = literalName(x); if (l !== null) return l;
    if (ts.isTemplateExpression(x)) { let t = x.head.text; for (const sp of x.templateSpans) { const inner = ts.isIdentifier(unwrap(sp.expression)) ? constInitializer(unwrap(sp.expression).text) : undefined; const v = inner ? literalName(unwrap(inner)) : null; t += (v !== null && v !== undefined ? v : "<" + sp.expression.getText(sf) + ">") + sp.literal.text; } return t; }
    if (ts.isBinaryExpression(x) && x.operatorToken.kind === ts.SyntaxKind.PlusToken) return foldText(x.left) + foldText(x.right);
    return "<" + x.getText(sf).slice(0, 40) + ">";
  };
  const noteEmbedded = (n) => { const line = lineOf(n); if (!embedded.some((e) => e.line === line)) embedded.push({ line, what: "playwright loaded by source held in a string (a child-process driver)" }); };
  const walkStr = (n) => {
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n)) {
      if (DRIVER_RE.test(n.text)) noteEmbedded(n);
    } else if (ts.isTemplateExpression(n) || (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.PlusToken)) {
      if (DRIVER_RE.test(foldText(n))) noteEmbedded(n);
    }
    ts.forEachChild(n, walkStr);
  };
  walkStr(sf);
  // THE INVARIANT (the header states it): what the parse resolved against what the record carries, three clauses; a module
  // that breaks one is refused naming the line and what was resolved, so no resolution ends as a silent class none
  const importedLines = new Set([...launcherImported, ...typeOnly.map((t) => t.line)]);
  for (const [n, r] of resolved) {
    if (r.kind === "playwright" && !playwright.has(r.spec) && !(r.how === "import" && typeOnly.some((t) => t.line === r.line && t.spec === r.spec))) refuse(n, "THE INVARIANT: the census resolved the playwright package " + r.spec + " here and its record carries no playwright package, a position the walker does not read; the census refuses rather than guesses");
    else if (r.kind === "launcher" && r.how === "import" && !importedLines.has(r.line)) refuse(n, "THE INVARIANT: the census resolved the shared launcher (" + r.spec + ") here and its record carries neither an import nor a type-only import of it; the census refuses rather than guesses");
    else if (r.kind === "launcher" && r.how === "load" && !followed.has(n)) refuse(n, "THE INVARIANT: the census resolved the shared launcher (" + r.spec + ") here and its record carries nothing of the load, which stands in a position the walker does not read (not a binding's initializer, an assignment's right side, a statement of its own, or the object of a member the walker read: here it is returned, passed, held in a field, a property or an array, read for inBrowser without a call, or read for a default member, which is not an export of the launcher); the census refuses rather than guesses: bind the load to a name, or call inBrowser on it directly");
  }
  const walkRefs = (n) => { if (ts.isIdentifier(n) && carriesInBrowser(bindingAt(n)) && !refRead.has(n) && !refRefused.has(n)) refuse(n, "THE INVARIANT: the census resolved the name " + n.text + " here to the shared launcher's binding and its record carries nothing of this use, a position the walker does not read; the census refuses rather than guesses"); ts.forEachChild(n, walkRefs); };
  walkRefs(sf);
  const seenL = new Set(); const launchesU = launches.filter((l) => { const k = l.line + "|" + l.how; if (seenL.has(k)) return false; seenL.add(k); return true; }); launches.length = 0; launches.push(...launchesU);
  const reaches = sharedCalls > 0 || playwright.size > 0 || embedded.length > 0;
  // the module holds inBrowser under a binding (named, whole-module or default), re-exports it, or calls it (on a binding or on
  // a load where it stands): what a module that imports THIS one reaches through it
  let launcherBinds = launcherReexport || sharedCalls > 0;
  for (const [, b] of bindings) if (b.module === "launcher" && (b.member === null || b.member === "default" || b.member === "inBrowser")) launcherBinds = true;
  const seenI = new Set(); const localU = localImports.filter((l) => { const k = l.line + "|" + l.spec; if (seenI.has(k)) return false; seenI.add(k); return true; });
  return { rel, refusals, launcherImported: launcherImported.length > 0, typeOnly, launcherBinds, sharedCalls, embedded, playwright: [...playwright].sort(), engines: [...engines].sort(), launches, skipTodo, swallow, reaches, localImports: localU };
}

const MODULE_EXT = /\.(d\.ts|[cm]?ts|[cm]?js)$/;
const fileAt = (p) => { try { return fs.statSync(p).isFile() ? p : null; } catch { return null; } };
/** The files a path names, tried in order: the .ts beside a .js spelling, the path itself, a .d.ts, a .js, a directory's index. */
const candidatesOf = (raw) => /\.[cm]?js$/.test(raw) ? [raw.replace(/\.[cm]?js$/, ".ts"), raw.replace(/\.[cm]?js$/, ".d.ts"), raw]
  : /\.[cm]?ts$/.test(raw) ? [raw]
  : [raw + ".ts", raw + ".d.ts", raw + ".js", raw + ".mjs", raw + ".cjs", path.join(raw, "index.ts"), path.join(raw, "index.js"), raw];
/** The file a local specifier names. A relative specifier resolves against the loading module's directory; a specifier that
 *  names no file there (a loader bound elsewhere by createRequire, a path expression folded to its literal pieces with the
 *  non-literal pieces dropped) resolves against the two bases loaders in this tree are anchored to, the repo root and
 *  vscode-extension/ (process.cwd() under npm test), UNDER THE ROOT ALONE: a candidate a base resolution carries outside the
 *  root (`../ui/<f>` against the root lands beside the checkout) is dropped before it is looked up, so a sibling directory beside
 *  the checkout is never read as a module of the tree and never an ambiguity, and the population is derived from the tree alone.
 *  The first resolution, beside the module, is the module's own relative path and may name a file outside the checkout (a test
 *  that loads one does so by its spelling): stated, not clamped. Returns { abs } (a file that is not a script, json or css, is
 *  returned and read by nobody), { ambiguous: [a, b] } when the two bases name different files, or null when none does. */
export function resolveLocal(fromFile, spec, root) {
  const clean = spec.replace(/<[^>]*>/g, "").replace(/\/{2,}/g, "/").replace(/^\/+/, "");
  const first = candidatesOf(path.resolve(path.dirname(fromFile), spec)).map(fileAt).find(Boolean);
  if (first) return { abs: first };
  const underRoot = (p) => { const rel = path.relative(root, p); return rel !== "" && rel !== ".." && !rel.startsWith(".." + path.sep) && !path.isAbsolute(rel); };
  const hits = [...new Set([root, path.join(root, "vscode-extension")].map((b) => candidatesOf(path.resolve(b, clean)).filter(underRoot).map(fileAt).find(Boolean)).filter(Boolean))];
  if (hits.length === 1) return { abs: hits[0] };
  if (hits.length > 1) return { ambiguous: hits };
  return null;
}
const isPackagePath = (abs) => abs.split(path.sep).includes("node_modules");

/** The refusals a test module owes to the modules of the tree it loads, read transitively (a cache of own records per module,
 *  a walk over the import graph per test import, so a cycle is visited once): a test whose import reaches a module that binds
 *  or calls the launcher's inBrowser (and the test itself never calls inBrowser), names a playwright package, holds a driver string, or
 *  a form the walker refuses, is refused at its import line with the chain. The walker follows nothing THROUGH such a module
 *  (it does not read what the test calls on it), so the remedy is to import the launcher directly, or to teach the census. */
export function localRefusals(ts, r, file, root, opts, ownCache) {
  const own = (abs) => {
    if (!ownCache.has(abs)) {
      const rec = classify(ts, abs, fs.readFileSync(abs, "utf8"), { ...opts, root });
      ownCache.set(abs, { rec, next: rec.refusals.length ? [] : rec.localImports.map((li) => ({ li, to: resolveLocal(abs, li.spec, root) })) });
    }
    return ownCache.get(abs);
  };
  const out = [];
  const at = (li, why) => { const msg = r.rel + ":" + li.line + ": " + why + ": the walker reads a module of the tree for the launcher and playwright bindings it holds and follows nothing through it; import ui/webview/real-viewer-leg.ts directly in this module, or teach scripts/browser-legs-census.mjs the module: " + li.text; if (!out.includes(msg)) out.push(msg); };
  const unresolved = (li, to, where) => (to === null ? "loads " + li.spec + ", which names no file in the tree (tried beside " + where + ", under the repo root and under vscode-extension/)" : "loads " + li.spec + ", which names two files (" + to.ambiguous.map((a) => path.relative(root, a)).join(" and ") + "), so the walker cannot tell which one it reads");
  for (const li of r.localImports) {
    const start = resolveLocal(file, li.spec, root);
    if (start === null || start.ambiguous) { at(li, unresolved(li, start, r.rel)); continue; }
    if (!MODULE_EXT.test(start.abs) || isPackagePath(start.abs)) continue;   // json, css: not a script; a package under node_modules binds nothing of the tree
    const seen = new Set([start.abs]), queue = [{ abs: start.abs, chain: [] }];
    let refused = false;
    while (queue.length && !refused) {
      const { abs, chain } = queue.shift();
      const rel = path.relative(root, abs), via = [...chain, rel];
      const link = via.map((x, i) => (i === 0 ? "loads " + x : ", which loads " + x)).join("");
      const { rec, next } = own(abs);
      if (rec.refusals.length) { at(li, link + ", which the census cannot classify (" + rec.refusals[0] + ")"); refused = true; break; }
      if (rec.playwright.length) { at(li, link + ", which names a playwright package (" + rec.playwright.join(", ") + "), so this module reaches a browser through it"); refused = true; break; }
      if (rec.embedded.length) { at(li, link + ", which holds a driver string that loads playwright (line " + rec.embedded[0].line + ")"); refused = true; break; }
      if (rec.launcherBinds && r.sharedCalls === 0) { at(li, link + ", which binds or calls the shared launcher's inBrowser, so this module may launch through it without the census seeing a call"); refused = true; break; }
      for (const n of next) {
        if (n.to === null || n.to.ambiguous) { at(li, link + ", which " + unresolved(n.li, n.to, rel) + " (" + rel + ":" + n.li.line + ")"); refused = true; break; }
        if (!MODULE_EXT.test(n.to.abs) || isPackagePath(n.to.abs) || seen.has(n.to.abs)) continue;
        seen.add(n.to.abs); queue.push({ abs: n.to.abs, chain: via });
      }
    }
  }
  return out;
}

const bundleOf = (dir, f) => "out-tests/" + dir + "/" + f.replace(/\.test\.ts$/, ".test.js");

/** The census over a tree: { legs: [bundle...] sorted, byBundle: Map bundle -> classify record (every module read, leg or
 *  not), refusals: [...], localModules: how many modules of the tree the test modules load were read }. */
export function census(root = REPO, opts = {}) {
  root = path.resolve(root);
  const ts = loadTypescript();
  const legs = [], byBundle = new Map(), refusals = [];
  const ownCache = new Map();   // the modules of the tree the test modules load, each read once
  for (const dir of LEG_DIRS) {
    const abs = path.join(root, dir);
    if (!fs.existsSync(abs)) continue;
    for (const f of fs.readdirSync(abs).filter((f) => f.endsWith(".test.ts")).sort()) {
      const file = path.join(abs, f);
      const r = classify(ts, file, fs.readFileSync(file, "utf8"), { ...opts, root });
      if (r.localImports) r.refusals.push(...localRefusals(ts, r, file, root, opts, ownCache));
      const bundle = bundleOf(dir, f);
      byBundle.set(bundle, r);
      if (r.refusals.length) refusals.push(...r.refusals);
      if (r.reaches) legs.push(bundle);
    }
  }
  return { legs: legs.sort(), byBundle, refusals, localModules: ownCache.size };
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
