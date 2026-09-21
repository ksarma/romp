import { test } from 'node:test';
const pw = require('playwright');
test('p2', async () => { const b = await pw.chromium.launch(); await b.close(); });
