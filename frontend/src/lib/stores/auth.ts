import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import type { Credentials } from '$lib/types';

function loadCredentials(): Credentials | null {
  if (!browser) return null;
  const pbUrl        = localStorage.getItem('pb_url');
  const pbToken      = localStorage.getItem('pb_token') ?? '';
  const pbEmail      = localStorage.getItem('pb_email') ?? '';
  const pbPassword   = localStorage.getItem('pb_password') ?? '';
  const aioUsername  = localStorage.getItem('aio_username');
  const aioKey       = localStorage.getItem('aio_key');
  const anthropicKey = localStorage.getItem('anthropic_key') ?? '';
  if (pbUrl && (pbToken || pbEmail) && aioUsername && aioKey) {
    return { pbUrl, pbToken, pbEmail, pbPassword, aioUsername, aioKey, anthropicKey };
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
      localStorage.setItem('pb_email',      creds.pbEmail);
      localStorage.setItem('pb_password',   creds.pbPassword);
      localStorage.setItem('aio_username',  creds.aioUsername);
      localStorage.setItem('aio_key',       creds.aioKey);
      localStorage.setItem('anthropic_key', creds.anthropicKey);
      set(creds);
    },
    updateToken(token: string) {
      localStorage.setItem('pb_token', token);
    },
    clear() {
      ['pb_url', 'pb_token', 'pb_email', 'pb_password', 'aio_username', 'aio_key', 'anthropic_key'].forEach(k =>
        localStorage.removeItem(k)
      );
      set(null);
    },
  };
}

export const auth = createAuthStore();
export const isAuthenticated = derived(auth, $auth => $auth !== null);
