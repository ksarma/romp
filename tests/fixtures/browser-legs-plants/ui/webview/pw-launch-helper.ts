// a helper that launches whatever playwright it is handed (a plant's companion, not a test module; names no package itself)
export async function launchWith(p: any): Promise<void> { const b = await p.webkit.launch(); await b.close(); }
