<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { getPb } from '$lib/pb';
  import type { ItemTyp } from '$lib/types';
  import { ALL_TYPEN } from '$lib/types';
  import Papa from 'papaparse';

  type State = 'idle' | 'previewing' | 'importing' | 'done';

  interface CsvRow {
    BoxNR:   string;
    Inhalt:  string;
    Typ:     string;
    Bereich: string;
    Foto:    string;
    QRcode:  string;
    [key: string]: string;
  }

  interface ValidatedRow {
    box_nr:  number;
    inhalt:  string;
    typ:     ItemTyp;
    bereich: string;
    foto:    string;
    skip:    boolean;   // duplicate
    typWarn: boolean;   // unknown typ coerced to Box
  }

  let state: State = 'idle';
  let rows: ValidatedRow[] = [];
  let existingBoxNrs = new Set<number>();

  // summary counts
  $: readyCount     = rows.filter(r => !r.skip).length;
  $: duplicateCount = rows.filter(r => r.skip).length;
  $: warnCount      = rows.filter(r => r.typWarn).length;
  $: previewRows    = rows.slice(0, 5);

  // progress
  let done      = 0;
  let photoFail = 0;
  let errored   = 0;

  // result
  let importedCount = 0;

  function normaliseTyp(raw: string): { typ: ItemTyp; warn: boolean } {
    const match = ALL_TYPEN.find(t => t.toLowerCase() === raw.trim().toLowerCase());
    return match ? { typ: match, warn: false } : { typ: 'Box', warn: true };
  }

  async function handleFile(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;

    // Fetch existing box numbers to detect duplicates
    try {
      const pb = getPb();
      const existing = await pb.collection('items').getFullList({ fields: 'box_nr' });
      existingBoxNrs = new Set(existing.map((r: { box_nr: number }) => r.box_nr));
    } catch {
      existingBoxNrs = new Set();
    }

    Papa.parse<CsvRow>(file, {
      header: true,
      skipEmptyLines: true,
      encoding: 'UTF-8',
      complete(results) {
        const headers = results.meta.fields ?? [];
        const required = ['BoxNR', 'Inhalt', 'Typ', 'Bereich', 'Foto'];
        const missing = required.filter(h =>
          !headers.some(f => f.trim().toLowerCase() === h.toLowerCase())
        );
        if (missing.length) {
          alert(`Missing columns: ${missing.join(', ')}`);
          return;
        }

        // Normalise header names (case-insensitive)
        rows = results.data.map(raw => {
          // find values case-insensitively
          const get = (key: string) => {
            const k = Object.keys(raw).find(f => f.trim().toLowerCase() === key.toLowerCase());
            return k ? raw[k].trim() : '';
          };

          const box_nr = parseInt(get('boxnr'), 10);
          const { typ, warn } = normaliseTyp(get('typ') || 'Box');

          return {
            box_nr,
            inhalt:  get('inhalt'),
            typ,
            bereich: get('bereich'),
            foto:    get('foto'),
            skip:    existingBoxNrs.has(box_nr),
            typWarn: warn,
          };
        }).filter(r => !isNaN(r.box_nr));

        state = 'previewing';
      },
      error(err) {
        alert(`CSV parse error: ${err.message}`);
      },
    });
  }

  async function executeImport() {
    state = 'importing';
    done = 0;
    photoFail = 0;
    errored = 0;
    importedCount = 0;

    const toImport = rows.filter(r => !r.skip);

    for (const row of toImport) {
      try {
        const fd = new FormData();
        fd.append('box_nr',  String(row.box_nr));
        fd.append('inhalt',  row.inhalt);
        fd.append('typ',     row.typ);
        fd.append('bereich', row.bereich);

        if (row.foto) {
          try {
            const resp = await fetch(row.foto.replace(/^http:\/\//, 'https://'));
            if (resp.ok) {
              const blob = await resp.blob();
              const filename = row.foto.split('/').pop() ?? 'image.jpg';
              fd.append('image', blob, filename);
            } else {
              photoFail++;
            }
          } catch {
            photoFail++;
          }
        }

        await getPb().collection('items').create(fd);
        importedCount++;
      } catch {
        errored++;
      }

      done++;
    }

    // Mark import as done so the gallery doesn't prompt again
    localStorage.setItem('import_done', '1');
    state = 'done';
  }
</script>

<svelte:head><title>Workshop — Import</title></svelte:head>

<div class="min-h-screen bg-gray-50">

  <!-- Header -->
  <header class="bg-white border-b border-gray-100 px-4 py-3 pt-safe flex items-center gap-3">
    <button on:click={() => goto(`${base}/gallery`)} class="text-gray-400 hover:text-gray-600">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
    </button>
    <h1 class="text-lg font-semibold">Import from Google Sheets CSV</h1>
  </header>

  <main class="px-4 py-6 max-w-lg mx-auto">

    <!-- IDLE: file upload -->
    {#if state === 'idle'}
      <div class="bg-white rounded-2xl p-6 shadow-sm text-center">
        <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
        </svg>
        <p class="text-sm text-gray-600 mb-1 font-medium">Select your exported CSV file</p>
        <p class="text-xs text-gray-400 mb-5">
          Required columns: BoxNR, Inhalt, Typ, Bereich, Foto, QRcode
        </p>
        <label class="cursor-pointer inline-block bg-brand-500 text-white rounded-xl px-6 py-3 text-sm font-medium hover:bg-brand-600 transition">
          Choose file
          <input type="file" accept=".csv" class="hidden" on:change={handleFile} />
        </label>
      </div>

    <!-- PREVIEWING: summary + preview table -->
    {:else if state === 'previewing'}
      <div class="space-y-4">

        <!-- Summary chips -->
        <div class="flex gap-2 flex-wrap">
          <span class="px-3 py-1.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            {readyCount} ready to import
          </span>
          {#if duplicateCount}
            <span class="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              {duplicateCount} duplicates — will skip
            </span>
          {/if}
          {#if warnCount}
            <span class="px-3 py-1.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
              {warnCount} unknown Typ → set to Box
            </span>
          {/if}
        </div>

        <!-- Preview table -->
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
          <p class="px-4 pt-4 pb-2 text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Preview (first {previewRows.length} rows)
          </p>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead class="bg-gray-50 text-gray-500">
                <tr>
                  <th class="px-3 py-2 text-left font-medium">#</th>
                  <th class="px-3 py-2 text-left font-medium">Inhalt</th>
                  <th class="px-3 py-2 text-left font-medium">Typ</th>
                  <th class="px-3 py-2 text-left font-medium">Bereich</th>
                  <th class="px-3 py-2 text-left font-medium">Photo</th>
                  <th class="px-3 py-2 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                {#each previewRows as row}
                  <tr class="{row.skip ? 'opacity-40' : ''}">
                    <td class="px-3 py-2 font-mono">{row.box_nr}</td>
                    <td class="px-3 py-2 max-w-[120px] truncate">{row.inhalt || '—'}</td>
                    <td class="px-3 py-2">
                      {row.typ}
                      {#if row.typWarn}<span class="text-yellow-500"> ⚠</span>{/if}
                    </td>
                    <td class="px-3 py-2 max-w-[80px] truncate">{row.bereich || '—'}</td>
                    <td class="px-3 py-2">{row.foto ? '✓' : '—'}</td>
                    <td class="px-3 py-2">
                      {#if row.skip}
                        <span class="text-gray-400">skip</span>
                      {:else}
                        <span class="text-green-600">import</span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>

        <div class="flex gap-3">
          <button
            on:click={() => { state = 'idle'; rows = []; }}
            class="flex-1 rounded-xl border border-gray-300 text-gray-600 py-3 text-sm font-medium hover:bg-gray-50 transition"
          >
            Cancel
          </button>
          <button
            on:click={executeImport}
            disabled={readyCount === 0}
            class="flex-1 rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold hover:bg-brand-600 disabled:opacity-40 transition"
          >
            Import {readyCount} items
          </button>
        </div>
      </div>

    <!-- IMPORTING: progress -->
    {:else if state === 'importing'}
      {@const total = rows.filter(r => !r.skip).length}
      {@const pct = total > 0 ? Math.round((done / total) * 100) : 0}
      <div class="bg-white rounded-2xl p-6 shadow-sm text-center space-y-4">
        <p class="text-sm font-medium text-gray-700">Importing… {done} / {total}</p>
        <div class="w-full bg-gray-100 rounded-full h-3">
          <div
            class="bg-brand-500 h-3 rounded-full transition-all duration-300"
            style="width: {pct}%"
          ></div>
        </div>
        {#if photoFail > 0}
          <p class="text-xs text-yellow-600">{photoFail} photos could not be downloaded</p>
        {/if}
        <p class="text-xs text-gray-400">Do not close this page</p>
      </div>

    <!-- DONE: results -->
    {:else if state === 'done'}
      <div class="bg-white rounded-2xl p-6 shadow-sm text-center space-y-3">
        <div class="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto">
          <svg class="w-7 h-7 text-green-600" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-gray-800">Import complete</h2>
        <div class="space-y-1 text-sm text-gray-600">
          <p>{importedCount} items imported</p>
          {#if duplicateCount}<p class="text-gray-400">{duplicateCount} duplicates skipped</p>{/if}
          {#if photoFail}<p class="text-yellow-600">{photoFail} photos failed — add them manually</p>{/if}
          {#if errored}<p class="text-red-500">{errored} rows errored</p>{/if}
        </div>
        <button
          on:click={() => goto(`${base}/gallery`, { replaceState: true })}
          class="w-full mt-2 rounded-xl bg-brand-500 text-white py-3 text-sm font-semibold hover:bg-brand-600 transition"
        >
          Open Gallery
        </button>
      </div>
    {/if}

  </main>
</div>
