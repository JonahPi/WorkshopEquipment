<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { auth } from '$lib/stores/auth';
  import { initPb } from '$lib/pb';
  import PocketBase from 'pocketbase';

  import { browser } from '$app/environment';

  let pbUrl       = browser ? (localStorage.getItem('pb_url') ?? '') : '';
  let pbEmail     = '';
  let pbPassword  = '';
  let aioUsername  = browser ? (localStorage.getItem('aio_username') ?? '') : '';
  let aioKey       = browser ? (localStorage.getItem('aio_key') ?? '') : '';
  let anthropicKey = browser ? (localStorage.getItem('anthropic_key') ?? '') : '';

  let pbError  = '';
  let aioError = '';
  let pbOk     = browser ? !!localStorage.getItem('pb_token') : false;
  let loading  = false;

  let showPbPassword   = false;
  let showAioKey       = false;
  let showAnthropicKey = false;

  function onPaste(e: Event, set: (v: string) => void) {
    requestAnimationFrame(() => set((e.target as HTMLInputElement).value));
  }

  async function verifyPocketBase() {
    pbError = '';
    pbOk = false;
    if (!pbUrl || !pbEmail || !pbPassword) { pbError = 'All three fields are required.'; return; }
    loading = true;
    try {
      const pb = new PocketBase(pbUrl.replace(/\/$/, ''));
      await pb.collection('_superusers').authWithPassword(pbEmail, pbPassword);
      pbOk = true;
      localStorage.setItem('pb_token', pb.authStore.token);
    } catch (e: unknown) {
      const status = (e as { status?: number })?.status;
      pbError = status === 400 || status === 401
        ? 'Wrong email or password.'
        : 'Cannot reach PocketBase — check URL.';
    } finally {
      loading = false;
    }
  }

  async function save() {
    if (!pbOk) { await verifyPocketBase(); if (!pbOk) return; }
    if (!aioUsername || !aioKey) { aioError = 'Both fields are required.'; return; }
    aioError = '';

    const pbToken = localStorage.getItem('pb_token') ?? '';
    const creds = {
      pbUrl:        pbUrl.replace(/\/$/, ''),
      pbToken,
      pbEmail,
      pbPassword,
      aioUsername,
      aioKey,
      anthropicKey,
    };
    auth.save(creds);
    initPb(creds.pbUrl, creds.pbToken);
    goto(`${base}/gallery`, { replaceState: true });
  }
</script>

<svelte:head><title>Workshop — Setup</title></svelte:head>

<main class="min-h-screen flex flex-col items-center justify-center px-6 py-12 bg-gray-50">
  <div class="w-full max-w-sm">

    <h1 class="text-2xl font-bold text-brand-500 mb-1">Workshop Inventory</h1>
    <p class="text-sm text-gray-500 mb-8">Enter your credentials to get started.</p>

    <!-- PocketBase -->
    <section class="mb-6">
      <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Database</h2>
      <div class="space-y-3">
        <input
          bind:value={pbUrl}
          type="url"
          placeholder="PocketBase URL  e.g. http://127.0.0.1:8090"
          class="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          autocomplete="off" autocapitalize="none" spellcheck="false"
        />
        <input
          bind:value={pbEmail}
          type="email"
          placeholder="Admin email"
          class="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          autocomplete="email" autocapitalize="none" autocorrect="off" spellcheck="false"
          on:paste={(e) => onPaste(e, v => pbEmail = v)}
        />
        <div class="relative">
          {#if showPbPassword}
            <input bind:value={pbPassword} type="text"
              placeholder="Admin password"
              class="w-full rounded-xl border border-gray-300 px-4 py-3 pr-16 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              autocomplete="current-password" autocapitalize="none" autocorrect="off" spellcheck="false"
              on:paste={(e) => onPaste(e, v => pbPassword = v)} />
          {:else}
            <input bind:value={pbPassword} type="password"
              placeholder="Admin password"
              class="w-full rounded-xl border border-gray-300 px-4 py-3 pr-16 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              autocomplete="current-password" autocapitalize="none" autocorrect="off"
              on:paste={(e) => onPaste(e, v => pbPassword = v)} />
          {/if}
          <button type="button" on:click={() => showPbPassword = !showPbPassword}
            class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-600 px-1 py-1"
          >{showPbPassword ? 'Hide' : 'Show'}</button>
        </div>
        {#if pbError}
          <p class="text-red-500 text-xs">{pbError}</p>
        {/if}
        {#if pbOk}
          <p class="text-green-600 text-xs">✓ Connected to PocketBase</p>
        {/if}
        <button
          on:click={verifyPocketBase}
          disabled={loading}
          class="w-full rounded-xl border border-brand-500 text-brand-500 px-4 py-2.5 text-sm font-medium
                 hover:bg-brand-50 active:bg-brand-100 disabled:opacity-40 transition"
        >
          {loading ? 'Checking…' : 'Test connection'}
        </button>
      </div>
    </section>

    <!-- Adafruit.io -->
    <section class="mb-8">
      <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Adafruit.io (MQTT)</h2>
      <div class="space-y-3">
        <input
          bind:value={aioUsername}
          type="text"
          placeholder="AIO Username"
          class="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          autocomplete="off" autocapitalize="none" spellcheck="false"
        />
        <div class="relative">
          {#if showAioKey}
            <input bind:value={aioKey} type="text"
              placeholder="AIO Key  aio_xxxxxxxxxxxx"
              class="w-full rounded-xl border border-gray-300 px-4 py-3 pr-16 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false"
              on:paste={(e) => onPaste(e, v => aioKey = v)} />
          {:else}
            <input bind:value={aioKey} type="password"
              placeholder="AIO Key  aio_xxxxxxxxxxxx"
              class="w-full rounded-xl border border-gray-300 px-4 py-3 pr-16 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              autocomplete="off" autocapitalize="none" autocorrect="off"
              on:paste={(e) => onPaste(e, v => aioKey = v)} />
          {/if}
          <button type="button" on:click={() => showAioKey = !showAioKey}
            class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-600 px-1 py-1"
          >{showAioKey ? 'Hide' : 'Show'}</button>
        </div>
        {#if aioError}
          <p class="text-red-500 text-xs">{aioError}</p>
        {/if}
      </div>
    </section>

    <!-- Anthropic (optional) -->
    <section class="mb-8">
      <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">AI Description (optional)</h2>
      <p class="text-xs text-gray-400 mb-3">Claude API key for auto-describing box contents from photos.</p>
      <div class="relative">
        {#if showAnthropicKey}
          <input bind:value={anthropicKey} type="text"
            placeholder="sk-ant-xxxxxxxxxxxx"
            class="w-full rounded-xl border border-gray-300 px-4 py-3 pr-16 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false"
            on:paste={(e) => onPaste(e, v => anthropicKey = v)} />
        {:else}
          <input bind:value={anthropicKey} type="password"
            placeholder="sk-ant-xxxxxxxxxxxx"
            class="w-full rounded-xl border border-gray-300 px-4 py-3 pr-16 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            autocomplete="off" autocapitalize="none" autocorrect="off"
            on:paste={(e) => onPaste(e, v => anthropicKey = v)} />
        {/if}
        <button type="button" on:click={() => showAnthropicKey = !showAnthropicKey}
          class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-600 px-1 py-1"
        >{showAnthropicKey ? 'Hide' : 'Show'}</button>
      </div>
    </section>

    <button
      on:click={save}
      disabled={loading}
      class="w-full rounded-xl bg-brand-500 text-white px-4 py-3 font-semibold text-sm
             hover:bg-brand-600 active:bg-brand-700 disabled:opacity-40 transition"
    >
      Save &amp; Open Inventory
    </button>

  </div>
</main>
