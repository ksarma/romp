// Synthetic image bytes for the host-script tests: a valid 2x2 RGBA PNG built from bytes at run
// time (signature, IHDR, one deflated IDAT, IEND, each chunk with its CRC), so no picture is ever
// committed and two colors give two different files — "the figure was regenerated" is a second
// call with other channel values. Also the sha256 the tests compare the host's hashes against.
import { createHash } from 'node:crypto';
import zlib from 'node:zlib';

function crc32(buf) {
  let crc = 0xffffffff;
  for (const b of buf) {
    crc ^= b;
    for (let k = 0; k < 8; k++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const body = Buffer.concat([Buffer.from(type, 'latin1'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body), 0);
  return Buffer.concat([len, body, crc]);
}

// A 2x2 PNG whose four pixels are the color (r, g, b), opaque.
export function tinyPng(r, g, b) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(2, 0);   // width
  ihdr.writeUInt32BE(2, 4);   // height
  ihdr[8] = 8;                // bit depth
  ihdr[9] = 6;                // color type: RGBA
  ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;   // compression, filter, interlace
  const row = Buffer.from([0, r, g, b, 255, r, g, b, 255]);   // filter byte 0, then two pixels
  const raw = Buffer.concat([row, row]);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

export function sha256(buf) {
  return createHash('sha256').update(buf).digest('hex');
}
