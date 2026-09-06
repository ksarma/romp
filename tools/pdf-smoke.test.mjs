// The PDF rendering dependency's smoke test (plans/file-review.md, Slice 4): pdfjs-dist, as installed
// under vscode-extension/node_modules, opens a PDF and reports its pages. The fixture is written HERE as
// bytes (two blank pages, a hand-built cross-reference table), never a real document: the repo may go
// public and a PDF is recorded data like any other. The legacy build is imported because it is the one
// pdf.js supports under Node: it runs its parser on the main thread from a worker file beside it, so
// nothing is configured and no canvas library is needed for the page count and the viewport.
//
// Skips, by name, when the dependency is not installed: CI's shell job runs tools/*.test.mjs without an
// npm ci, so the assertion runs in the vscode-extension job (which installs) and skips in the shell job,
// and the skip line says which install would make it run. A developer without node_modules sees the same.
//
// Run: node --test tools/pdf-smoke.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PKG_DIR = path.resolve(HERE, '..', 'vscode-extension', 'node_modules', 'pdfjs-dist');
const LEGACY = path.join(PKG_DIR, 'legacy', 'build', 'pdf.mjs');
const SKIP = fs.existsSync(LEGACY)
  ? false
  : 'pdfjs-dist is not installed under vscode-extension/node_modules (run `npm ci` in vscode-extension); the PDF smoke test did not run';

/** A minimal, valid PDF: `pageCount` blank pages on one MediaBox, with a correct xref table (pdf.js
 *  would reconstruct a broken one, which is exactly what this fixture must not lean on). */
export function minimalPdf(pageCount, mediaBox = [0, 0, 612, 792]) {
  const objs = ['<< /Type /Catalog /Pages 2 0 R >>'];
  const kids = Array.from({ length: pageCount }, (_, i) => `${3 + i} 0 R`).join(' ');
  objs.push(`<< /Type /Pages /Kids [${kids}] /Count ${pageCount} >>`);
  for (let i = 0; i < pageCount; i++) objs.push(`<< /Type /Page /Parent 2 0 R /MediaBox [${mediaBox.join(' ')}] >>`);
  let out = '%PDF-1.4\n';
  const offsets = [];
  objs.forEach((body, i) => {
    offsets.push(Buffer.byteLength(out, 'latin1'));
    out += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = Buffer.byteLength(out, 'latin1');
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;          // each entry exactly 20 bytes
  for (const o of offsets) out += `${String(o).padStart(10, '0')} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return new Uint8Array(Buffer.from(out, 'latin1'));
}

test('pdfjs-dist opens a two-page synthetic PDF: two pages, each with a positive viewport', { skip: SKIP }, async () => {
  const pdfjs = await import(pathToFileURL(LEGACY).href);
  const task = pdfjs.getDocument({ data: minimalPdf(2) });
  const doc = await task.promise;
  try {
    assert.equal(doc.numPages, 2);
    const page = await doc.getPage(1);
    const vp = page.getViewport({ scale: 1 });
    assert.ok(vp.width > 0 && vp.height > 0, `viewport ${vp.width}x${vp.height}`);
    assert.equal(vp.width, 612, 'a US-letter MediaBox is 612 points wide at scale 1');
    assert.equal(vp.height, 792);
    // the width-fit scale the chunk computes (root width over natural width) lands on the root's width
    const fit = page.getViewport({ scale: 800 / vp.width });
    assert.equal(Math.round(fit.width), 800);
    assert.equal(Math.round(fit.height), Math.round(792 * 800 / 612));
    const last = await doc.getPage(2);
    assert.equal(last.getViewport({ scale: 1 }).height, 792, 'the second page is a page too');
  } finally {
    await task.destroy();      // pdf.js 6: destroy lives on the loading task, not the document proxy
  }
});

test('the installed pdfjs-dist is the 6.x line, Apache-2.0, and ships the worker the esbuild entry names', { skip: SKIP }, () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(PKG_DIR, 'package.json'), 'utf8'));
  assert.match(pkg.version, /^6\./, 'the chunk is written against pdf.js 6');
  assert.equal(pkg.license, 'Apache-2.0', 'the license docs/install.md names');
  assert.ok(fs.existsSync(path.join(PKG_DIR, 'build', 'pdf.worker.mjs')), 'vscode-extension/esbuild.js bundles this file as dist/pdf-worker.js');
});

test('the fixture is a well-formed PDF on its own terms: header, one xref entry per object, offsets that land on their objects', () => {
  const text = Buffer.from(minimalPdf(2)).toString('latin1');
  assert.match(text, /^%PDF-1\.4\n/);
  assert.match(text, /\/Count 2 >>/);
  const start = Number(text.match(/startxref\n(\d+)\n%%EOF\n$/)[1]);
  assert.equal(text.slice(start, start + 4), 'xref', 'startxref names the byte where the table begins');
  const table = text.slice(start);
  assert.equal(table.match(/^\d{10} \d{5} [nf] $/gm).length, 5, 'the free entry plus catalog, pages and two page objects');
  let obj = 0;
  for (const m of table.matchAll(/^(\d{10}) 00000 n \n/gm)) {
    obj += 1;
    const off = Number(m[1]);
    assert.equal(text.slice(off, off + `${obj} 0 obj`.length), `${obj} 0 obj`, `xref entry ${obj} points at its object`);
  }
  assert.equal(obj, 4);
});
