use std::sync::OnceLock;

use serde::Deserialize;

// Single source of truth for the product name, shared with the engine
// (katib_mudawwin.branding) and the old dashboard (src/lib/branding.js).
// Embedded at compile time -- unlike the Python/JS versions, which read
// this file at runtime relative to their own location (fine there, since
// they always run from a repo checkout; wrong for a packaged/installed
// Tauri binary, which has no repo checkout to read from).
const BRANDING_JSON: &str = include_str!("../../../branding.json");

#[derive(Debug, Deserialize, Default)]
struct Branding {
    #[serde(rename = "displayName")]
    display_name: Option<String>,
    #[serde(rename = "configDirName")]
    config_dir_name: Option<String>,
}

static BRANDING: OnceLock<Branding> = OnceLock::new();

fn branding() -> &'static Branding {
    BRANDING.get_or_init(|| serde_json::from_str(BRANDING_JSON).unwrap_or_default())
}

pub fn display_name() -> String {
    branding()
        .display_name
        .clone()
        .unwrap_or_else(|| "KātibMudawwin".to_string())
}

pub fn config_dir_name() -> String {
    branding()
        .config_dir_name
        .clone()
        .unwrap_or_else(|| "katib-mudawwin".to_string())
}
