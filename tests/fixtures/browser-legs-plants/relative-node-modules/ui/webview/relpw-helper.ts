// a helper that imports playwright by a relative path into node_modules (a plant's companion, not a test module)
import { firefox } from "../../vscode-extension/node_modules/playwright";
export async function open(): Promise<any> { return firefox.launch(); }
