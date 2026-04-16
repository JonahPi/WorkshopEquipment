<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth';

  onMount(() => {
    goto($auth ? `${base}/gallery` : `${base}/setup`, { replaceState: true });
  });
</script>
