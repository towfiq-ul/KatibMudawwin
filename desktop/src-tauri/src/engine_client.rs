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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SummarizeResult {
    pub date: String,
    pub summary_path: String,
}

#[derive(Debug)]
pub enum EngineError {
    Unreachable(String),
    BadStatus(u16),
    // (status code, message) -- carries the engine's {"error": "..."} body
    // (e.g. "no notes found for 20260825") instead of just a status code.
    Failed(u16, String),
}

impl std::fmt::Display for EngineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EngineError::Unreachable(msg) => {
                write!(f, "engine unreachable: {msg}")
            }
            EngineError::BadStatus(code) => write!(f, "engine returned status {code}"),
            EngineError::Failed(_, msg) => write!(f, "{msg}"),
        }
    }
}

pub struct EngineClient {
    client: reqwest::Client,
    // Summarization can run a local LLM inference (or, on first use,
    // download a ~2.3GB model) -- give it much more room than the quick
    // status/start/stop calls below.
    long_client: reqwest::Client,
    base_url: String,
}

impl EngineClient {
    pub fn new(host: &str, port: u16) -> Self {
        Self {
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(5))
                .build()
                .expect("failed to build http client"),
            long_client: reqwest::Client::builder()
                .timeout(Duration::from_secs(300))
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

    pub async fn summarize(&self, date: &str) -> Result<SummarizeResult, EngineError> {
        let res = self
            .long_client
            .post(format!("{}/summarize", self.base_url))
            .json(&serde_json::json!({ "date": date }))
            .send()
            .await
            .map_err(|e| EngineError::Unreachable(e.to_string()))?;

        let status = res.status();
        if !status.is_success() {
            let body: serde_json::Value = res.json().await.unwrap_or_default();
            let msg = body
                .get("error")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string())
                .unwrap_or_else(|| format!("engine returned status {}", status.as_u16()));
            return Err(EngineError::Failed(status.as_u16(), msg));
        }

        res.json::<SummarizeResult>()
            .await
            .map_err(|e| EngineError::Unreachable(e.to_string()))
    }
}
