<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { getPb } from '$lib/pb';
  import { auth } from '$lib/stores/auth';
  import type { Item, ItemTyp } from '$lib/types';
  import { ALL_TYPEN, TYP_COLOURS } from '$lib/types';
  import PhotoEditor from '$lib/components/PhotoEditor.svelte';

  // Edit mode when ?edit=<box_nr> is present
  $: editBoxNr = $page.url.searchParams.get('edit')
    ? parseInt($page.url.searchParams.get('edit')!, 10)
    : null;
  $: isEdit = editBoxNr !== null;

  // Wizard step: 1 | 2 | 3 | 4
  let step = isEdit ? 3 : 1;   // skip steps 1-2 in edit mode

  // Form fields
  let boxNr     = 0;
  let typ: ItemTyp = 'Box';
  let bereich   = '';
  let inhalt    = '';

  // Image handling
  let imageFile: File | null = null;
  let imagePreview = '';
  let existingImageUrl = '';
  let editorSrc = '';
  let showEditor = false;

  // Step 1 state
  let boxNrInput  = '';
  let boxNrError  = '';
  let loadingNext = false;
  let existingItem: Item | null = null;   // populated in edit mode

  // Save state
  let saving = false;
  let saveError = '';

  onMount(async () => {
    if (isEdit && editBoxNr) {
      // Load existing item for editing
      loadingNext = true;
      try {
        const pb = getPb();
        existingItem = await pb.collection('items').getFirstListItem<Item>(`box_nr=${editBoxNr}`);
        boxNr    = existingItem.box_nr;
        typ      = existingItem.typ;
        bereich  = existingItem.bereich;
        inhalt   = existingItem.inhalt;
        if (existingItem.image) {
          existingImageUrl = pb.getFileUrl(existingItem, existingItem.image, { thumb: '800x600' });
        }
        step = 3;
      } catch {
        saveError = 'Could not load item.';
      } finally {
        loadingNext = false;
      }
    } else {
      // Propose next box number
      await proposeBoxNr();
    }
  });

  async function proposeBoxNr() {
    try {
      const result = await getPb()
        .collection('items')
        .getList<Item>(1, 1, { sort: '-box_nr', fields: 'box_nr' });
      const max = result.items[0]?.box_nr ?? 0;
      boxNrInput = String(max + 1);
    } catch {
      boxNrInput = '';
    }
  }

  async function confirmBoxNr() {
    boxNrError = '';
    const nr = parseInt(boxNrInput, 10);
    if (!nr || nr < 1) { boxNrError = 'Enter a valid number.'; return; }

    loadingNext = true;
    try {
      await getPb().collection('items').getFirstListItem(`box_nr=${nr}`);
      boxNrError = `Box #${nr} already exists.`;
    } catch (e: unknown) {
      if ((e as { status?: number })?.status === 404) {
        boxNr = nr;
        step = 2;
      } else {
        boxNrError = 'Could not check — try again.';
      }
    } finally {
      loadingNext = false;
    }
  }

  function handlePhoto(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      editorSrc = ev.target?.result as string;
      showEditor = true;
    };
    reader.readAsDataURL(file);
  }

  function handleEditorConfirm(file: File) {
    imageFile = file;
    const reader = new FileReader();
    reader.onload = ev => { imagePreview = ev.target?.result as string; };
    reader.readAsDataURL(file);
    showEditor = false;
  }

  function handleEditorCancel() {
    showEditor = false;
    editorSrc = '';
  }

  let describing = false;
  let describeError = '';

  async function describeWithAI() {
    const src = imagePreview || existingImageUrl;
    if (!src || !$auth?.anthropicKey) return;
    describing = true;
    describeError = '';
    try {
      let base64: string;
      let mediaType: string;

      if (imagePreview) {
        // data URL → split out base64 and mime type
        const [meta, data] = imagePreview.split(',');
        base64    = data;
        mediaType = meta.match(/:(.*?);/)?.[1] ?? 'image/jpeg';
      } else {
        // fetch existing PocketBase image
        const resp = await fetch(existingImageUrl);
        const blob = await resp.blob();
        mediaType  = blob.type || 'image/jpeg';
        base64     = await new Promise<string>(resolve => {
          const r = new FileReader();
          r.onload = e => resolve((e.target!.result as string).split(',')[1]);
          r.readAsDataURL(blob);
        });
      }

      const resp = await fetch(`${$auth.pbUrl}/api/describe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64, api_key: $auth.anthropicKey, media_type: mediaType }),
      });
      const data = await resp.json();
      if (data.description) inhalt = data.description;
      else describeError = 'No description returned.';
    } catch {
      describeError = 'AI description failed — check your API key.';
    } finally {
      describing = false;
    }
  }

  async function save() {
    saving = true;
    saveError = '';
    try {
      const fd = new FormData();
      if (!isEdit) fd.append('box_nr', String(boxNr));
      fd.append('typ',     typ);
      fd.append('bereich', bereich);
      fd.append('inhalt',  inhalt);
      if (imageFile) fd.append('image', imageFile);

      if (isEdit && existingItem) {
        await getPb().collection('items').update(existingItem.id, fd);
      } else {
        await getPb().collection('items').create(fd);
      }
      goto(`${base}/item/${isEdit ? editBoxNr : boxNr}`, { replaceState: true });
    } catch (e: unknown) {
      const status = (e as { status?: number })?.status;
      if (status === 401) { auth.clear(); goto(`${base}/setup`, { replaceState: true }); }
      else saveError = 'Save failed — please try again.';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Workshop — {isEdit ? 'Edit' : 'Add'} Item</title>
</svelte:head>

{#if showEditor}
  <PhotoEditor
    src={editorSrc}
    on:confirm={e => handleEditorConfirm(e.detail)}
    on:cancel={handleEditorCancel}
  />
{/if}

<div class="flex flex-col min-h-screen bg-gray-50">

  <!-- Header -->
  <header class="bg-white border-b border-gray-100 px-4 py-3 pt-safe flex items-center gap-3 sticky top-0 z-10">
    <button
      on:click={() => isEdit ? goto(`${base}/item/${editBoxNr}`) : (step > 1 ? step-- : goto(`${base}/gallery`))}
      class="text-gray-400 hover:text-gray-600"
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
    </button>
    <h1 class="text-lg font-semibold flex-1">{isEdit ? 'Edit Item' : 'New Item'}</h1>
    {#if !isEdit}
      <!-- Step indicator -->
      <span class="text-xs text-gray-400">Step {step} / 4</span>
    {/if}
  </header>

  <main class="flex-1 px-4 py-6 max-w-lg mx-auto w-full">

    <!-- ── Step 1: Box Number ── -->
    {#if step === 1}
      <div class="space-y-4">
        <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
          <div>
            <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Box Number
            </label>
            <input
              bind:value={boxNrInput}
              type="number"
              min="1"
              placeholder="e.g. 42"
              class="w-full rounded-xl border border-gray-300 px-4 py-3 text-2xl font-mono
                     focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            {#if boxNrError}
              <p class="text-red-500 text-xs mt-1">{boxNrError}</p>
            {/if}
          </div>
          <p class="text-xs text-gray-400">
            This number is encoded in the QR code label. It cannot be changed later.
          </p>
        </div>

        <button
          on:click={confirmBoxNr}
          disabled={loadingNext}
          class="w-full rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold
                 hover:bg-brand-600 disabled:opacity-40 transition"
        >
          {loadingNext ? 'Checking…' : 'Confirm number →'}
        </button>
      </div>

    <!-- ── Step 2: Photo ── -->
    {:else if step === 2}
      <div class="space-y-4">
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
          <!-- Preview area -->
          <div class="aspect-video bg-gray-100 flex items-center justify-center">
            {#if imagePreview}
              <img src={imagePreview} alt="Preview" class="w-full h-full object-contain" />
            {:else}
              <svg class="w-16 h-16 text-gray-300" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round"
                  d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z"/>
              </svg>
            {/if}
          </div>
          <div class="p-4 flex gap-2">
            <label class="flex-1 cursor-pointer text-center rounded-xl border border-brand-500 text-brand-500
                          py-2.5 text-sm font-medium hover:bg-brand-50 transition">
              {imagePreview ? 'Retake photo' : 'Take photo'}
              <input
                type="file"
                accept="image/*"
                capture="environment"
                class="hidden"
                on:change={handlePhoto}
              />
            </label>
            <label class="flex-1 cursor-pointer text-center rounded-xl border border-gray-300 text-gray-600
                          py-2.5 text-sm font-medium hover:bg-gray-50 transition">
              Choose file
              <input
                type="file"
                accept="image/*"
                class="hidden"
                on:change={handlePhoto}
              />
            </label>
          </div>
        </div>

        <div class="flex gap-3">
          <button
            on:click={() => { imageFile = null; imagePreview = ''; step = 3; }}
            class="flex-1 rounded-xl border border-gray-300 text-gray-500 py-3 text-sm font-medium
                   hover:bg-gray-50 transition"
          >
            Skip photo
          </button>
          <button
            on:click={() => step = 3}
            disabled={!imageFile}
            class="flex-1 rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold
                   hover:bg-brand-600 disabled:opacity-40 transition"
          >
            Next →
          </button>
        </div>
      </div>

    <!-- ── Step 3: Storage location ── -->
    {:else if step === 3}
      <div class="space-y-4">
        <div class="bg-white rounded-2xl shadow-sm p-5 space-y-5">

          <!-- Typ selector -->
          <div>
            <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Storage type
            </label>
            <div class="flex flex-wrap gap-2">
              {#each ALL_TYPEN as t}
                <button
                  on:click={() => (typ = t)}
                  class="px-3 py-1.5 rounded-full text-xs font-medium transition border
                         {typ === t
                           ? TYP_COLOURS[t] + ' border-transparent'
                           : 'border-gray-200 text-gray-500 hover:border-gray-300'}"
                >
                  {t}
                </button>
              {/each}
            </div>
          </div>

          <!-- Bereich -->
          <div>
            <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Bereich
            </label>
            <input
              bind:value={bereich}
              type="text"
              placeholder="e.g. 3500/2000  or  Kellertreppe"
              class="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm
                     focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <p class="text-xs text-gray-400 mt-1">
              Stepper coordinates (x/y) or a descriptive location
            </p>
          </div>
        </div>

        <button
          on:click={() => step = 4}
          class="w-full rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold
                 hover:bg-brand-600 transition"
        >
          Next →
        </button>
      </div>

    <!-- ── Step 4: Contents + Save ── -->
    {:else if step === 4}
      <div class="space-y-4">
        <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">

          <!-- Existing photo in edit mode -->
          {#if isEdit && existingImageUrl && !imagePreview}
            <div class="aspect-video bg-gray-100 rounded-xl overflow-hidden">
              <img src={existingImageUrl} alt="Current" class="w-full h-full object-contain" />
            </div>
            <label class="block cursor-pointer text-center rounded-xl border border-gray-300 text-gray-600
                          py-2.5 text-sm font-medium hover:bg-gray-50 transition">
              Replace photo
              <input type="file" accept="image/*" capture="environment" class="hidden" on:change={handlePhoto} />
            </label>
          {/if}

          {#if imagePreview}
            <div class="aspect-video bg-gray-100 rounded-xl overflow-hidden">
              <img src={imagePreview} alt="New photo" class="w-full h-full object-contain" />
            </div>
          {/if}

          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Inhalt
              </label>
              {#if $auth?.anthropicKey && (imagePreview || existingImageUrl)}
                <button
                  on:click={describeWithAI}
                  disabled={describing}
                  class="text-xs text-brand-500 font-medium flex items-center gap-1
                         disabled:opacity-40 hover:text-brand-600 transition"
                >
                  {#if describing}
                    Describing…
                  {:else}
                    ✨ Describe with AI
                  {/if}
                </button>
              {/if}
            </div>
            {#if describeError}
              <p class="text-red-500 text-xs mb-1">{describeError}</p>
            {/if}
            <textarea
              bind:value={inhalt}
              rows="4"
              placeholder="What's inside this box?"
              class="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm resize-none
                     focus:outline-none focus:ring-2 focus:ring-brand-500"
            ></textarea>
          </div>

          {#if saveError}
            <p class="text-red-500 text-xs">{saveError}</p>
          {/if}
        </div>

        <button
          on:click={save}
          disabled={saving}
          class="w-full rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold
                 hover:bg-brand-600 disabled:opacity-40 transition"
        >
          {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Save item'}
        </button>
      </div>
    {/if}

  </main>
</div>
