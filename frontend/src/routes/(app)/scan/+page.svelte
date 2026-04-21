<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import QRScanner from '$lib/components/QRScanner.svelte';

  function onScan(e: CustomEvent<number>) {
    goto(`${base}/item/${e.detail}`);
  }

  function onCancel() {
    goto(`${base}/gallery`);
  }
</script>

<svelte:head><title>Workshop — Scan</title></svelte:head>

<QRScanner on:scan={onScan} on:cancel={onCancel} />
