<script lang="ts">
  import { base } from '$app/paths';
  import type { Item } from '$lib/types';
  import { TYP_COLOURS } from '$lib/types';
  import { getPb } from '$lib/pb';

  export let item: Item;

  function thumbnailUrl(item: Item): string {
    if (!item.image) return '';
    try {
      return getPb().getFileUrl(item, item.image, { thumb: '200x200' });
    } catch {
      return '';
    }
  }

  $: thumb = thumbnailUrl(item);
  $: boxNrFormatted = String(item.box_nr).padStart(3, '0');
</script>

<a
  href="{base}/item/{item.box_nr}"
  class="block rounded-2xl overflow-hidden bg-white shadow-sm active:scale-95 transition-transform"
>
  <!-- Thumbnail -->
  <div class="relative aspect-square bg-gray-100">
    {#if thumb}
      <img
        src={thumb}
        alt="Box {boxNrFormatted}"
        class="w-full h-full object-cover"
        loading="lazy"
      />
    {:else}
      <div class="w-full h-full flex items-center justify-center text-gray-300">
        <svg class="w-12 h-12" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M13.5 12h.008v.008H13.5V12zm0 0a2.25 2.25 0 100-4.5 2.25 2.25 0 000 4.5z"/>
        </svg>
      </div>
    {/if}

    <!-- Box number badge -->
    <span class="absolute top-2 left-2 bg-gray-900/70 text-white text-xs font-mono font-bold
                 px-2 py-0.5 rounded-full backdrop-blur-sm">
      #{boxNrFormatted}
    </span>
  </div>

  <!-- Info -->
  <div class="px-3 py-2">
    <p class="text-sm text-gray-800 line-clamp-2 min-h-[2.5rem]">
      {item.inhalt || '—'}
    </p>
    <div class="flex items-center gap-1.5 mt-1.5">
      <span class="text-xs px-2 py-0.5 rounded-full font-medium {TYP_COLOURS[item.typ]}">
        {item.typ}
      </span>
      {#if item.bereich}
        <span class="text-xs text-gray-400 truncate">{item.bereich}</span>
      {/if}
    </div>
  </div>
</a>
