// a plant's companion, not a test module: the .jsx beside bundler-order-jsx.js, the file the bundler loads for a specifier spelled
// ./bundler-order-jsx, since the test build's suffix list tries .jsx before .js (p388); it carries JSX and launches Firefox itself
const { firefox } = require("playwright");
exports.view = <div />;
exports.go = async function () { const b = await firefox.launch(); await b.close(); };
