// a helper that launches through its own playwright (a plant's companion, not a test module)
export async function launchIt(): Promise<any> { const pw = require("playwright"); return pw.chromium.launch(); }
