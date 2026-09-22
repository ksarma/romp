// a helper that calls the launcher's inBrowser on an awaited import it never binds (a plant's companion, not a test module)
export async function run(t: any): Promise<void> { await (await import("./real-viewer-leg")).inBrowser(t, async () => {}); }
