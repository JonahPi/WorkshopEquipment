import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import type { Credentials } from '$lib/types';

function loadCredentials(): Credentials | null {
  if (!browser) return null;
  const pbUrl       = localStorage.getItem('pb_url');
  const pbToken     = localStorage.getItem('pb_token');
  const aioUsername = localStorage.getItem('aio_username');
  const aioKey      = localStorage.getItem('aio_key');
  if (pbUrl && pbToken && aioUsername && aioKey) {
    return { pbUrl, pbToken, aioUsername, aioKey };
  }
  return null;
}

function createAuthStore() {
  const { subscribe, set } = writable<Credentials | null>(loadCredentials());

  return {
    subscribe,
    save(creds: Credentials) {
      localStorage.setItem('pb_url',        creds.pbUrl);
      localStorage.setItem('pb_token',      creds.pbToken);
      localStorage.setItem('aio_username',  creds.aioUsername);
      localStorage.setItem('aio_key',       creds.aioKey);
      set(creds);
    },
    clear() {
      ['pb_url', 'pb_token', 'aio_username', 'aio_key'].forEach(k =>
        localStorage.removeItem(k)
      );
      set(null);
    },
  };
}

export const auth = createAuthStore();
export const isAuthenticated = derived(auth, $auth => $auth !== null);
