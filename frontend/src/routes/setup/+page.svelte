<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { auth } from '$lib/stores/auth';
  import { initPb } from '$lib/pb';
  import PocketBase from 'pocketbase';

  let pbUrl       = '';
  let pbEmail     = '';
  let pbPassword  = '';
  let aioUsername = '';
  let aioKey      = '';

  let pbError  = '';
  let aioError = '';
  let pbOk     = false;
  let loading  = false;

  async function verifyPocketBase() {
    pbError = '';
    pbOk = false;
    if (!pbUrl || !pbEmail || !pbPassword) { pbError = 'All three fields are required.'; return; }
    loading = true;
    try {
      const pb = new PocketBase(pbUrl.replace(/\/$/, ''));
      await pb.collection('_superusers').authWithPassword(pbEmail, pbPassword);
      pbOk = true;
      // store the resulting JWT so we can restore it on next launch
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
      pbUrl:       pbUrl.replace(/\/$/, ''),
      pbToken,
      aioUsername,
      aioKey,
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
          autocomplete="email"
        />
        <input
          bind:value={pbPassword}
          type="password"
          placeholder="Admin password"
          class="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          autocomplete="current-password"
        />
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
        <input
          bind:value={aioKey}
          type="password"
          placeholder="AIO Key  aio_xxxxxxxxxxxx"
          class="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          autocomplete="off"
        />
        {#if aioError}
          <p class="text-red-500 text-xs">{aioError}</p>
        {/if}
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
