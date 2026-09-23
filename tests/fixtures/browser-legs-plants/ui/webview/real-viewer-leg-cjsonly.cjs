// a CommonJS module named like the launcher with no .ts beside it (a plant's companion, not a test module): an inBrowser that launches nothing (p325)
exports.inBrowser = async function (t, body) { void t; await body({}); };
