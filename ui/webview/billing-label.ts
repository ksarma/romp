// The Billing label: what one session bills, in the words the chat tab's hover row and the tab menu's
// Billing item show. Pure and string-only, so the two surfaces cannot drift and every case runs as a test
// (billing-label.test.ts); the callers own their chrome.
//
// Two sources ride the status payload. `auth` is the INTENT: the pick when one was made (the picker, the
// gear, a remembered pick), else the default the kernel seeds for an unpicked session (the API key when
// Claude Code's settings carry an apiKeyHelper, else the side ROMP_EXPECTED_AUTH declares, else the
// login; romp holds no key of its own). `authLive` is the CLI's OWN
// report from its init, "" until one has landed. `authPicked` says which kind `auth` is.
//
// The CLI's report is the fact, so it leads whenever there is one. A pick the CLI contradicted deserves a
// warning: the user asked for one side and gets the other. A seeded default the CLI disagrees with is no
// contradiction, only a default that guessed wrong, so the report shows plainly. Until 2026-09-09 the
// row could not tell the two apart, and on a box whose sessions authenticate through Claude Code's
// apiKeyHelper every unpicked session read plain "Login": the seeded intent was the login (romp holds no
// key of its own there) and the kernel's live merge never forwarded the CLI's report, so the payload's
// authLive was "" (the user 2026-09-09). Had the report reached the row, the old wording would have shown
// "Login picked, but the CLI reports the API key" for a default nobody picked. No key material anywhere:
// the key is labelled 'API key'.
//
// Three more fields ride the payload since upstream's one-auth Billing picker (#1147, folded 2026-09-09):
// `authPickUnavailable` names an EXPLICIT pick this box cannot bill (the kernel's pick_unavailable: a login pick
// with no signed-in login or under a managed apiKeyHelper, a key pick with no helper; "" for an unpicked session
// or a pick the box can apply), `authPickFell` the side the launch billed instead (pick_fall, the launch's one
// decision), and `authAvail` which sides the box can bill with the kernel's reasons. A pick that fell outranks
// the contradiction reading: the kernel already says what happened, and the row repeats it in upstream's words,
// so the two trees agree on the copy.

export interface BillingFacts {
  auth?: string;          // "login" | "key" | "" (a tmux session reports nothing)
  authLive?: string;      // the CLI's own report: "login" | "key" | "" until an init lands
  authPicked?: boolean;   // `auth` is an explicit pick, not the seeded default
  authPending?: boolean;  // a switch's applying reconnect is in flight
  authAcct?: string;      // the login's display name, when known
  authPickUnavailable?: string;   // the explicit pick this box cannot bill: "login" | "key" | "" (kernel pick_unavailable)
  authPickFell?: string;          // the side the launch billed instead: "login" | "key" | ""; absent on an older kernel (kernel pick_fall)
  authAvail?: BillingAvail;       // which sides this box can bill, with the reasons (kernel auth_avail / _auth_avail)
  pickHeld?: { surfaces: string[] } | null;   // a pick waits for the session's live work before that reconnect
  //   (the status's one held marker, SdkSession.snapshot pickHeld; 2026-09-09): "auth" among the surfaces
  //   means the switch is not applying yet, and the CLI's last report still describes the running process
}

// The billing switch is HELD: picked, pending, and waiting for live work rather than applying.
export function billingHeld(f: BillingFacts): boolean {
  return !!(f.authPending && f.pickHeld && f.pickHeld.surfaces.includes("auth"));
}

// The plain label for one side, naming the login's account when known; "" for no side at all.
export function billingSide(side: string, acct?: string): string {
  if (!side) return "";
  return side === "key" ? "API key" : (acct ? `Login (${acct})` : "Login");
}

// The host kernel's availability reply for the new-session picker (the sessionList payload's authAvail).
export interface BillingAvail {
  login?: boolean;   // the credential store names a signed-in account
  key?: boolean;     // Claude Code's settings carry an apiKeyHelper (the kernel's key_available; romp holds no key)
  acct?: string;     // the login's display name, when known
  default?: string;  // what a session created now without an explicit pick would bill: "login" | "key"
  loginWhy?: string; // why the login side is unavailable, in the kernel's words (credentials.WHY_*); absent when it is available
  keyWhy?: string;   // the same for the key side
}

// The side a written-out row names: the kernel's `default`, exactly what a spawn without a pick bills (new_session_auth);
// a remembered login pick on a keyed box seeds the login into the created session, so the helper's key is not the
// answer there; the key arm serves only a reply carrying no default.
function pickerKeyed(a: BillingAvail): boolean { return a.default ? a.default === "key" : !!a.key; }

// The picker's Billing row, from that reply: whether the row has anything to say, whether it offers BUTTONS
// (both choices real) and, when not, the single applying choice written out (the user 2026-08-09:
// informative, never a one-option selector). The row shows whenever the host can name what a new session
// bills: a login, a helper's key, or a DECLARED key (`default` reads "key" under ROMP_EXPECTED_AUTH=key
// on a box whose settings carry no helper, where the kernel sees neither credential). Until 2026-09-09 the
// gate required a login or a key, so on that box, the one the fix is for, the row was absent while the created
// session's hover said "API key" (review round 1). With none of the three the row stays hidden rather
// than writing out a "Login" nobody can vouch for (the CLI would refuse at init).
export function pickerBillingRow(a: BillingAvail | null | undefined): { show: boolean; both: boolean; fixed: string } {
  const show = !!(a && (a.login || a.key || a.default === "key"));
  const both = !!(a && a.login && a.key);
  const keyed = !!a && pickerKeyed(a);   // the written-out choice follows the kernel's default (pickerKeyed)
  const fixed = !show || both ? "" : (keyed ? "API key" : billingSide("login", a!.acct));
  return { show, both, fixed };
}

// The written-out row's hover: why the OTHER side is not on offer, in the kernel's reason (upstream #1147, the
// user 2026-09-08), keyed as upstream keys it, on whether the box's settings carry an apiKeyHelper: with one the
// login side is explained, without one the key side. "" when the row is hidden or offers buttons. On a box that
// declares the key (ROMP_EXPECTED_AUTH=key) with no helper the row writes out the declared side and this hover
// says no helper is configured: two facts of the kernel's side by side, rendered as upstream renders that reply
// (the 2026-09-09 fold, slice 3: the resolve's "" for a login beside a declared key was a departure no fork test
// had pinned, so upstream's behaviour stands).
export function pickerBillingTitle(a: BillingAvail | null | undefined): string {
  const row = pickerBillingRow(a);
  if (!row.show || row.both) return "";
  return a!.key ? `Login unavailable: ${a!.loginWhy || "no Claude login signed in on this machine"}`
                : `API key unavailable: ${a!.keyWhy || "no apiKeyHelper configured"}`;
}

// The explicit pick this box cannot bill, when the status names one: the kernel's word (authPickUnavailable),
// never inferred here from the availability alone.
export function billingPickUnavailable(f: BillingFacts): boolean {
  return !!(f.auth && f.authPickUnavailable === f.auth);
}

// The side a pick this box cannot bill actually fell to ("login" | "key"), "" when nothing did: the kernel's
// authPickFell (the launch's own decision, 2026-09-09). An older kernel without the field is read the way the
// Billing sub-line always inferred it: the pick is unavailable and the other side exists.
export function billingFellTo(f: BillingFacts): string {
  if (f.authPickFell !== undefined) return f.authPickFell || "";
  if (!billingPickUnavailable(f)) return "";
  const other = f.auth === "key" ? "login" : "key";
  const avail: BillingAvail = f.authAvail || { login: true, key: true };
  return avail[other] ? other : "";
}

// Why the picked side cannot be billed, in the kernel's words (authAvail's reason for that side), else the generic.
function unavailableWhy(f: BillingFacts): string {
  return (f.auth === "key" ? f.authAvail?.keyWhy : f.authAvail?.loginWhy) || "this machine cannot bill it";
}

// The sub-line's word for a side (upstream's wordOf): the key by its plain label, the login in lower case.
const wordOf = (side: string): string => (side === "key" ? "API key" : "login");

// Whether there is a contradiction to warn about: an explicit pick the CLI's own report disagrees with.
export function billingContradicted(f: BillingFacts): boolean {
  return !!(f.authPicked && f.auth && f.authLive && f.authLive !== f.auth);
}

// The tab hover's Billing row. A pending pick says so first (the reconnect window is never shown as
// applied fact); a pick this box cannot bill says so next, naming the side the launch went to, in upstream's
// words (the user 2026-09-08; review 2026-09-09: the fall is the kernel's word, never inferred from the pick
// alone, since a box with neither side launches as picked and the CLI decides); a contradicted pick leads
// with the warning and names what is billed; otherwise the CLI's reported side, falling back to the intent
// before any report has landed.
export function billingRowText(f: BillingFacts): string {
  if (billingHeld(f)) {
    // the running side leads when the CLI reported one (the report still describes the running process:
    // the kernel keeps it through the hold and clears it at the arm); the pick is named as what waits
    const now = billingSide(f.authLive || "", f.authAcct), then = billingSide(f.auth || "", f.authAcct);
    return now ? `${now} until the background work finishes, then ${then}`
      : `${then} applies when the background work finishes`;
  }
  if (f.authPending) return billingSide(f.auth || "") + " (applying, not confirmed yet)";
  if (billingPickUnavailable(f)) {
    const fell = billingFellTo(f);
    return `⚠ ${billingSide(f.auth || "")} picked, but ${unavailableWhy(f)}`
      + (fell ? ` — this session bills ${fell === "key" ? "the API key" : "the login"}`
              : " — nothing to fall to, so the launch went out as picked");
  }
  if (billingContradicted(f)) {
    return `⚠ ${billingSide(f.auth || "")} picked, but the CLI reports `
      + `${f.authLive === "key" ? "the API key" : "the login"}; this session bills that`;
  }
  return billingSide(f.authLive || f.auth || "", f.authAcct);
}

// The tab menu's Billing item sub-line: the same decision in fewer words, since the switch is one click
// away and the row is a control's caption.
export function billingSubText(f: BillingFacts): string {
  if (billingHeld(f)) return "waiting for background work";
  if (f.authPending) return "applying…";
  if (billingPickUnavailable(f)) {   // the pick names a side this box cannot bill: the launch went to the other one when it exists
    const fell = billingFellTo(f);
    return `⚠ ${wordOf(f.auth || "")} unavailable` + (fell ? `, billing ${wordOf(fell)}` : "");
  }
  if (billingContradicted(f)) return `⚠ CLI reports ${f.authLive === "key" ? "API key" : "login"}`;
  return billingSide(f.authLive || f.auth || "", f.authAcct);
}
