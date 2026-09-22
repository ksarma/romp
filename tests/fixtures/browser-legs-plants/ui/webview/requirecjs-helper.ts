// a helper that launches through the launcher's own requireCjs, reached as a member of the whole-module binding (a plant's
// companion, not a test module)
import * as leg from "./real-viewer-leg";
export async function launchIt(): Promise<any> { return leg.requireCjs("playwright").firefox.launch(); }
