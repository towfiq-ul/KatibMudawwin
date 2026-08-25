// Ported from dashboard/src/routes/notes.js. Validating `date`/`file`
// before building any filesystem path is the path-traversal guard, not
// incidental -- keep that order.

use std::fs;
use std::path::Path;

// date: exactly 8 ASCII digits (YYYYMMDD).
pub fn is_valid_date(date: &str) -> bool {
    date.len() == 8 && date.bytes().all(|b| b.is_ascii_digit())
}

// file: note_YYYYMMDD_HHMMSS.txt
pub fn is_valid_note_file(file: &str) -> bool {
    let Some(mid) = file.strip_prefix("note_").and_then(|s| s.strip_suffix(".txt")) else {
        return false;
    };
    // mid = "YYYYMMDD_HHMMSS" -> 8 digits + '_' + 6 digits = 15 chars.
    if mid.len() != 15 {
        return false;
    }
    let (date_part, rest) = mid.split_at(8);
    let Some(time_part) = rest.strip_prefix('_') else {
        return false;
    };
    date_part.bytes().all(|b| b.is_ascii_digit())
        && time_part.len() == 6
        && time_part.bytes().all(|b| b.is_ascii_digit())
}

// file: summary_note_YYYYMMDD.txt (written by /summarize, see
// summarize_notes.py's summarize_date()).
pub fn is_valid_summary_file(file: &str) -> bool {
    let Some(date_part) = file.strip_prefix("summary_note_").and_then(|s| s.strip_suffix(".txt")) else {
        return false;
    };
    date_part.len() == 8 && date_part.bytes().all(|b| b.is_ascii_digit())
}

fn is_readable_note_file(file: &str) -> bool {
    is_valid_note_file(file) || is_valid_summary_file(file)
}

pub fn list_date_dirs(storage_dir: &Path) -> Vec<String> {
    let notes_root = storage_dir.join("notes");
    let mut dates: Vec<String> = match fs::read_dir(&notes_root) {
        Ok(entries) => entries
            .filter_map(|e| e.ok())
            .filter(|e| e.path().is_dir())
            .filter_map(|e| e.file_name().into_string().ok())
            .filter(|name| is_valid_date(name))
            .collect(),
        Err(_) => Vec::new(),
    };
    dates.sort_by(|a, b| b.cmp(a));
    dates
}

pub fn list_note_files(storage_dir: &Path, date: &str) -> Option<Vec<String>> {
    if !is_valid_date(date) {
        return None;
    }
    let dir = storage_dir.join("notes").join(date);
    if !dir.exists() {
        return None;
    }
    let mut files: Vec<String> = fs::read_dir(&dir)
        .ok()?
        .filter_map(|e| e.ok())
        .filter_map(|e| e.file_name().into_string().ok())
        .filter(|name| is_readable_note_file(name))
        .collect();
    files.sort_by(|a, b| b.cmp(a));
    Some(files)
}

pub fn read_note(storage_dir: &Path, date: &str, file: &str) -> Option<String> {
    if !is_valid_date(date) || !is_readable_note_file(file) {
        return None;
    }
    let path = storage_dir.join("notes").join(date).join(file);
    fs::read_to_string(path).ok()
}
