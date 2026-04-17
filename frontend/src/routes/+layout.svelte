<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { auth } from '$lib/stores/auth';
  import { initPb } from '$lib/pb';
  import { mqttStore } from '$lib/stores/mqtt';

  onMount(() => {
    const creds = $auth;
    const onSetup = $page.url.pathname.endsWith('/setup');

    if (!creds && !onSetup) {
      goto(`${base}/setup`);
    } else if (creds) {
      initPb(creds.pbUrl, creds.pbToken);
      mqttStore.connect(creds.aioUsername, creds.aioKey);
    }
  });
</script>

<slot />
