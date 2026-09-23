// a plant's companion, not a test module: a .jsx with nothing else of its name beside it, the file the bundler loads for a specifier
// spelled ./bundler-order-jsx-alone (p389), which the census found no file for before it read the bundler's order from the build;
// it carries JSX and launches Firefox itself
const { firefox } = require("playwright");
exports.view = <div />;
exports.go = async function () { const b = await firefox.launch(); await b.close(); };
