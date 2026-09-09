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
// apiKeyHelper every session read "Login picked, but the CLI reports the API key" when nobody had picked
// anything (the user 2026-09-09). No key material anywhere: the key is labelled 'API key'.

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
