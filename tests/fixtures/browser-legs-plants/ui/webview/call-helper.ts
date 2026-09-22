// a helper that calls the launcher's inBrowser on a load it never binds (a plant's companion, not a test module)
export async function run(t: any): Promise<void> { await require("./real-viewer-leg").inBrowser(t, async () => {}); }
