// a helper whose shared call hands its rejection to .catch (a plant's companion, not a test module): the swallow folds into the importer's record at the import line
import { inBrowser } from "./real-viewer-leg";
export async function safe(t: any): Promise<void> { await inBrowser(t, async () => {}).catch(() => {}); }
