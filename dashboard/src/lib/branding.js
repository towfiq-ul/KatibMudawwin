const fs = require('fs');
const path = require('path');

// Single source of truth for the product name, shared with the engine via
// branding.json at the repo root -- see engine/src/katib_mudawwin/branding.py.
const BRANDING_PATH = path.join(__dirname, '..', '..', '..', 'branding.json');

function load() {
  try {
    return JSON.parse(fs.readFileSync(BRANDING_PATH, 'utf8'));
  } catch (err) {
    return {};
  }
}

const branding = load();

module.exports = {
  DISPLAY_NAME: branding.displayName || 'KātibMudawwin',
  CONFIG_DIR_NAME: branding.configDirName || 'katib-mudawwin',
};
