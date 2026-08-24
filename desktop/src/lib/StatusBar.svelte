<script>
  import { onMount, onDestroy } from 'svelte';
  import { getEngineStatus, startEngine, stopEngine } from './api.js';

  let status = 'loading...';
  let statusClass = '';
  let errorText = '';
  let timer;

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
    await startEngine();
    refresh();
  }

  async function handleStop() {
    await stopEngine();
    refresh();
  }

  onMount(() => {
    refresh();
    timer = setInterval(refresh, 5000);
  });

  onDestroy(() => clearInterval(timer));
</script>

<p>Status: <span class={statusClass}>{status}</span></p>
<button on:click={handleStart}>Start recording</button>
<button on:click={handleStop}>Stop recording</button>
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
