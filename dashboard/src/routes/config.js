const express = require('express');

const { loadConfig, saveConfig, maskSecret } = require('../lib/config');

const router = express.Router();

router.get('/api/config', (req, res) => {
  const { configPath, raw } = loadConfig();
  const masked = JSON.parse(JSON.stringify(raw));
  const apiKey = masked?.summarizer?.anthropic?.api_key;
  if (apiKey) masked.summarizer.anthropic.api_key = maskSecret(apiKey);
  res.json({ configPath, config: masked });
});

// Full-replace semantics (not a partial merge): the dashboard loads the
// current config, edits it client-side, and posts the whole object back.
// This sidesteps any ambiguity about how to merge nested keys.
//
// The GET above masks summarizer.anthropic.api_key, and the dashboard form has
// no input for it, so an unrelated edit's save would otherwise write that
// mask string over the real key. If the incoming value still matches the
// mask of what's on disk, keep the real on-disk key instead.
router.post('/api/config', (req, res) => {
  const config = req.body;
  if (typeof config !== 'object' || config === null || Array.isArray(config)) {
    return res.status(400).json({ error: 'body must be a JSON object' });
  }
  const existingKey = loadConfig().raw?.summarizer?.anthropic?.api_key;
  const incomingKey = config?.summarizer?.anthropic?.api_key;
  if (existingKey && incomingKey === maskSecret(existingKey)) {
    config.summarizer.anthropic.api_key = existingKey;
  }
  saveConfig(config);
  res.json({ config });
});

module.exports = router;
