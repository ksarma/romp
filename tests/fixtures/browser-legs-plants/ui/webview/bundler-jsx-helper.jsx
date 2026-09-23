// a plant's companion, not a test module: a .jsx a test loads by its own spelling (p374); it carries JSX and launches Firefox itself
const { firefox } = require("playwright");
exports.view = <div />;
exports.go = async function () { const b = await firefox.launch(); await b.close(); };
