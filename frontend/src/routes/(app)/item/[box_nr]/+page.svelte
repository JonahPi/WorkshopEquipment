<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { getPb } from '$lib/pb';
  import { auth } from '$lib/stores/auth';
  import { mqttStore } from '$lib/stores/mqtt';
  const mqttStatus = mqttStore.status;
  import type { Item } from '$lib/types';
  import { TYP_COLOURS } from '$lib/types';

  let item: Item | null = null;
  let loading = true;
  let error = '';
  let deleting = false;
  let confirmDelete = false;

  let actionMsg = '';
  let actionError = '';

  const BASE_URL = 'https://jonahpi.github.io/WorkshopEquipment';
  const STEPPER_RE = /^\d+\/\d+$/;

  function mqttTopic(feed: string): string {
    return `${$auth?.aioUsername ?? ''}/feeds/${feed}`;
  }

  function wordWrap(text: string, maxLen = 40): string {
    const words = (text ?? '').split(' ');
    const lines: string[] = [];
    let current = '';
    for (const word of words) {
      if (current.length === 0) {
        current = word;
      } else if (current.length + 1 + word.length <= maxLen) {
        current += ' ' + word;
      } else {
        lines.push(current);
        current = word;
      }
    }
    if (current) lines.push(current);
    return lines.join('\n');
  }

  async function printLabel(labelType: 'material' | 'materialgross') {
    if (!item) return;
    actionMsg = ''; actionError = '';
    const qr_content = `${BASE_URL}/item/${item.box_nr}`;
    const payload = JSON.stringify({
      label_type: labelType,
      data: { box_nr: item.box_nr, qr_content, inhalt: wordWrap(item.inhalt), font_size: 1.25, copies: 1 },
    });
    try {
      await mqttStore.publish('ToniTwn/feeds/easylabelprivate.data', payload);
      actionMsg = 'Label sent!';
    } catch {
      actionError = 'MQTT not connected — check settings.';
    }
    setTimeout(() => { actionMsg = ''; actionError = ''; }, 3000);
  }

  async function sendToMachine() {
    if (!item) return;
    actionMsg = ''; actionError = '';
    const isCoords = STEPPER_RE.test((item.bereich ?? '').trim());
    const topic = mqttTopic(isCoords ? 'workshop.laser' : 'workshop.box');
    const payload = isCoords ? item.bereich.trim() : String(item.box_nr);
    try {
      await mqttStore.publish(topic, payload);
      actionMsg = 'Sent!';
    } catch {
      actionError = 'MQTT not connected — check settings.';
    }
    setTimeout(() => { actionMsg = ''; actionError = ''; }, 3000);
  }

  $: boxNr = parseInt($page.params.box_nr, 10);

  function imageUrl(item: Item): string {
    if (!item.image) return '';
    return getPb().getFileUrl(item, item.image);
  }

  function thumbnailUrl(item: Item): string {
    if (!item.image) return '';
    return getPb().getFileUrl(item, item.image, { thumb: '800x600' });
  }

  onMount(async () => {
    try {
      const result = await getPb()
        .collection('items')
        .getFirstListItem<Item>(`box_nr=${boxNr}`);
      item = result;
    } catch (e: unknown) {
      const status = (e as { status?: number })?.status;
      if (status === 401) { auth.clear(); goto(`${base}/setup`, { replaceState: true }); }
      else if (status === 404) error = 'Item not found.';
      else error = 'Could not load item.';
    } finally {
      loading = false;
    }
  });

  async function deleteItem() {
    if (!item) return;
    deleting = true;
    try {
      await getPb().collection('items').delete(item.id);
      goto(`${base}/gallery`, { replaceState: true });
    } catch {
      error = 'Delete failed.';
      deleting = false;
      confirmDelete = false;
    }
  }
</script>

<svelte:head><title>Workshop — Box {boxNr}</title></svelte:head>

<div class="flex flex-col min-h-screen bg-gray-50">

  <!-- Header -->
  <header class="bg-white border-b border-gray-100 px-4 py-3 pt-safe flex items-center gap-3 sticky top-0 z-10">
    <button on:click={() => goto(`${base}/gallery`)} class="text-gray-400 hover:text-gray-600">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
    </button>
    <h1 class="text-lg font-semibold flex-1">
      {#if item}Box #{String(item.box_nr).padStart(3, '0')}{:else}Detail{/if}
    </h1>
    {#if item}
      <button
        on:click={() => goto(`${base}/add?edit=${item?.box_nr}`)}
        class="text-brand-500 text-sm font-medium px-3 py-1.5 rounded-xl hover:bg-brand-50 transition"
      >
        Edit
      </button>
    {/if}
  </header>

  <main class="flex-1 pb-safe">

    {#if loading}
      <div class="flex items-center justify-center h-48 text-gray-400 text-sm">Loading…</div>

    {:else if error}
      <div class="flex items-center justify-center h-48 text-red-500 text-sm">{error}</div>

    {:else if item}
      <!-- Image -->
      <div class="bg-black aspect-video w-full">
        {#if item.image}
          <img
            src={thumbnailUrl(item)}
            alt="Box {item.box_nr}"
            class="w-full h-full object-contain"
          />
        {:else}
          <div class="w-full h-full flex items-center justify-center text-gray-600">
            <svg class="w-16 h-16 opacity-30" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909"/>
            </svg>
          </div>
        {/if}
      </div>

      <!-- Details card -->
      <div class="px-4 py-4 space-y-4">
        <div class="bg-white rounded-2xl shadow-sm divide-y divide-gray-100">

          <div class="px-4 py-3 flex items-center gap-3">
            <span class="text-xs text-gray-400 w-20 shrink-0">Typ</span>
            <span class="text-sm px-2.5 py-0.5 rounded-full font-medium {TYP_COLOURS[item.typ]}">
              {item.typ}
            </span>
          </div>

          <div class="px-4 py-3 flex gap-3">
            <span class="text-xs text-gray-400 w-20 shrink-0 pt-0.5">Bereich</span>
            <span class="text-sm text-gray-800">{item.bereich || '—'}</span>
          </div>

          <div class="px-4 py-3 flex gap-3">
            <span class="text-xs text-gray-400 w-20 shrink-0 pt-0.5">Inhalt</span>
            <span class="text-sm text-gray-800 whitespace-pre-wrap">{item.inhalt || '—'}</span>
          </div>

        </div>

        <!-- Action buttons -->
        <div class="space-y-2">
          {#if actionMsg}
            <p class="text-center text-sm text-green-600 font-medium">{actionMsg}</p>
          {:else if actionError}
            <p class="text-center text-sm text-red-500">{actionError}</p>
          {/if}

          <div class="flex gap-2">
            <button
              on:click={() => printLabel('material')}
              class="flex-1 rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold
                     hover:bg-brand-600 active:bg-brand-700 transition"
            >
              Print Label
            </button>
            <button
              on:click={() => printLabel('materialgross')}
              class="flex-1 rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold
                     hover:bg-brand-600 active:bg-brand-700 transition"
            >
              Print Label + QR
            </button>
          </div>
          <button
            on:click={sendToMachine}
            class="w-full rounded-xl border border-brand-500 text-brand-500 py-3 text-sm font-semibold
                   hover:bg-brand-50 active:bg-brand-100 transition"
          >
            Show me!
          </button>

          <!-- MQTT status indicator -->
          <p class="text-center text-xs text-gray-300">
            MQTT: {$mqttStatus}
          </p>
        </div>

        <!-- Delete -->
        {#if !confirmDelete}
          <button
            on:click={() => (confirmDelete = true)}
            class="w-full text-red-400 text-sm py-2 hover:text-red-600 transition"
          >
            Delete item…
          </button>
        {:else}
          <div class="bg-red-50 rounded-2xl p-4 space-y-3">
            <p class="text-sm text-red-700 font-medium text-center">Delete Box #{item.box_nr}?</p>
            <p class="text-xs text-red-500 text-center">This cannot be undone.</p>
            <div class="flex gap-2">
              <button
                on:click={() => (confirmDelete = false)}
                class="flex-1 rounded-xl border border-gray-300 text-gray-600 py-2.5 text-sm font-medium hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                on:click={deleteItem}
                disabled={deleting}
                class="flex-1 rounded-xl py-2.5 text-sm font-semibold disabled:opacity-40"
                style="background-color: #ef4444; color: white;"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        {/if}

      </div>
    {/if}
  </main>
</div>
