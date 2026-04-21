<script lang="ts">
  import { base } from '$app/paths';
  import { page } from '$app/stores';

  $: currentPath = $page.url.pathname;
  $: onGallery = currentPath.endsWith('/gallery') || currentPath === base + '/';
  $: onScan    = currentPath.endsWith('/scan');
  $: onAdd     = currentPath.endsWith('/add');
</script>

<div class="flex flex-col min-h-screen">
  <!-- Page content -->
  <div class="flex-1 pb-16">
    <slot />
  </div>

  <!-- Bottom tab bar -->
  <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 pb-safe z-10">
    <div class="flex">
      <a
        href="{base}/gallery"
        class="flex-1 flex flex-col items-center py-2 text-xs font-medium transition-colors
               {onGallery ? 'text-brand-500' : 'text-gray-400'}"
        aria-label="Gallery"
      >
        <!-- Home icon -->
        <svg class="w-6 h-6 mb-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        Gallery
      </a>

      <a
        href="{base}/scan"
        class="flex-1 flex flex-col items-center py-2 text-xs font-medium transition-colors
               {onScan ? 'text-brand-500' : 'text-gray-400'}"
        aria-label="Scan QR code"
      >
        <!-- QR scan icon -->
        <svg class="w-6 h-6 mb-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M3 9V6a1 1 0 011-1h3M3 15v3a1 1 0 001 1h3m11-4v3a1 1 0 01-1 1h-3m4-12h-3a1 1 0 00-1 1v3
               M7 7h3v3H7zm7 0h3v3h-3zM7 14h3v3H7z"/>
        </svg>
        Scan
      </a>

      <a
        href="{base}/add"
        class="flex-1 flex flex-col items-center py-2 text-xs font-medium transition-colors
               {onAdd ? 'text-brand-500' : 'text-gray-400'}"
        aria-label="Add item"
      >
        <!-- Plus icon -->
        <svg class="w-6 h-6 mb-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        Add Item
      </a>
    </div>
  </nav>
</div>
