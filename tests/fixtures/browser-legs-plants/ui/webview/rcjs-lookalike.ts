// a helper exporting a function named like the launcher's loader that never touches the launcher (a plant's companion, not a test module)
export function requireCjs(spec: string): any { return spec; }
