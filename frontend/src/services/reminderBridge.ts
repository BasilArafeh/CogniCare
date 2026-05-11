let _pendingMessage: string | null = null;

export function setPendingReminder(message: string) {
  _pendingMessage = message;
}

export function consumePendingReminder(): string | null {
  const msg = _pendingMessage;
  _pendingMessage = null;
  return msg;
}
