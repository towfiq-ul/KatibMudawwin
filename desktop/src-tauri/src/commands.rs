// #[tauri::command] wrappers, one per dashboard route -- thin glue over
// config/notes/engine_client/branding. No capability entries are needed for
// these in capabilities/default.json: custom commands registered via
// invoke_handler are callable from the frontend by default in Tauri v2:
// the permissions system only gates plugin-provided commands.

use serde::Serialize;
use serde_json::Value;
use tauri::command;

use crate::{
    branding, config, engine_client::EngineClient, engine_client::EngineStatus,
    engine_client::SummarizeResult, notes,
};

#[command]
pub fn get_notes_dates() -> Vec<String> {
    let loaded = config::load_config();
    let storage_dir = config::get_storage_dir(&loaded.raw);
    notes::list_date_dirs(&storage_dir)
}

#[command]
pub fn get_notes_files(date: String) -> Result<Vec<String>, String> {
    let loaded = config::load_config();
    let storage_dir = config::get_storage_dir(&loaded.raw);
    notes::list_note_files(&storage_dir, &date).ok_or_else(|| "date not found".to_string())
}

#[command]
pub fn get_note_content(date: String, file: String) -> Result<String, String> {
    let loaded = config::load_config();
    let storage_dir = config::get_storage_dir(&loaded.raw);
    notes::read_note(&storage_dir, &date, &file).ok_or_else(|| "note not found".to_string())
}

#[derive(Serialize)]
pub struct ConfigResponse {
    #[serde(rename = "configPath")]
    config_path: String,
    config: Value,
}

#[command]
pub fn get_config() -> ConfigResponse {
    let loaded = config::load_config();
    let mut masked = loaded.raw.clone();
    if let Some(key) = masked
        .pointer("/summarizer/anthropic/api_key")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
    {
        if let Some(obj) = masked.pointer_mut("/summarizer/anthropic") {
            obj["api_key"] = Value::String(config::mask_secret(&key));
        }
    }
    ConfigResponse {
        config_path: loaded.config_path.to_string_lossy().to_string(),
        config: masked,
    }
}

// Full-replace semantics (not a merge), matching the old dashboard's
// POST /api/config: the frontend loads the current config, edits it
// client-side, and posts the whole object back. If the incoming
// summarizer.anthropic.api_key still matches the mask of what's on disk
// (i.e. the user didn't touch that field), keep the real on-disk key
// instead of overwriting it with the mask string.
#[command]
pub fn save_config(config_in: Value) -> Result<Value, String> {
    if !config_in.is_object() {
        return Err("body must be a JSON object".to_string());
    }
    let mut config_in = config_in;
    let existing = config::load_config().raw;
    if let Some(existing_key) = existing
        .pointer("/summarizer/anthropic/api_key")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
    {
        let incoming_key = config_in
            .pointer("/summarizer/anthropic/api_key")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());
        if incoming_key.as_deref() == Some(config::mask_secret(&existing_key).as_str()) {
            if let Some(obj) = config_in.pointer_mut("/summarizer/anthropic") {
                obj["api_key"] = Value::String(existing_key);
            }
        }
    }
    config::save_config(&config_in).map_err(|e| e.to_string())?;
    Ok(config_in)
}

#[command]
pub async fn engine_status() -> Result<EngineStatus, String> {
    let loaded = config::load_config();
    let (host, port) = config::get_server_host_port(&loaded.raw);
    EngineClient::new(&host, port)
        .get_status()
        .await
        .map_err(|e| e.to_string())
}

#[command]
pub async fn engine_start() -> Result<EngineStatus, String> {
    let loaded = config::load_config();
    let (host, port) = config::get_server_host_port(&loaded.raw);
    EngineClient::new(&host, port)
        .start()
        .await
        .map_err(|e| e.to_string())
}

#[command]
pub async fn engine_stop() -> Result<EngineStatus, String> {
    let loaded = config::load_config();
    let (host, port) = config::get_server_host_port(&loaded.raw);
    EngineClient::new(&host, port)
        .stop()
        .await
        .map_err(|e| e.to_string())
}

#[command]
pub async fn summarize_notes(date: String) -> Result<SummarizeResult, String> {
    let loaded = config::load_config();
    let (host, port) = config::get_server_host_port(&loaded.raw);
    EngineClient::new(&host, port)
        .summarize(&date)
        .await
        .map_err(|e| e.to_string())
}

#[command]
pub fn get_branding() -> Value {
    serde_json::json!({ "displayName": branding::display_name() })
}
