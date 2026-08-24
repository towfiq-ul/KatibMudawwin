import { invoke } from '@tauri-apps/api/core';

export function getBranding() {
  return invoke('get_branding');
}

export function getEngineStatus() {
  return invoke('engine_status');
}

export function startEngine() {
  return invoke('engine_start');
}

export function stopEngine() {
  return invoke('engine_stop');
}

export function getNoteDates() {
  return invoke('get_notes_dates');
}

export function getNoteFiles(date) {
  return invoke('get_notes_files', { date });
}

export function getNoteContent(date, file) {
  return invoke('get_note_content', { date, file });
}

export function summarizeNotes(date) {
  return invoke('summarize_notes', { date });
}

export function getConfig() {
  return invoke('get_config');
}

export function saveConfig(config) {
  return invoke('save_config', { configIn: config });
}
