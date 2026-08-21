const express = require('express');
const fs = require('fs');
const path = require('path');

const { getStorageDir } = require('../lib/config');

const router = express.Router();

const NOTES_ROOT = 'notes';

// Validating these before building a file path prevents path traversal via
// a crafted :date/:file -- only note_*.txt (the per-meeting transcript) is
// exposed here, not the shared per-day summary_note_*.txt.
const DATE_DIR_PATTERN = /^\d{8}$/;
const NOTE_FILE_PATTERN = /^note_\d{8}_\d{6}\.txt$/;

function listDateDirs() {
  const storageDir = getStorageDir();
  const notesRoot = path.join(storageDir, NOTES_ROOT);
  if (!fs.existsSync(notesRoot)) return [];
  return fs
    .readdirSync(notesRoot)
    .filter(
      (d) => DATE_DIR_PATTERN.test(d) && fs.statSync(path.join(notesRoot, d)).isDirectory()
    )
    .sort((a, b) => (a < b ? 1 : -1));
}

function listNoteFiles(date) {
  const storageDir = getStorageDir();
  const dirPath = path.join(storageDir, NOTES_ROOT, date);
  if (!fs.existsSync(dirPath)) return null;
  return fs
    .readdirSync(dirPath)
    .filter((f) => NOTE_FILE_PATTERN.test(f))
    .sort((a, b) => (a < b ? 1 : -1));
}

router.get('/api/notes', (req, res) => {
  res.json(listDateDirs());
});

router.get('/api/notes/:date', (req, res) => {
  const { date } = req.params;
  if (!DATE_DIR_PATTERN.test(date)) {
    return res.status(400).json({ error: 'invalid date' });
  }
  const files = listNoteFiles(date);
  if (files === null) {
    return res.status(404).json({ error: 'date not found' });
  }
  res.json(files);
});

router.get('/api/notes/:date/:file', (req, res) => {
  const { date, file } = req.params;
  if (!DATE_DIR_PATTERN.test(date) || !NOTE_FILE_PATTERN.test(file)) {
    return res.status(400).json({ error: 'invalid path' });
  }
  const storageDir = getStorageDir();
  const filePath = path.join(storageDir, NOTES_ROOT, date, file);
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'note not found' });
  }
  res.json({ content: fs.readFileSync(filePath, 'utf8') });
});

module.exports = router;
