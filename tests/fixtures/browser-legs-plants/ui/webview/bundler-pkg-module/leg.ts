// a plant's companion, not a test module: the file the package.json beside it names as its module, which the bundler loads for an
// import statement spelled ./bundler-pkg-module before the directory's index (p395); it launches Firefox itself
import { firefox } from "playwright";
export async function go(): Promise<void> { const b = await firefox.launch(); await b.close(); }
