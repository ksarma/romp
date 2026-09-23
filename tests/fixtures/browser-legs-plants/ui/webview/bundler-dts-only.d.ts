// a plant's companion, not a test module: a declaration file with no .js, .ts or .tsx beside it, which the bundler never loads, so
// a specifier spelled ./bundler-dts-only.js names no file it can bundle (p375)
export declare function go(): Promise<void>;
