// a helper that reaches Firefox through the shared launcher (a plant's companion, not a test module)
import { inBrowser } from "./real-viewer-leg";
export const inFirefox = (t: any, body: (b: any) => Promise<void>): Promise<void> => inBrowser(t, body, "firefox" as any);
