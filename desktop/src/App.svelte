<script>
  import { onMount } from 'svelte';
  import { getCurrentWindow } from '@tauri-apps/api/window';
  import { getBranding } from './lib/api.js';
  import StatusBar from './lib/StatusBar.svelte';
  import NotesBrowser from './lib/NotesBrowser.svelte';
  import ConfigForm from './lib/ConfigForm.svelte';

  let displayName = 'KatibMudawwin';

  onMount(async () => {
    try {
      const branding = await getBranding();
      if (branding?.displayName) {
        displayName = branding.displayName;
        await getCurrentWindow().setTitle(displayName);
      }
    } catch (err) {
      // Keep the hardcoded fallback already in the markup.
    }
  });
</script>

<main>
  <h1>{displayName}</h1>

  <section>
    <h2>Engine status</h2>
    <StatusBar />
  </section>

  <section>
    <h2>Notes</h2>
    <NotesBrowser />
  </section>

  <section>
    <h2>Config</h2>
    <ConfigForm />
  </section>
</main>

<style>
  :global(body) {
    font-family: system-ui, sans-serif;
    max-width: 48rem;
    margin: 2rem auto;
    padding: 0 1rem;
    color: #222;
  }

  h1 {
    font-size: 1.4rem;
  }

  h2 {
    font-size: 1.1rem;
    margin-top: 2.5rem;
    border-bottom: 1px solid #ddd;
    padding-bottom: 0.3rem;
  }
</style>
