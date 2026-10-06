// tests/lab_result.cjs: the one road a served driver's record takes to pytest (2026-10-06). The Python half is
// tests/lab_result.py; the two halves are pinned together by execution in tests/test_lab_result_pipe_served.py, and the
// reader's refusals in tests/test_lab_result.py.
//
// WHY. A served driver used to hand its record to pytest by printing it whole on stdout, many with one fs.writeSync(1,
// ...). Loading playwright leaves the process's stdout non-blocking, so one fs.writeSync to a pipe puts in what the pipe has
// room for and the rest is lost without a throw: up to 64 KiB, and 8 KiB on a loaded machine (a user past
// fs.pipe-user-pages-soft gets minimum-size pipes, pipe(7)). A record that grew past the room arrived cut, and how big a
// record may grow is a property of the tree, not of the driver. So no driver writes its record to stdout: the record goes
// to a file the Python side names, and stdout carries one short line naming that file.
//
// THE PROTOCOL, per drive (one node process):
//   1. Python mints the drive's target with lab_result.target(lab, name): {resultPath, resultNonce, resultLib}, a file
//      under the lab, a fresh random nonce, and this file's absolute path. It hands the target to the driver inside the
//      driver's cfg (cfg.update(target) before the cfg is written), or, for a driver that takes no cfg, in the
//      LAB_RESULT environment variable (lab_result.env(target)).
//   2. The driver calls writeResult(target, record) once, at the end of the drive or on the way out of a failed one.
//   3. Python calls lab_result.read(p, target) on the finished process and gets the record back, or a ResultError (an
//      AssertionError) that says what went wrong, with the tails of both streams.
//
// THE API (module.exports):
//   writeResult(target, record, opts)
//       target  the drive's target; a driver passes its whole cfg, since the cfg carries the three target keys. Only
//               target.resultPath and target.resultNonce are read.
//       record  any JSON value: an object, an array, a string. undefined, or a value JSON.stringify turns into nothing
//               (a function), is a write error, as is one it throws on (a BigInt, a cycle).
//       opts    optional {died}: the reason a failed drive stopped. Without it, record.died is used when the record is
//               an object, so the drivers' existing `writeResult(cfg, { ...out, died: why })` needs no opts.
//     Writes {"nonce": <target.resultNonce>, "record": <record>} to target.resultPath + ".tmp-<pid>" and renames it onto
//     target.resultPath, so the path holds a whole file or none. Then writes exactly one line to stdout:
//       RESULT:{"resultPath": ..., "nonce": ...[, "died": first 600 characters][, "resultWriteError": first 200]}
//     preceded by a line feed, so the line starts a line even after a partial line some other code left on stdout. Any
//     failure (no target, no path or nonce, a record that does not serialize, the write, the rename) becomes
//     resultWriteError on the line instead of a throw, and the reader reports it. The line is a few hundred bytes and
//     goes out through writeAll, which resumes after a partial write and waits out EAGAIN, so a full or non-blocking
//     pipe delays it but never cuts it. Returns the line's object. Call it once per process: the reader refuses a
//     stdout with two RESULT: lines. It does not exit or close anything; the driver does that after it, as before.
//   writeLine(tag, value)
//       A progress line that is not the record, for a value Python reads from stdout even after a failed drive (the
//       kernel pid lines, KPID:<pid>). tag matches /^[A-Z][A-Z0-9_]*$/ and is not RESULT; value is one line of at most
//       200 characters. Throws on anything else. Goes through writeAll too.
//   targetFromEnv()
//       The target from the LAB_RESULT environment variable, for a driver that takes no cfg (an argv driver). null when
//       the variable is unset, which writeResult reports as a write error.
//   writeAll(fd, text)
//       Every byte of text to fd, through a non-blocking pipe too. Exported for the pins; a driver has no use for it.
//   PREFIX
//       "RESULT:".
//
// LOADING IT. The file is CommonJS, so every driver loads it synchronously:
//   an inline driver (a text a test module writes into its lab and runs; it binds `require` with
//       createRequire(process.env.EXT_PKG) to load playwright, and that require takes an absolute path):
//         const lab = require(cfg.resultLib);
//   an ES module file under tests/:   import lab from "./lab_result.cjs";
//   a CommonJS file under tests/:     const lab = require("./lab_result.cjs");
//   a CommonJS text written into a lab and run with LAB_RESULT set:
//         const lab = require(JSON.parse(process.env.LAB_RESULT).resultLib);
//
// STALENESS. The nonce is minted per drive and must match three ways (the reader's mint, the line, the file), so a
// file an earlier drive left at the same path never passes for this drive's record, whatever the module deletes first.
//
// Never print the record, or anything else, to stdout by another road: console.log, process.stdout.write and
// fs.writeSync(1, ...) of a record are the cut this file exists to close. Diagnostics go to stderr (console.error).
"use strict";
const fs = require("fs");

const PREFIX = "RESULT:";
const DIED_MAX = 600;
const ERROR_MAX = 200;
const LINE_VALUE_MAX = 200;
const pause = new Int32Array(new SharedArrayBuffer(4));

// at most n characters of s, cut between code points, never inside a surrogate pair
function clip(s, n) {
  return Array.from(String(s)).slice(0, n).join("");
}

function writeAll(fd, text) {
  const buf = Buffer.from(text, "utf8");
  let off = 0;
  while (off < buf.length) {
    try {
      off += fs.writeSync(fd, buf, off, buf.length - off);
    } catch (e) {
      if (!e || e.code !== "EAGAIN") throw e;
      Atomics.wait(pause, 0, 0, 5);   // the pipe is full: wait for the reader to drain it, 5 ms at a time
    }
  }
}

function writeResult(target, record, opts) {
  const t = target && typeof target === "object" ? target : {};
  const line = {
    resultPath: typeof t.resultPath === "string" && t.resultPath ? t.resultPath : null,
    nonce: typeof t.resultNonce === "string" && t.resultNonce ? t.resultNonce : null,
  };
  const died = opts && typeof opts === "object" && "died" in opts ? opts.died
    : (record && typeof record === "object" && !Array.isArray(record) ? record.died : undefined);
  if (died !== undefined && died !== null) line.died = clip(died, DIED_MAX);
  let tmp = null;
  try {
    if (!line.resultPath || !line.nonce) throw new Error("the target names no resultPath or no resultNonce: hand writeResult the cfg that carries lab_result.target()");
    const body = record === undefined ? undefined : JSON.stringify(record);
    if (body === undefined) throw new Error("the record does not serialize to JSON (undefined or a function)");
    tmp = line.resultPath + ".tmp-" + process.pid;
    fs.writeFileSync(tmp, '{"nonce":' + JSON.stringify(line.nonce) + ',"record":' + body + "}");
    fs.renameSync(tmp, line.resultPath);
    tmp = null;
  } catch (e) {
    line.resultWriteError = clip((e && e.message) || e, ERROR_MAX);
    if (tmp) { try { fs.unlinkSync(tmp); } catch (_) { /* never written */ } }
  }
  writeAll(1, "\n" + PREFIX + JSON.stringify(line) + "\n");
  return line;
}

function writeLine(tag, value) {
  const v = String(value);
  if (typeof tag !== "string" || !/^[A-Z][A-Z0-9_]*$/.test(tag) || tag + ":" === PREFIX) {
    throw new Error("writeLine takes an upper-case tag other than RESULT, got " + JSON.stringify(tag));
  }
  if (v.length > LINE_VALUE_MAX || /[\r\n\u2028\u2029]/.test(v)) {
    throw new Error("writeLine takes one line of at most " + LINE_VALUE_MAX + " characters; the record goes through writeResult");
  }
  writeAll(1, tag + ":" + v + "\n");
}

function targetFromEnv() {
  const raw = process.env.LAB_RESULT;
  return raw ? JSON.parse(raw) : null;
}

module.exports = { writeResult, writeLine, targetFromEnv, writeAll, PREFIX };
