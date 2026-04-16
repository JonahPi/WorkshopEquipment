<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { getPb } from '$lib/pb';
  import { auth } from '$lib/stores/auth';
  import ItemCard from '$lib/components/ItemCard.svelte';
  import type { Item, ItemTyp } from '$lib/types';
  import { ALL_TYPEN } from '$lib/types';

  let items: Item[] = [];
  let loading = true;
  let error = '';
  let searchText = '';
  let filterTyp: ItemTyp | '' = '';
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
      if (status === 401) {
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
    const matchesText = !searchText
      || item.inhalt?.toLowerCase().includes(searchText.toLowerCase())
      || item.bereich?.toLowerCase().includes(searchText.toLowerCase())
      || String(item.box_nr).includes(searchText);
    const matchesTyp = !filterTyp || item.typ === filterTyp;
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
          bind:value={searchText}
          type="search"
          placeholder="Search inventory…"
          class="w-full pl-9 pr-4 py-2 bg-gray-100 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>
      <button
        on:click={() => (showFilters = !showFilters)}
        class="p-2 rounded-xl {filterTyp ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-500'} transition"
        aria-label="Filter by type"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M10 12h4"/>
        </svg>
      </button>
    </div>

    {#if showFilters}
      <div class="flex gap-2 pb-3 overflow-x-auto scrollbar-none">
        <button
          on:click={() => (filterTyp = '')}
          class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition
                 {!filterTyp ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-600'}"
        >All</button>
        {#each ALL_TYPEN as typ}
          <button
            on:click={() => (filterTyp = filterTyp === typ ? '' : typ)}
            class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition
                   {filterTyp === typ ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-600'}"
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
      <div class="flex items-center justify-center h-48 text-gray-400 text-sm">
        {items.length === 0 ? 'No items yet — tap + to add one.' : 'No results.'}
      </div>

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
