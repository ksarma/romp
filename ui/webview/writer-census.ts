/** The writer CENSUS of a source (T386 stage 1, round seven): every call of the scroll-write family, read with the TypeScript
 *  compiler's own parser, so strings, template literals, regular expressions, comments and nesting are what the language says
 *  they are, never what a regular expression guessed.
 *
 *  The rule the census enforces (landing-settle.ts WRITER_CLASS and WRITER_WRAPPERS): at a call of the write helper or of a
 *  registered wrapper, the argument at the writer's position is a PLAIN STRING LITERAL, or it is a parameter of the enclosing
 *  function, which is then a wrapper and must be in the table at that parameter's position. Anything else at that position, a
 *  template literal, a concatenation, a module-level constant, a variable, a spread, is a FAILURE naming the call; a function
 *  that passes one of its own parameters through, whatever the parameter is called and however the function is written (async,
 *  nested, a method, an arrow), is a wrapper and must be registered; a registered name that passes nothing through is stale.
 *  The table's root (the write helper itself) is the one entry that forwards to nothing.
 *
 *  The census reads SYNTAX, not data flow (round seven, low 1): a family function called through a property access
 *  (`x.writeScroll(...)`, `writeScroll.call(...)`) or given another name (`const w = writeScroll`) is a FAILURE naming the site,
 *  since a call by any other route would count nothing; a wrapper's writer parameter that a block const shadows or a reassignment
 *  changes before the family call is NOT followed: the census counts the caller's literal, and the string written may differ.
 *  Neither shape occurs in render.ts; the pin holds the first, the second is the stated limit.
 *
 *  The module's second census, cardStateCensus, reads file-comments.ts for every assignment to the Panel's private #cardState,
 *  every call of its private writer and every call of the names it is given. It lists every other mention of those names in the
 *  file's code (a decorator on a declaration by the name or on its parameters among them), their own declarations aside; every
 *  decorator on the declaration of #cardState, #latchCardState or #replaced or on its parameters; and these doors to code in a
 *  string: eval and Function by name; the identifier constructor; a string literal spelled eval, Function, constructor,
 *  setTimeout or setInterval; and a timer given anything but a function written in place. It reads no name computed at run
 *  time, no code in another module, and none of the other ways a page runs code from a string, such as a module imported from a
 *  data address, handler attributes or markup, and an element whose text runs as code. The card-state rule is stated in
 *  #cardState's doc there; this census's own doc says what it counts and what it lists for the test to hold empty.
 *
 *  Node-only: the tests import it; the webview bundle never does. */
import * as ts from "typescript";

export type CensusFailure = { line: number; call: string; why: string };
export type WriterCensus = {
  /** every plain string literal at a writer position, sorted, unique */
  literals: string[];
  /** every function that passes one of its own parameters at a writer position, with that parameter's index */
  wrappers: Record<string, number>;
  /** every call and every wrapper the rule refuses, each naming its line */
  failures: CensusFailure[];
};

/** A writer name: lower-case words and digits, hyphen-joined (the ledger's vocabulary). */
export const WRITER_NAME = /^[a-z][a-z0-9-]*$/;

export function writerCensus(src: string, table: Readonly<Record<string, number>>, root = "writeScroll", file = "render.ts"): WriterCensus {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const literals = new Set<string>();
  const wrappers: Record<string, number> = {};
  const wrapperLine: Record<string, number> = {};
  const failures: CensusFailure[] = [];
  const lineOf = (n: ts.Node): number => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const shown = (n: ts.Node): string => n.getText(sf).replace(/\s+/g, " ").slice(0, 90);
  const fail = (n: ts.Node, call: string, why: string): void => { failures.push({ line: lineOf(n), call, why }); };
  /** The argument's kind by its node (SyntaxKind's numeric aliases print their first name: a template literal without a substitution
   *  would read FirstTemplateToken). */
  const kindName = (n: ts.Node): string => ts.isNoSubstitutionTemplateLiteral(n) ? "NoSubstitutionTemplateLiteral" : ts.isTemplateExpression(n) ? "TemplateExpression" : ts.SyntaxKind[n.kind];

  /** The function that OWNS a parameter name at a use site: the nearest enclosing function whose parameter list names it (an
   *  inner function's parameter of the same name shadows an outer one, as in the language). */
  const ownerOf = (from: ts.Node, name: string): { fn: ts.SignatureDeclaration; index: number } | null => {
    for (let n: ts.Node | undefined = from.parent; n; n = n.parent) {
      if (ts.isFunctionLike(n)) {
        const index = n.parameters.findIndex((p) => ts.isIdentifier(p.name) && p.name.text === name);
        if (index >= 0) return { fn: n, index };
      }
    }
    return null;
  };
  /** A function's name however it is written: a declaration's or method's own, the variable or property it is assigned to. */
  const nameOf = (fn: ts.SignatureDeclaration): string | null => {
    if ((ts.isFunctionDeclaration(fn) || ts.isMethodDeclaration(fn) || ts.isFunctionExpression(fn)) && fn.name) return fn.name.getText(sf);
    const p = fn.parent;
    if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
    if (p && (ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p))) return p.name.getText(sf);
    return null;
  };

  const inTable = (name: string): boolean => Object.prototype.hasOwnProperty.call(table, name);
  const visit = (n: ts.Node): void => {
    // a family function reached by any route but its bare name counts nothing here, so it fails loudly (round seven, low 1)
    if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression)) {
      const pa = n.expression;
      if (inTable(pa.name.text)) fail(n, shown(n), pa.name.text + " is called through a property access; the census reads a call by its bare name only");
      else if (ts.isIdentifier(pa.expression) && inTable(pa.expression.text)) fail(n, shown(n), pa.expression.text + "." + pa.name.text + " calls the family by another route; the census reads a call by its bare name only");
    }
    if (ts.isVariableDeclaration(n) && n.initializer && ts.isIdentifier(n.initializer) && inTable(n.initializer.text))
      fail(n, shown(n), n.initializer.text + " is given another name; a call through it would count nothing");
    if (ts.isCallExpression(n) && ts.isIdentifier(n.expression) && Object.prototype.hasOwnProperty.call(table, n.expression.text)) {
      const callee = n.expression.text;
      const pos = table[callee];
      const arg = n.arguments[pos];
      const call = shown(n);
      if (!arg) fail(n, call, callee + " takes its writer at position " + pos + " and this call passes nothing there");
      else if (ts.isStringLiteral(arg)) {
        if (WRITER_NAME.test(arg.text)) literals.add(arg.text);
        else fail(n, call, JSON.stringify(arg.text) + " is not a writer name (lower-case words and digits, hyphen-joined)");
      } else if (ts.isIdentifier(arg)) {
        const owner = ownerOf(n, arg.text);
        if (!owner) fail(n, call, "the writer is the variable " + arg.text + ": not a plain string literal, and not a parameter of any enclosing function");
        else {
          const wname = nameOf(owner.fn);
          if (!wname) fail(n, call, "an anonymous function passes its parameter " + arg.text + " as the writer: name it and register it in WRITER_WRAPPERS");
          else {
            if (wname in wrappers && wrappers[wname] !== owner.index) fail(owner.fn, wname, "passes its writer from two positions (" + wrappers[wname] + " and " + owner.index + ")");
            wrappers[wname] = owner.index;
            wrapperLine[wname] = lineOf(owner.fn);
          }
        }
      } else fail(n, call, "the writer is " + kindName(arg) + ", not a plain string literal");
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);

  for (const w of Object.keys(wrappers)) {
    if (!Object.prototype.hasOwnProperty.call(table, w)) failures.push({ line: wrapperLine[w], call: w, why: "passes its parameter " + wrappers[w] + " to the family and is not in WRITER_WRAPPERS" });
    else if (table[w] !== wrappers[w]) failures.push({ line: wrapperLine[w], call: w, why: "is registered at position " + table[w] + " but passes its parameter " + wrappers[w] });
  }
  for (const t of Object.keys(table)) {
    if (t === root || Object.prototype.hasOwnProperty.call(wrappers, t)) continue;
    failures.push({ line: 0, call: t, why: "is in WRITER_WRAPPERS but passes no parameter of its own to the family in this source" });
  }
  // the root: a function of that name, with a parameter at the table's position
  let rootSeen = false;
  const findRoot = (n: ts.Node): void => {
    if (ts.isFunctionDeclaration(n) && n.name && n.name.text === root) { rootSeen = true; if (n.parameters.length <= table[root]) failures.push({ line: lineOf(n), call: root, why: "the root has no parameter at position " + table[root] }); }
    else ts.forEachChild(n, findRoot);
  };
  findRoot(sf);
  if (!rootSeen) failures.push({ line: 0, call: root, why: "the root is not declared as a function in this source" });

  failures.sort((a, b) => a.line - b.line || a.call.localeCompare(b.call));
  return { literals: [...literals].sort(), wrappers, failures };
}

/** A place the card-state census found: the function it sits in (for a decorator in `decorators`, the declaration it decorates),
 *  its line, its text, and for a call of the writer the event it names. */
export type CardSite = { fn: string; line: number; text: string; at?: string };
/** The card-state census (file-comments.ts: the Panel's private #cardState, whose doc states the rule it keeps). Each site it
 *  finds is named by the function it sits in: a method's or a function's own name, "constructor", or for a callback its host's
 *  name ("onRendered's callback", "fcinline's callback"); a decorator in `decorators` is named by the declaration it decorates.
 *  It COUNTS: the declarations of #cardState (decls); every assignment to #cardState (writes) and to #replaced, the count of the
 *  body's changes the rule reads (counts), an assignment being any assignment operator's, a destructuring target's, a for-in or
 *  for-of head's, or an increment's or a decrement's whose target is the private field; every call of #latchCardState, with the
 *  event its first argument names (calls); and every call of `callees` (callers), a call whose callee is the name itself or a
 *  property access ending in it (`name(...)`, `this.name(...)`, `x?.name(...)`).
 *  It LISTS, for the test to hold empty (fail closed): a mention of #latchCardState that is not a call of it (refs), and these
 *  doors to code in a string, whose code no census reads (evals): every identifier spelled eval or Function, however it is
 *  written (a unicode escape reads as the name) and wherever it stands, a call's callee or not; every identifier spelled
 *  constructor (a function's constructor property is the Function constructor, `(function () {}).constructor`, or for an async,
 *  a generator or an async generator function that constructor's async, generator or async generator kin, each of which makes a
 *  function of a string); every string literal, quoted or a template with no substitution, whose text is eval, Function,
 *  constructor, setTimeout or setInterval (an element access's key, `globalThis["eval"]`, `` globalThis[`eval`] ``); and every
 *  identifier spelled setTimeout or setInterval but the callee of a call whose first argument, through parentheses, is a function
 *  written in place (an arrow function or a function expression) and a name in a type (`ReturnType<typeof setTimeout>`; an
 *  instantiation expression, `setTimeout<[string]>`, is a value and is listed), since a timer given anything else may be given a
 *  string, which it runs as code, and one handed on or given another name may be called so. A
 *  direct eval inside the class runs its string as the class's own code, so it can write a private field where no syntax shows
 *  it, as a decorator on the field's declaration can through the access it is handed (decorators, below); no other road
 *  reaches one: a private name is written in no other syntax (no computed key, no Object.assign, Reflect or
 *  defineProperty, and `delete` of it does not parse), code outside its class cannot name it, and an indirect eval, a Function
 *  body or a timer's string runs as global code, where the name does not parse. A write through the state meets an object frozen
 *  at its one assignment, which throws. A private name's element-access spelling (a string key "#cardState") reaches a
 *  different, public property and is none of these. Global code can still call a public method, such as a name in `callees`, on
 *  a panel handed to it (a Function's parameters) or reachable from it, with no mention of that name in this file.
 *  It LISTS as well, for the test to hold empty, every decorator on a declaration of #cardState, #latchCardState or #replaced or
 *  on one of its parameters (decorators): one on a private field is handed access that reads and writes the field, and one on a
 *  private method is handed the method and, through addInitializer, the instance, so its body, which may sit outside the class,
 *  can write the field or call the method where no syntax in this file shows it.
 *  It also LISTS every other mention of a name in `callees` (calleeRefs, by name), for a test that needs that name's callers exact
 *  to hold empty: the name as an identifier anywhere but a counted call's callee and the name a class member, a function or a
 *  signature is declared by (a reference bound or handed on, `this.name.bind(this)`; an alias, `const f = this.name`; a
 *  destructured name; a call through parentheses or `.call`); every string literal whose text is the name (an element access's
 *  key, `this["name"]()`, or Reflect's argument); and every decorator on a declaration by the name or on one of its parameters,
 *  which is handed the method it decorates (and, through addInitializer, the instance) and may call it with no mention of the
 *  name. So the census reads this file's syntax alone: a name computed at run time (`this[k]`, a concatenation) is in neither
 *  callers nor calleeRefs; code in another module is not read (a decorator on a member whose decorators are not listed is handed
 *  that member and the instance, and its body may sit in another module); and none of the other ways a page runs code from a
 *  string is read or listed, such as a module imported from a data address (`import("data:...")`), handler attributes or markup
 *  (`setAttribute("onclick", ...)`, markup given to innerHTML), and an element whose text runs as code. */
export function cardStateCensus(src: string, callees: string[] = [], file = "file-comments.ts"): { decls: number; writes: CardSite[]; calls: CardSite[]; refs: CardSite[]; counts: CardSite[]; evals: CardSite[]; decorators: CardSite[]; callers: Record<string, string[]>; calleeRefs: Record<string, CardSite[]> } {
  const sf = ts.createSourceFile(file, src, 99, true);   // 99: the compiler's newest language level (its enum's Latest), so every construct of the file parses; the kind follows the name's .ts
  const lineOf = (n: ts.Node): number => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const shown = (n: ts.Node): string => n.getText(sf).replace(/\s+/g, " ").slice(0, 120);
  const fnName = (n: ts.Node): string => {
    for (let x: ts.Node | undefined = n.parent; x; x = x.parent) {
      if (ts.isConstructorDeclaration(x)) return "constructor";
      if ((ts.isMethodDeclaration(x) || ts.isFunctionDeclaration(x) || ts.isGetAccessor(x) || ts.isSetAccessor(x)) && x.name) return x.name.getText(sf);
      if (ts.isArrowFunction(x) || ts.isFunctionExpression(x)) {
        const p = x.parent;
        if (ts.isCallExpression(p)) return (ts.isPropertyAccessExpression(p.expression) ? p.expression.name.text : p.expression.getText(sf)) + "'s callback";
        if (ts.isPropertyAssignment(p)) return p.name.getText(sf) + "'s callback";
        if (ts.isVariableDeclaration(p) || ts.isPropertyDeclaration(p)) return p.name.getText(sf);
        return "a callback at line " + lineOf(x);
      }
    }
    return "the module";
  };
  /** Whether `e`, through parentheses and type assertions, is `<object>.#name`. */
  const isPrivate = (e: ts.Node, name: string): boolean => {
    let x: ts.Node = e;
    while (ts.isParenthesizedExpression(x) || ts.isAsExpression(x) || ts.isNonNullExpression(x) || ts.isTypeAssertionExpression(x) || ts.isSatisfiesExpression(x)) x = x.expression;
    return ts.isPropertyAccessExpression(x) && ts.isPrivateIdentifier(x.name) && x.name.text === name;
  };
  /** Whether an assignment's target writes #name: the field itself, or a destructuring pattern holding it anywhere. */
  const targets = (e: ts.Node, name: string): boolean => {
    if (isPrivate(e, name)) return true;
    if (!ts.isObjectLiteralExpression(e) && !ts.isArrayLiteralExpression(e)) return false;
    let hit = false;
    const walk = (n: ts.Node): void => { if (isPrivate(n, name)) hit = true; ts.forEachChild(n, walk); };
    walk(e);
    return hit;
  };
  const out = { decls: 0, writes: [] as CardSite[], calls: [] as CardSite[], refs: [] as CardSite[], counts: [] as CardSite[], evals: [] as CardSite[], decorators: [] as CardSite[], callers: Object.fromEntries(callees.map((c) => [c, [] as string[]])) as Record<string, string[]>,
    calleeRefs: Object.fromEntries(callees.map((c) => [c, [] as CardSite[]])) as Record<string, CardSite[]> };
  const named = (name: string): boolean => Object.prototype.hasOwnProperty.call(out.callers, name);
  /** Whether the identifier is the callee a call of `callees` is counted by: the call's expression, or the name of the property
   *  access that is. */
  const countedCallee = (n: ts.Identifier): boolean =>
    (ts.isCallExpression(n.parent) && n.parent.expression === n)
    || (ts.isPropertyAccessExpression(n.parent) && n.parent.name === n && ts.isCallExpression(n.parent.parent) && n.parent.parent.expression === n.parent);
  /** Whether the identifier is the name a class member, a function or a signature is declared by. */
  const declaredName = (n: ts.Identifier): boolean => {
    const p = n.parent;
    return (ts.isMethodDeclaration(p) || ts.isFunctionDeclaration(p) || ts.isPropertyDeclaration(p) || ts.isGetAccessor(p) || ts.isSetAccessor(p) || ts.isMethodSignature(p) || ts.isPropertySignature(p)) && p.name === n;
  };
  /** A callee's mention, shown with what holds it (for a property's name, what holds the property access). */
  const mention = (n: ts.Node): CardSite => { const at = ts.isPropertyAccessExpression(n.parent) && n.parent.name === n ? n.parent : n; return { fn: fnName(n), line: lineOf(n), text: shown(at.parent) }; };
  /** The names of the doors to code in a string (evals), and the timers among them. */
  const DOORS = new Set(["eval", "Function", "constructor", "setTimeout", "setInterval"]);
  const TIMERS = new Set(["setTimeout", "setInterval"]);
  /** The private names whose declarations' decorators are listed (decorators): the state, its writer and the count the rule reads. */
  const STATE_NAMES = new Set(["#cardState", "#latchCardState", "#replaced"]);
  /** Whether the identifier stands in a type (`typeof setTimeout` in an annotation), where no code runs; an instantiation
   *  expression (`setTimeout<T>`) is a value, not a type. */
  const inType = (n: ts.Node): boolean => { for (let x = n.parent; x; x = x.parent) if (ts.isTypeNode(x) && !ts.isExpressionWithTypeArguments(x)) return true; return false; };
  /** Whether the identifier is a counted callee (as a call of `callees` is counted) of a call whose first argument, through
   *  parentheses, is a function written in place. */
  const givenFunction = (n: ts.Identifier): boolean => {
    if (!countedCallee(n)) return false;
    const call = (ts.isCallExpression(n.parent) ? n.parent : n.parent.parent) as ts.CallExpression;
    let a: ts.Node | undefined = call.arguments[0];
    while (a && ts.isParenthesizedExpression(a)) a = a.expression;
    return !!a && (ts.isArrowFunction(a) || ts.isFunctionExpression(a));
  };
  const door = (n: ts.Node): CardSite => ({ fn: fnName(n), line: lineOf(n), text: shown(n.parent) });
  /** An assignment: the binary expression's operator, its middle child, is one of the assignment operators. */
  const assigns = (n: ts.BinaryExpression): boolean => { const k = n.getChildAt(1, sf).kind; return k >= ts.SyntaxKind.FirstAssignment && k <= ts.SyntaxKind.LastAssignment; };
  /** An increment or a decrement: ++ or -- before the operand or after it. */
  const steps = (n: ts.PrefixUnaryExpression | ts.PostfixUnaryExpression): boolean => { const t = n.getText(sf).replace(/\s+/g, ""); return ts.isPrefixUnaryExpression(n) ? /^(\+\+|--)/.test(t) : /(\+\+|--)$/.test(t); };
  /** Whether `n` is an assignment whose target is the private field `name`. */
  const assignmentTo = (n: ts.Node, name: string): boolean =>
    (ts.isBinaryExpression(n) && assigns(n) && targets(n.left, name))
    || ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && steps(n) && isPrivate(n.operand, name))
    || ((ts.isForOfStatement(n) || ts.isForInStatement(n)) && targets(n.initializer, name));
  const site = (n: ts.Node): CardSite => ({ fn: fnName(n), line: lineOf(n), text: shown(ts.isForOfStatement(n) || ts.isForInStatement(n) ? n.initializer : n) });
  const visit = (n: ts.Node): void => {
    if ((ts.isPropertyDeclaration(n) || ts.isGetAccessor(n) || ts.isSetAccessor(n) || ts.isMethodDeclaration(n)) && ts.isPrivateIdentifier(n.name) && n.name.text === "#cardState") out.decls++;
    if (assignmentTo(n, "#cardState")) out.writes.push(site(n));
    if (assignmentTo(n, "#replaced")) out.counts.push(site(n));
    if (ts.isIdentifier(n) && DOORS.has(n.text) && !(TIMERS.has(n.text) && (inType(n) || givenFunction(n)))) out.evals.push(door(n));
    if (ts.isStringLiteralLike(n) && DOORS.has(n.text)) out.evals.push(door(n));
    if (ts.isCallExpression(n)) {
      const c = n.expression;
      const name = ts.isPropertyAccessExpression(c) ? c.name.text : ts.isIdentifier(c) ? c.text : null;
      if (name !== null && named(name)) out.callers[name].push(fnName(n));
    }
    if (ts.isIdentifier(n) && named(n.text) && !countedCallee(n) && !declaredName(n)) out.calleeRefs[n.text].push(mention(n));
    if (ts.isStringLiteralLike(n) && named(n.text)) out.calleeRefs[n.text].push(mention(n));
    if (ts.isDecorator(n)) {
      const nm = ts.getNameOfDeclaration((ts.isParameter(n.parent) ? n.parent.parent : n.parent) as ts.Declaration);
      if (nm && (ts.isIdentifier(nm) || ts.isStringLiteralLike(nm)) && named(nm.text)) out.calleeRefs[nm.text].push({ fn: fnName(n), line: lineOf(n), text: shown(n) });
      if (nm && ts.isPrivateIdentifier(nm) && STATE_NAMES.has(nm.text)) out.decorators.push({ fn: nm.text, line: lineOf(n), text: shown(n) });
    }
    if (ts.isPropertyAccessExpression(n) && ts.isPrivateIdentifier(n.name) && n.name.text === "#latchCardState") {
      const call = ts.isCallExpression(n.parent) && n.parent.expression === n ? n.parent : null;
      if (call) { const a = call.arguments[0]; out.calls.push({ fn: fnName(n), line: lineOf(n), text: shown(call), at: a && ts.isStringLiteralLike(a) ? a.text : "(not a literal)" }); }
      else out.refs.push({ fn: fnName(n), line: lineOf(n), text: shown(n.parent) });
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}
