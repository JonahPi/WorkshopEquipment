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

  // Initialize PocketBase synchronously so child pages can call getPb()
  // in their own onMount without a race condition on direct URL loads.
  if (browser && $auth) {
    initPb($auth.pbUrl, $auth.pbToken);
  }

  onMount(() => {
    const creds = $auth;
    const onSetup = $page.url.pathname.endsWith('/setup');

    if (!creds && !onSetup) {
      goto(`${base}/setup`);
    } else if (creds) {
      mqttStore.connect(creds.aioUsername, creds.aioKey);
    }
  });
</script>

<slot />
