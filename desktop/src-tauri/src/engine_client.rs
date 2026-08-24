// Ported from dashboard/src/lib/engineClient.js -- talks to the engine's
// Flask status API over HTTP, since (unlike the old pystray tray, which
// called SessionRecorder methods in-process) both this app and the tray
// live in a separate process from the engine now.

use std::time::Duration;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineStatus {
    pub status: String,
    pub started_at: Option<String>,
    pub transcript_path: Option<String>,
    pub summary_path: Option<String>,
}

#[derive(Debug)]
pub enum EngineError {
    Unreachable(String),
    BadStatus(u16),
}

impl std::fmt::Display for EngineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EngineError::Unreachable(msg) => {
                write!(f, "engine unreachable: {msg}")
            }
            EngineError::BadStatus(code) => write!(f, "engine returned status {code}"),
        }
    }
}

pub struct EngineClient {
    client: reqwest::Client,
    base_url: String,
}

impl EngineClient {
    pub fn new(host: &str, port: u16) -> Self {
        Self {
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(5))
                .build()
                .expect("failed to build http client"),
            base_url: format!("http://{host}:{port}"),
        }
    }

    async fn request(&self, method: reqwest::Method, path: &str) -> Result<EngineStatus, EngineError> {
        let res = self
            .client
            .request(method, format!("{}{}", self.base_url, path))
            .send()
            .await
            .map_err(|e| EngineError::Unreachable(e.to_string()))?;
        if !res.status().is_success() {
            return Err(EngineError::BadStatus(res.status().as_u16()));
        }
        res.json::<EngineStatus>()
            .await
            .map_err(|e| EngineError::Unreachable(e.to_string()))
    }

    pub async fn get_status(&self) -> Result<EngineStatus, EngineError> {
        self.request(reqwest::Method::GET, "/status").await
    }

    pub async fn start(&self) -> Result<EngineStatus, EngineError> {
        self.request(reqwest::Method::POST, "/start").await
    }

    pub async fn stop(&self) -> Result<EngineStatus, EngineError> {
        self.request(reqwest::Method::POST, "/stop").await
    }
}
