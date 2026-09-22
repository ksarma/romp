// a helper that hands the launcher's load to a promise callback (a plant's companion, not a test module)
export function run(t: any): Promise<void> { return import("./real-viewer-leg").then((m) => m.inBrowser(t, async () => {})); }
