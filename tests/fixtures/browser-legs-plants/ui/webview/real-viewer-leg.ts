import { createRequire } from "node:module";
export const requireCjs = createRequire(process.cwd() + "/package.json");
export async function inBrowser(t: any, body: (b: any) => Promise<void>): Promise<void> { void t; void body; }
export function pageHtml(): string { return ""; }
export type Opened = { page: any };
