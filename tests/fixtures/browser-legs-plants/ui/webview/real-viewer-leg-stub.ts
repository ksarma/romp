// a module named like the launcher that is not it (a plant's companion, not a test module): an inBrowser that launches nothing (p323, p324)
export async function inBrowser(t: any, body: (b: any) => Promise<void>): Promise<void> { void t; await body({}); }
