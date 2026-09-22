import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p116", (t) => { const tail = [async () => {}, "webkit"] as const; return (inBrowser as any)(t, ...tail); });
