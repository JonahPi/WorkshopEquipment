<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { Html5Qrcode } from 'html5-qrcode';

  const dispatch = createEventDispatcher<{ scan: number; cancel: void }>();

  let scanner: Html5Qrcode | null = null;
  let error = '';

  // Extract box_nr from:
  //   New PWA URL  …/item/42
  //   Legacy URL   …?b=42
  //   Plain number 42
  function extractBoxNr(text: string): number | null {
    const itemMatch = text.match(/\/item\/(\d+)/);
    if (itemMatch) return parseInt(itemMatch[1]);

    try {
      const url = new URL(text);
      const b = url.searchParams.get('b');
      if (b && /^\d+$/.test(b)) return parseInt(b);
    } catch {}

    if (/^\d+$/.test(text.trim())) return parseInt(text.trim());

    return null;
  }

  onMount(async () => {
    scanner = new Html5Qrcode('qr-reader');
    try {
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (decodedText) => {
          const boxNr = extractBoxNr(decodedText);
          if (boxNr !== null) {
            scanner!.stop().catch(() => {});
            dispatch('scan', boxNr);
          } else {
            error = `Unrecognised QR content: ${decodedText}`;
          }
        },
        undefined
      );
    } catch (e: unknown) {
      error = `Camera unavailable — ${e}`;
    }
  });

  onDestroy(async () => {
    if (scanner?.isScanning) {
      await scanner.stop().catch(() => {});
    }
  });

  async function cancel() {
    if (scanner?.isScanning) {
      await scanner.stop().catch(() => {});
    }
    dispatch('cancel');
  }
</script>

<!-- Full-screen overlay -->
<div class="fixed inset-0 bg-black z-50 flex flex-col">

  <!-- Viewfinder -->
  <div class="flex-1 relative flex items-center justify-center">
    <div id="qr-reader" class="w-full h-full" />

    {#if error}
      <div class="absolute bottom-8 left-4 right-4 bg-black/70 text-red-400 text-sm text-center rounded-xl px-4 py-3">
        {error}
      </div>
    {:else}
      <div class="absolute bottom-8 left-4 right-4 text-white/60 text-sm text-center">
        Point camera at QR code on the box label
      </div>
    {/if}
  </div>

  <!-- Cancel -->
  <div class="pb-safe px-6 py-4 flex justify-center">
    <button
      on:click={cancel}
      class="px-8 py-3 rounded-full bg-white/20 text-white text-sm font-medium active:bg-white/30"
    >
      Cancel
    </button>
  </div>

</div>
