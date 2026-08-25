// Third implementation of the config/storage-dir path resolution that
// already has to be kept in sync between engine/src/katib_mudawwin/config.py
// and dashboard/src/lib/config.js (both carry a comment saying so) -- keep
// this one in sync with both too, including the macOS/Windows branches
// neither the engine nor this app actually runs today (Linux-only, but the
// repo's existing convention is to implement all three branches anyway).

use std::path::PathBuf;

use serde_json::Value;

use crate::branding::config_dir_name;

pub fn default_config_path() -> PathBuf {
    let home = dirs::home_dir().unwrap_or_default();
    if cfg!(target_os = "windows") {
        let base = std::env::var_os("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|| home.clone());
        base.join(config_dir_name()).join("config.yaml")
    } else if cfg!(target_os = "macos") {
        home.join("Library")
            .join("Application Support")
            .join(config_dir_name())
            .join("config.yaml")
    } else {
        let base = std::env::var_os("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| home.join(".config"));
        base.join(config_dir_name()).join("config.yaml")
    }
}

pub fn default_storage_dir() -> PathBuf {
    let home = dirs::home_dir().unwrap_or_default();
    if cfg!(target_os = "windows") {
        std::env::var_os("USERPROFILE")
            .map(PathBuf::from)
            .unwrap_or_else(|| home.clone())
            .join("ZoomNotes")
    } else if cfg!(target_os = "macos") {
        home.join("Documents").join("ZoomNotes")
    } else {
        home.join("ZoomNotes")
    }
}

pub fn expand_home(p: &str) -> PathBuf {
    if p == "~" {
        if let Some(home) = dirs::home_dir() {
            return home;
        }
    } else if let Some(rest) = p.strip_prefix("~/") {
        if let Some(home) = dirs::home_dir() {
            return home.join(rest);
        }
    }
    PathBuf::from(p)
}

pub struct LoadedConfig {
    pub config_path: PathBuf,
    pub raw: Value,
}

pub fn load_config() -> LoadedConfig {
    let config_path = default_config_path();
    let raw = std::fs::read_to_string(&config_path)
        .ok()
        .and_then(|s| serde_yaml_ng::from_str::<Value>(&s).ok())
        .unwrap_or_else(|| Value::Object(Default::default()));
    LoadedConfig { config_path, raw }
}

pub fn get_storage_dir(raw: &Value) -> PathBuf {
    match raw.get("storage_dir").and_then(|v| v.as_str()) {
        Some(s) if !s.is_empty() => expand_home(s),
        _ => default_storage_dir(),
    }
}

pub fn get_server_host_port(raw: &Value) -> (String, u16) {
    let host = raw
        .pointer("/server/status_api_host")
        .and_then(|v| v.as_str())
        .unwrap_or("127.0.0.1")
        .to_string();
    let port = raw
        .pointer("/server/status_api_port")
        .and_then(|v| v.as_u64())
        .unwrap_or(8765) as u16;
    (host, port)
}

pub fn save_config(raw: &Value) -> std::io::Result<()> {
    let config_path = default_config_path();
    if let Some(parent) = config_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let yaml = serde_yaml_ng::to_string(raw)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;
    std::fs::write(config_path, yaml)
}

// Masks a secret for display, keeping only the last 4 characters visible.
// Deterministic so a round-tripped, unedited value can be recognized on
// save (see commands::save_config) -- ported verbatim from
// dashboard/src/lib/config.js's maskSecret().
pub fn mask_secret(value: &str) -> String {
    if value.is_empty() {
        return String::new();
    }
    let len = value.chars().count();
    if len <= 4 {
        return "\u{2022}".repeat(len);
    }
    let visible: String = value.chars().skip(len - 4).collect();
    format!("{}{}", "\u{2022}".repeat(len - 4), visible)
}
