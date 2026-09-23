// a module named like the launcher at the plants' root, beside a same-named one under vscode-extension/ (a plant's companion, not a test module): the two bases name two files (p329)
export async function inBrowser(t: any, body: (b: any) => Promise<void>): Promise<void> { void t; await body({}); }
