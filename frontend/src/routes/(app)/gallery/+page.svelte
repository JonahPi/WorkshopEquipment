<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { getPb } from '$lib/pb';
  import { auth } from '$lib/stores/auth';
  import ItemCard from '$lib/components/ItemCard.svelte';
  import type { Item } from '$lib/types';
  import { ALL_TYPEN } from '$lib/types';
  import { searchText, filterTyp } from '$lib/stores/galleryFilter';

  let items: Item[] = [];
  let loading = true;
  let error = '';
  let showFilters = false;

  async function loadItems() {
    loading = true;
    error = '';
    try {
      const pb = getPb();
      const result = await pb.collection('items').getFullList<Item>({
        sort: 'box_nr',
      });
      items = result;
    } catch (e: unknown) {
      const status = (e as { status?: number })?.status;
      if (status === 401 || status === 403) {
        auth.clear();
        goto(`${base}/setup`, { replaceState: true });
      } else {
        error = 'Could not load inventory. Check your connection.';
      }
    } finally {
      loading = false;
    }
  }

  onMount(loadItems);

  $: filtered = items.filter(item => {
    const matchesText = !$searchText
      || item.inhalt?.toLowerCase().includes($searchText.toLowerCase())
      || item.bereich?.toLowerCase().includes($searchText.toLowerCase())
      || String(item.box_nr).includes($searchText);
    const matchesTyp = !$filterTyp || item.typ === $filterTyp;
    return matchesText && matchesTyp;
  });

  let refreshing = false;
  async function pullRefresh() {
    if (refreshing) return;
    refreshing = true;
    await loadItems();
    refreshing = false;
  }
</script>

<svelte:head><title>Workshop — Inventory</title></svelte:head>

<div class="flex flex-col h-screen">

  <!-- Header -->
  <header class="bg-white border-b border-gray-100 px-4 pt-safe sticky top-0 z-10">
    <div class="flex items-center gap-2 py-3">
      <div class="relative flex-1">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
          fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M21 21l-4.35-4.35M17 11A6 6 0 1 0 5 11a6 6 0 0 0 12 0z"/>
        </svg>
        <input
          bind:value={$searchText}
          type="search"
          placeholder="Search inventory…"
          class="w-full pl-9 pr-4 py-2 bg-gray-100 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>
      <button
        on:click={() => (showFilters = !showFilters)}
        class="p-2 rounded-xl {$filterTyp ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-500'} transition"
        aria-label="Filter by type"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M10 12h4"/>
        </svg>
      </button>
      <a
        href="{base}/setup"
        class="p-2 rounded-xl bg-gray-100 text-gray-500 hover:bg-gray-200 transition"
        aria-label="Settings"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
        </svg>
      </a>
    </div>

    {#if showFilters}
      <div class="flex gap-2 pb-3 overflow-x-auto scrollbar-none">
        <button
          on:click={() => ($filterTyp = '')}
          class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition
                 {!$filterTyp ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-600'}"
        >All</button>
        {#each ALL_TYPEN as typ}
          <button
            on:click={() => ($filterTyp = $filterTyp === typ ? '' : typ)}
            class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition
                   {$filterTyp === typ ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-600'}"
          >{typ}</button>
        {/each}
      </div>
    {/if}
  </header>

  <!-- Content -->
  <main class="flex-1 overflow-y-auto px-3 py-3">

    {#if loading}
      <div class="flex items-center justify-center h-48 text-gray-400 text-sm">
        Loading inventory…
      </div>

    {:else if error}
      <div class="flex flex-col items-center justify-center h-48 gap-3">
        <p class="text-red-500 text-sm">{error}</p>
        <button on:click={pullRefresh} class="text-brand-500 text-sm underline">Retry</button>
      </div>

    {:else if filtered.length === 0}
      {#if items.length === 0 && !localStorage.getItem('import_done')}
        <!-- First-run import prompt -->
        <div class="flex flex-col items-center justify-center h-64 gap-4 text-center px-6">
          <p class="text-gray-500 text-sm">Your inventory is empty.</p>
          <p class="text-gray-400 text-xs">Import your existing Google Sheets data or add items manually.</p>
          <a
            href="{base}/import"
            class="rounded-xl bg-brand-500 text-white px-6 py-3 text-sm font-semibold hover:bg-brand-600 transition"
          >
            Import from CSV
          </a>
        </div>
      {:else}
        <div class="flex items-center justify-center h-48 text-gray-400 text-sm">
          {items.length === 0 ? 'No items yet — tap + to add one.' : 'No results.'}
        </div>
      {/if}

    {:else}
      <div class="grid grid-cols-2 gap-3">
        {#each filtered as item (item.id)}
          <ItemCard {item} />
        {/each}
      </div>
      <p class="text-center text-xs text-gray-300 mt-4 pb-2">
        {filtered.length} of {items.length} items
      </p>
    {/if}

  </main>
</div>
