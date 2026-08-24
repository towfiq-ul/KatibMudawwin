// Replaces engine/src/katib_mudawwin/tray.py's pystray icon. Same four
// actions (Start/Stop recording, Show window, Quit), but driven over the
// engine's HTTP status API instead of in-process SessionRecorder calls,
// since the engine is now a separate process.
//
// Start/Stop recording is a single toggling menu item, not two separate
// items with one disabled -- only one action is ever valid at a time, so
// only one should ever be shown. tray.py polled recorder.state every 2s and
// called icon.update_menu() on change, because most pystray backends don't
// re-evaluate visible=/text predicates live (see that file's comment).
// Tauri v2's MenuItem supports live in-place set_text() with no rebuild
// needed, so the same polling loop here just relabels the one item.

use std::thread;
use std::time::Duration;

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    AppHandle, Manager, Wry,
};

use crate::{config, engine_client::EngineClient};

const POLL_INTERVAL: Duration = Duration::from_secs(2);

struct TrayMenuItems {
    toggle_recording: MenuItem<Wry>,
}

fn engine_client_from_config() -> EngineClient {
    let loaded = config::load_config();
    let (host, port) = config::get_server_host_port(&loaded.raw);
    EngineClient::new(&host, port)
}

fn is_recording(client: &EngineClient) -> bool {
    tauri::async_runtime::block_on(client.get_status())
        .map(|s| s.status == "recording")
        .unwrap_or(false)
}

fn label_for(recording: bool) -> &'static str {
    if recording {
        "Stop recording"
    } else {
        "Start recording"
    }
}

fn set_recording_state(items: &TrayMenuItems, recording: bool) {
    let _ = items.toggle_recording.set_text(label_for(recording));
}

pub fn setup_tray(app: &tauri::App) -> tauri::Result<()> {
    let toggle_i = MenuItem::with_id(app, "toggle_recording", label_for(false), true, None::<&str>)?;
    let open_i = MenuItem::with_id(app, "open", "Show KatibMudawwin", true, None::<&str>)?;
    let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&toggle_i, &open_i, &quit_i])?;

    app.manage(TrayMenuItems {
        toggle_recording: toggle_i.clone(),
    });

    TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("Katib Mudawwin")
        .icon(
            app.default_window_icon()
                .cloned()
                .expect("bundle.icon must be configured in tauri.conf.json"),
        )
        .on_menu_event(|app, event| handle_menu_event(app, event.id.as_ref()))
        .build(app)?;

    let handle = app.handle().clone();
    thread::spawn(move || poll_status_loop(handle));

    Ok(())
}

fn handle_menu_event(app: &AppHandle, id: &str) {
    match id {
        "toggle_recording" => {
            let app = app.clone();
            thread::spawn(move || {
                let client = engine_client_from_config();
                // Re-check current state right before acting, rather than
                // trusting the last poll (up to 2s stale), so a fast
                // double-click or a state change from elsewhere (the
                // desktop window, another client) can't fire the wrong
                // action.
                let _ = if is_recording(&client) {
                    tauri::async_runtime::block_on(client.stop())
                } else {
                    tauri::async_runtime::block_on(client.start())
                };
                refresh_menu(&app);
            });
        }
        "open" => {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        "quit" => {
            let app = app.clone();
            thread::spawn(move || {
                // Finalize any in-progress recording before exiting, same
                // as tray.py's on_exit.
                let _ = tauri::async_runtime::block_on(engine_client_from_config().stop());
                app.exit(0);
            });
        }
        _ => {}
    }
}

fn refresh_menu(app: &AppHandle) {
    if let Some(items) = app.try_state::<TrayMenuItems>() {
        set_recording_state(&items, is_recording(&engine_client_from_config()));
    }
}

fn poll_status_loop(app: AppHandle) {
    let mut last_recording: Option<bool> = None;
    loop {
        thread::sleep(POLL_INTERVAL);
        let recording = is_recording(&engine_client_from_config());
        if last_recording != Some(recording) {
            last_recording = Some(recording);
            if let Some(items) = app.try_state::<TrayMenuItems>() {
                set_recording_state(&items, recording);
            }
        }
    }
}
