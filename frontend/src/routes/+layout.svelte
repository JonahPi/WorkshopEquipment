<script lang="ts">
  import '../app.css';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { auth } from '$lib/stores/auth';
  import { initPb } from '$lib/pb';
  import { mqttStore } from '$lib/stores/mqtt';
  import PocketBase from 'pocketbase';

  if (browser && $auth) {
    initPb($auth.pbUrl, $auth.pbToken);
  }

  onMount(async () => {
    const creds = $auth;
    const onSetup = $page.url.pathname.endsWith('/setup');

    if (!creds && !onSetup) {
      goto(`${base}/setup`);
      return;
    }

    if (creds) {
      // Try to refresh the existing token; fall back to re-auth with stored password.
      try {
        const pb = new PocketBase(creds.pbUrl);
        pb.authStore.save(creds.pbToken, null);
        try {
          const result = await pb.collection('_superusers').authRefresh();
          auth.updateToken(result.token);
          initPb(creds.pbUrl, result.token);
        } catch {
          if (creds.pbEmail && creds.pbPassword) {
            const result = await pb.collection('_superusers').authWithPassword(creds.pbEmail, creds.pbPassword);
            auth.updateToken(result.token);
            initPb(creds.pbUrl, result.token);
          } else {
            auth.clear();
            goto(`${base}/setup`);
            return;
          }
        }
      } catch {
        auth.clear();
        goto(`${base}/setup`);
        return;
      }

      mqttStore.connect(creds.aioUsername, creds.aioKey);
    }
  });
</script>

<slot />
