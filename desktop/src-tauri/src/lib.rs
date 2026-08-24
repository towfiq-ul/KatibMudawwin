mod branding;
mod commands;
mod config;
mod engine_client;
mod notes;
mod tray;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // If the app is already running (hidden to tray) and the user
        // launches it again, show/focus the existing window instead of
        // starting a second instance.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .invoke_handler(tauri::generate_handler![
            commands::get_notes_dates,
            commands::get_notes_files,
            commands::get_note_content,
            commands::get_config,
            commands::save_config,
            commands::engine_status,
            commands::engine_start,
            commands::engine_stop,
            commands::get_branding,
        ])
        .setup(|app| {
            tray::setup_tray(app)?;
            Ok(())
        })
        // Closing the window (titlebar X) hides it to tray instead of
        // quitting the app -- Quit (tray menu only) is the sole real-exit
        // path, mirroring tray.py's pattern of the dashboard/tray staying
        // up as long as the engine is meant to be recording.
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
