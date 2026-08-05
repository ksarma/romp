// update-target — WHERE the one-click self-update runs, decided LOCALLY and never off the wire.
//
// updateExtension() shells out to `bash <dir>/install.sh`, so <dir> is an EXECUTION target and may
// only come from something we already trust: this VSIX's own installed location
// (context.extensionPath) or ROMP_DIR out of the extension host's own environment — both set by
// whoever launched VS Code, i.e. the user. It used to come from `rompDir` on the kernel's /version,
// which is the wrong kind of source: /version is auth-exempt, so anything answering on the kernel
// port (a local process that grabbed it before the real kernel, say) got to name the directory a
// shell command ran from — and that same listener's keepalive `dv` raises the "newer build" prompt
// that invites the click. A path that arrives over a socket is not a path to run.
//
// A candidate must look like a romp CHECKOUT, not merely a directory holding an install.sh: the
// packaged VSIX ships install.sh but not esbuild.js (.vscodeignore drops the build inputs), and that
// copy can't rebuild anything. Requiring BOTH markers is what separates "running from a checkout" —
// where the update genuinely works — from "installed from a .vsix", which resolves to nothing so the
// caller can say so plainly and point at the terminal (fail loudly, don't degrade).
import * as path from "path";

// Present together only in a real vscode-extension/ source dir: install.sh does the build+package,
// esbuild.js is the build it invokes. A packaged install carries the first without the second.
export const CHECKOUT_MARKERS = ["install.sh", "esbuild.js"];

export interface InstallTarget {
  dir: string;      // the vscode-extension/ dir to run in (install.sh cd's here itself)
  script: string;   // <dir>/install.sh
}

// The dirs worth probing, best first. Both are this host's own knowledge of itself; nothing here
// consults the kernel.
export function installCandidates(extensionPath: string, rompDirEnv?: string): string[] {
  const out: string[] = [];
  const ext = (extensionPath || "").trim();
  if (ext) out.push(ext);                                        // run from a checkout: the extension dir IS vscode-extension/
  const repo = (rompDirEnv || "").trim();
  if (repo) out.push(path.join(repo, "vscode-extension"));       // a host launched from a romp shell/service knows the repo
  return out;
}

// The first candidate that is a romp checkout, or null when this copy can't rebuild itself.
export function resolveInstallScript(
  extensionPath: string,
  rompDirEnv: string | undefined,
  exists: (p: string) => boolean,
): InstallTarget | null {
  for (const dir of installCandidates(extensionPath, rompDirEnv)) {
    if (CHECKOUT_MARKERS.every((m) => exists(path.join(dir, m)))) {
      return { dir, script: path.join(dir, "install.sh") };
    }
  }
  return null;
}
