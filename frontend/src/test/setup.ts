import { beforeEach } from 'vitest';

// Each test starts a separate tab navigation context. Tests can still unmount /
// remount App within one case to exercise actual sessionStorage restoration.
beforeEach(() => {
  window.sessionStorage.clear();
  window.history.replaceState(null, '');
});
