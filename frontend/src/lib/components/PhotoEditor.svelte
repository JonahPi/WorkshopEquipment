<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import Cropper from 'cropperjs';
  import 'cropperjs/dist/cropper.css';

  export let src: string;

  const dispatch = createEventDispatcher<{ confirm: File; cancel: void }>();

  let imgEl: HTMLImageElement;
  let cropper: Cropper;

  onMount(() => {
    cropper = new Cropper(imgEl, {
      viewMode: 1,
      autoCropArea: 1,
      movable: true,
      zoomable: true,
      rotatable: true,
      scalable: true,
      responsive: true,
    });
  });

  onDestroy(() => cropper?.destroy());

  function rotate(deg: number) {
    cropper.rotate(deg);
  }

  function confirm() {
    const canvas = cropper.getCroppedCanvas({ maxWidth: 1920, maxHeight: 1920 });
    canvas.toBlob(blob => {
      if (blob) dispatch('confirm', new File([blob], 'photo.jpg', { type: 'image/jpeg' }));
    }, 'image/jpeg', 0.85);
  }
</script>

<!-- Full-screen overlay -->
<div class="fixed inset-0 z-50 bg-black flex flex-col">

  <!-- Toolbar -->
  <div class="flex items-center justify-between px-4 py-3 bg-black/80">
    <button
      on:click={() => dispatch('cancel')}
      class="text-white text-sm font-medium px-3 py-1.5"
    >
      Cancel
    </button>
    <div class="flex gap-4">
      <button on:click={() => rotate(-90)} class="text-white" title="Rotate left">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3"/>
        </svg>
      </button>
      <button on:click={() => rotate(90)} class="text-white" title="Rotate right">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15 15l6-6m0 0l-6-6m6 6H9a6 6 0 000 12h3"/>
        </svg>
      </button>
    </div>
    <button
      on:click={confirm}
      class="text-white text-sm font-semibold px-3 py-1.5 bg-brand-500 rounded-xl"
    >
      Use photo
    </button>
  </div>

  <!-- Cropper area -->
  <div class="flex-1 overflow-hidden">
    <img bind:this={imgEl} {src} alt="Edit" class="block max-w-full" />
  </div>

</div>
