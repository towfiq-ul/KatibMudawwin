<script>
  import { onMount } from 'svelte';
  import { getConfig, saveConfig } from './api.js';

  let configPath = '';
  let currentConfig = {};
  let statusText = '';
  let values = {};

  // Same field set as the previous Express dashboard's config form.
  const fields = [
    { name: 'storage_dir', label: 'Storage directory', type: 'text' },
    {
      name: 'summarizer.provider',
      label: 'Summarizer provider',
      type: 'select',
      options: [
        { value: 'local', label: 'local (Phi-3, offline)' },
        { value: 'anthropic', label: 'anthropic (Claude API)' },
      ],
    },
    {
      name: 'summarizer.local.repo_id',
      label: 'Local model (Hugging Face repo id, GGUF)',
      type: 'text',
    },
    { name: 'summarizer.anthropic.model', label: 'Anthropic model', type: 'text' },
    {
      name: 'summarizer.anthropic.api_key',
      label: 'Anthropic API key (optional; overrides the env var, shown masked)',
      type: 'password',
      placeholder: 'leave blank to keep current value',
    },
    { name: 'whisper.model_size', label: 'Whisper model size', type: 'text' },
  ];

  function getPath(obj, dottedPath) {
    return dottedPath.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
  }

  function setPath(obj, dottedPath, value) {
    const keys = dottedPath.split('.');
    let node = obj;
    for (let i = 0; i < keys.length - 1; i++) {
      if (typeof node[keys[i]] !== 'object' || node[keys[i]] === null) node[keys[i]] = {};
      node = node[keys[i]];
    }
    node[keys[keys.length - 1]] = value;
  }

  async function load() {
    const data = await getConfig();
    currentConfig = data.config || {};
    configPath = data.configPath;
    const next = {};
    for (const field of fields) {
      const value = getPath(currentConfig, field.name);
      if (value !== undefined) next[field.name] = value;
    }
    values = next;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    // Only touch fields the user actually filled in -- an empty password
    // field means "don't change the stored key", not "clear it" (mirrors
    // the previous dashboard form's exact behavior).
    for (const field of fields) {
      const value = values[field.name];
      if (!value) continue;
      setPath(currentConfig, field.name, value);
    }
    try {
      await saveConfig(currentConfig);
      statusText = 'Saved.';
    } catch (err) {
      statusText = 'Failed to save.';
    }
    setTimeout(() => {
      statusText = '';
    }, 3000);
  }

  onMount(load);
</script>

<p class="muted">File: {configPath}</p>
<form on:submit={handleSubmit}>
  {#each fields as field (field.name)}
    <label>
      {field.label}
      {#if field.type === 'select'}
        <select bind:value={values[field.name]}>
          {#each field.options as opt (opt.value)}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      {:else if field.type === 'password'}
        <input
          type="password"
          autocomplete="off"
          placeholder={field.placeholder || ''}
          bind:value={values[field.name]}
        />
      {:else}
        <input
          type="text"
          placeholder={field.placeholder || ''}
          bind:value={values[field.name]}
        />
      {/if}
    </label>
  {/each}
  <button type="submit">Save config</button>
  <span>{statusText}</span>
</form>

<style>
  label {
    display: block;
    margin-top: 0.75rem;
    font-size: 0.9rem;
  }

  input,
  select {
    width: 100%;
    padding: 0.3rem;
    margin-top: 0.2rem;
    box-sizing: border-box;
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
    margin-top: 1rem;
  }

  button:hover {
    background: #eee;
  }
</style>
