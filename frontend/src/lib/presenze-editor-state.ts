/** An already closed editor stays closed when an earlier input event is applied. */
export function patchPresenzeEditor<T>(current: T | null, changes: Partial<T>): T | null {
  return current === null ? null : { ...current, ...changes };
}
