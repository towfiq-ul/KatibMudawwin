const fs = require('fs');
const os = require('os');
const path = require('path');
const yaml = require('js-yaml');

// Keep these two functions in sync with default_storage_dir() /
// default_config_path() in engine/src/zoom_notes_engine/config.py -- if the
// two diverge, the dashboard can end up reading a different directory than
// the engine writes to, with meetings recorded but never listed.
function defaultConfigPath() {
  const home = os.homedir();
  if (process.platform === 'win32') {
    return path.join(process.env.APPDATA || home, 'zoom-note-taker', 'config.yaml');
  }
  if (process.platform === 'darwin') {
    return path.join(home, 'Library', 'Application Support', 'zoom-note-taker', 'config.yaml');
  }
  return path.join(process.env.XDG_CONFIG_HOME || path.join(home, '.config'), 'zoom-note-taker', 'config.yaml');
}

function defaultStorageDir() {
  const home = os.homedir();
  if (process.platform === 'win32') return path.join(process.env.USERPROFILE || home, 'ZoomNotes');
  if (process.platform === 'darwin') return path.join(home, 'Documents', 'ZoomNotes');
  return path.join(home, 'ZoomNotes');
}

function expandHome(p) {
  if (!p) return p;
  if (p === '~') return os.homedir();
  if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
  return p;
}

function loadConfig() {
  const configPath = defaultConfigPath();
  let raw = {};
  if (fs.existsSync(configPath)) {
    raw = yaml.load(fs.readFileSync(configPath, 'utf8')) || {};
  }
  return { configPath, raw };
}

function getStorageDir() {
  const { raw } = loadConfig();
  return raw.storage_dir ? expandHome(raw.storage_dir) : defaultStorageDir();
}

function saveConfig(raw) {
  const configPath = defaultConfigPath();
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  fs.writeFileSync(configPath, yaml.dump(raw), 'utf8');
}

// Masks a secret for display, keeping only the last 4 characters visible.
// Deterministic so a round-tripped, unedited value can be recognized on save.
function maskSecret(value) {
  if (!value) return value;
  if (value.length <= 4) return '•'.repeat(value.length);
  return '•'.repeat(value.length - 4) + value.slice(-4);
}

module.exports = {
  defaultConfigPath,
  defaultStorageDir,
  expandHome,
  loadConfig,
  getStorageDir,
  saveConfig,
  maskSecret,
};
