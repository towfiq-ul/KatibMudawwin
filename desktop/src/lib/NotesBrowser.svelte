<script>
  import { getNoteDates, getNoteFiles, getNoteContent } from './api.js';

  let open = false;
  let view = 'dates'; // 'dates' | 'files' | 'content'
  let dates = [];
  let files = [];
  let currentDate = '';
  let currentFile = '';
  let content = '';
  let loading = false;

  function formatDate(yyyymmdd) {
    return `${yyyymmdd.slice(0, 4)}-${yyyymmdd.slice(4, 6)}-${yyyymmdd.slice(6, 8)}`;
  }

  function formatNoteLabel(filename) {
    const m = filename.match(/^note_\d{8}_(\d{2})(\d{2})(\d{2})\.txt$/);
    return m ? `${m[1]}:${m[2]}:${m[3]}` : filename;
  }

  async function openModal() {
    open = true;
    await showDates();
  }

  async function showDates() {
    view = 'dates';
    loading = true;
    dates = await getNoteDates();
    loading = false;
  }

  async function showFiles(date) {
    currentDate = date;
    view = 'files';
    loading = true;
    files = await getNoteFiles(date);
    loading = false;
  }

  async function showContent(file) {
    currentFile = file;
    view = 'content';
    loading = true;
    content = await getNoteContent(currentDate, file);
    loading = false;
  }

  function close() {
    open = false;
  }
</script>

<button on:click={openModal}>Browse notes</button>

{#if open}
  <div class="modal-overlay">
    <div class="modal">
      <div class="modal-header">
        {#if view === 'files'}
          <button class="link-btn" on:click={showDates}>&larr; Back</button>
        {:else if view === 'content'}
          <button class="link-btn" on:click={() => showFiles(currentDate)}>&larr; Back</button>
        {/if}
        <h3>
          {#if view === 'dates'}
            Notes by date
          {:else if view === 'files'}
            {formatDate(currentDate)}
          {:else}
            {formatDate(currentDate)} {formatNoteLabel(currentFile)}
          {/if}
        </h3>
        <button class="close-btn" aria-label="Close" on:click={close}>&times;</button>
      </div>

      {#if view === 'content'}
        <pre>{content}</pre>
      {:else}
        <ul class="modal-list">
          {#if loading}
            <li class="muted">Loading...</li>
          {:else if view === 'dates' && dates.length === 0}
            <li class="muted">No notes yet.</li>
          {:else if view === 'files' && files.length === 0}
            <li class="muted">No notes for this day.</li>
          {:else if view === 'dates'}
            {#each dates as date}
              <li on:click={() => showFiles(date)}>{formatDate(date)}</li>
            {/each}
          {:else}
            {#each files as file}
              <li on:click={() => showContent(file)}>{formatNoteLabel(file)}</li>
            {/each}
          {/if}
        </ul>
      {/if}
    </div>
  </div>
{/if}

<style>
  button {
    cursor: pointer;
    padding: 0.4rem 0.9rem;
    border: 1px solid #999;
    border-radius: 4px;
    background: #f7f7f7;
  }

  button:hover {
    background: #eee;
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .modal {
    background: #fff;
    border-radius: 6px;
    width: min(32rem, 90vw);
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #eee;
  }

  .modal-header h3 {
    margin: 0;
    flex: 1;
    font-size: 1rem;
  }

  .link-btn {
    background: none;
    border: none;
    color: #06c;
    padding: 0;
    cursor: pointer;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.3rem;
    line-height: 1;
    cursor: pointer;
    color: #777;
    padding: 0 0.25rem;
  }

  .modal-list {
    list-style: none;
    margin: 0;
    padding: 0.5rem 0;
    overflow-y: auto;
  }

  .modal-list li {
    padding: 0.6rem 1rem;
    cursor: pointer;
  }

  .modal-list li:hover {
    background: #fafafa;
  }

  .muted {
    color: #777;
  }

  pre {
    white-space: pre-wrap;
    margin: 1rem;
    max-height: 60vh;
    overflow-y: auto;
  }
</style>
