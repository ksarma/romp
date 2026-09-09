// The Billing label: what one session bills, in the words the chat tab's hover row and the tab menu's
// Billing item show. Pure and string-only, so the two surfaces cannot drift and every case runs as a test
// (billing-label.test.ts); the callers own their chrome.
//
// Two sources ride the status payload. `auth` is the INTENT: the pick when one was made (the picker, the
// gear, a remembered pick), else the default the kernel seeds for an unpicked session (the key romp holds
// to inject, else the side ROMP_EXPECTED_AUTH declares, else the login). `authLive` is the CLI's OWN
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

export interface BillingFacts {
  auth?: string;          // "login" | "key" | "" (a tmux session reports nothing)
  authLive?: string;      // the CLI's own report: "login" | "key" | "" until an init lands
  authPicked?: boolean;   // `auth` is an explicit pick, not the seeded default
  authPending?: boolean;  // a switch's applying reconnect is in flight
  authAcct?: string;      // the login's display name, when known
}

// The plain label for one side, naming the login's account when known; "" for no side at all.
export function billingSide(side: string, acct?: string): string {
  if (!side) return "";
  return side === "key" ? "API key" : (acct ? `Login (${acct})` : "Login");
}

// The host kernel's availability reply for the new-session picker (the sessionList payload's authAvail).
export interface BillingAvail {
  login?: boolean;   // the credential store names a signed-in account
  key?: boolean;     // romp holds a key source of its own
  acct?: string;     // the login's display name, when known
  default?: string;  // what a session created now without an explicit pick would bill: "login" | "key"
}

// The picker's Billing row, from that reply: whether the row has anything to say, whether it offers BUTTONS
// (both choices real) and, when not, the single applying choice written out (the user 2026-08-09:
// informative, never a one-option selector). The row shows whenever the host can name what a new session
// bills: a login, a key of romp's, or a DECLARED key (`default` reads "key" under ROMP_EXPECTED_AUTH=key
// on an apiKeyHelper box, which holds neither credential of romp's). Until 2026-09-09 the gate required a
// login or a key of romp's, so on that box, the one the fix is for, the row was absent while the created
// session's hover said "API key" (review round 1). With none of the three the row stays hidden rather
// than writing out a "Login" nobody can vouch for (the CLI would refuse at init).
export function pickerBillingRow(a: BillingAvail | null | undefined): { show: boolean; both: boolean; fixed: string } {
  const show = !!(a && (a.login || a.key || a.default === "key"));
  const both = !!(a && a.login && a.key);
  const fixed = !show || both ? "" : ((a!.key || a!.default === "key") ? "API key" : billingSide("login", a!.acct));
  return { show, both, fixed };
}

// Whether there is a contradiction to warn about: an explicit pick the CLI's own report disagrees with.
export function billingContradicted(f: BillingFacts): boolean {
  return !!(f.authPicked && f.auth && f.authLive && f.authLive !== f.auth);
}

// The tab hover's Billing row. A pending pick says so first (the reconnect window is never shown as
// applied fact); a contradicted pick leads with the warning and names what is billed; otherwise the
// CLI's reported side, falling back to the intent before any report has landed.
export function billingRowText(f: BillingFacts): string {
  if (f.authPending) return billingSide(f.auth || "") + " (applying, not confirmed yet)";
  if (billingContradicted(f)) {
    return `⚠ ${billingSide(f.auth || "")} picked, but the CLI reports `
      + `${f.authLive === "key" ? "the API key" : "the login"}; this session bills that`;
  }
  return billingSide(f.authLive || f.auth || "", f.authAcct);
}

// The tab menu's Billing item sub-line: the same decision in fewer words, since the switch is one click
// away and the row is a control's caption.
export function billingSubText(f: BillingFacts): string {
  if (f.authPending) return "applying…";
  if (billingContradicted(f)) return `⚠ CLI reports ${f.authLive === "key" ? "API key" : "login"}`;
  return billingSide(f.authLive || f.auth || "", f.authAcct);
}
