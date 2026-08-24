<script>
  import { onMount, onDestroy } from 'svelte';
  import { getEngineStatus, startEngine, stopEngine } from './api.js';

  let status = 'loading...';
  let statusClass = '';
  let errorText = '';
  let timer;

  // Only one of Start/Stop is ever a valid action -- show just that one,
  // same as the tray icon's single toggling menu item (tray.rs). Anything
  // other than a confirmed "recording" status (idle, unreachable, loading)
  // defaults to showing Start.
  $: recording = status === 'recording';

  async function refresh() {
    try {
      const data = await getEngineStatus();
      status = data.status;
      statusClass = `status-${data.status}`;
      errorText = '';
    } catch (err) {
      status = 'unreachable';
      statusClass = '';
      errorText = "Could not reach the engine's status API -- is it running?";
    }
  }

  async function handleStart() {
    try {
      await startEngine();
      await refresh(); // only refresh (and let it own errorText) on success
    } catch (err) {
      errorText = 'Failed to start recording -- is the engine running?';
    }
  }

  async function handleStop() {
    try {
      await stopEngine();
      await refresh();
    } catch (err) {
      errorText = 'Failed to stop recording -- is the engine running?';
    }
  }

  onMount(() => {
    refresh();
    timer = setInterval(refresh, 5000);
  });

  onDestroy(() => clearInterval(timer));
</script>

<p>Status: <span class={statusClass}>{status}</span></p>
{#if recording}
  <button on:click={handleStop}>Stop recording</button>
{:else}
  <button on:click={handleStart}>Start recording</button>
{/if}
<p class="muted">{errorText}</p>

<style>
  .status-recording {
    color: #b00;
    font-weight: bold;
  }

  .status-idle {
    color: #555;
    font-weight: bold;
  }

  .muted {
    color: #777;
    font-size: 0.85rem;
  }

  button {
    cursor: pointer;
    padding: 0.4rem 0.9rem;
    border: 1px solid #999;
    border-radius: 4px;
    background: #f7f7f7;
    margin-right: 0.5rem;
  }

  button:hover {
    background: #eee;
  }
</style>
