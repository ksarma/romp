// a UI helper that never touches the launcher and builds objects with a todo property (a plant's companion, not a test module)
export function rows(items: { id: string }[]): { todo: { id: string } }[] { const out: { todo: { id: string } }[] = []; for (const t of items) out.push({ todo: t }); return out; }
