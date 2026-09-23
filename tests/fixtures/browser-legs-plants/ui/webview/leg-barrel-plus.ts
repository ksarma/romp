// a barrel that re-exports inBrowser AND exports something else of its own (a plant's companion, not a test module)
export { inBrowser } from "./real-viewer-leg";
export function helper(): void {}
