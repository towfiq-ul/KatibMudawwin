// Prevents an extra console window from appearing on Windows in release
// builds (not shipped today -- Linux-only, see README -- but kept for
// parity with the rest of the codebase's "implement all OS branches" habit).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    katib_mudawwin_desktop_lib::run();
}
