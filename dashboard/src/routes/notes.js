const express = require('express');
const fs = require('fs');
const path = require('path');

const { getStorageDir } = require('../lib/config');

const router = express.Router();

// Meeting ids are exactly the timestamp prefix the engine generates
// (YYYY-MM-DD_HH-MM-SS) -- validating against this before building a file
// path prevents path traversal via a crafted :id.
const MEETING_ID_PATTERN = /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$/;

function listMeetings() {
  const storageDir = getStorageDir();
  if (!fs.existsSync(storageDir)) return [];
  const files = fs.readdirSync(storageDir);
  return files
    .filter((f) => f.endsWith('_meeting-notes.txt'))
    .map((f) => {
      const id = f.slice(0, -'_meeting-notes.txt'.length);
      const summaryFile = `${id}_summary.txt`;
      return { id, hasSummary: files.includes(summaryFile) };
    })
    .filter((m) => MEETING_ID_PATTERN.test(m.id))
    .sort((a, b) => (a.id < b.id ? 1 : -1));
}

router.get('/api/meetings', (req, res) => {
  res.json(listMeetings());
});

router.get('/api/meetings/:id', (req, res) => {
  const { id } = req.params;
  if (!MEETING_ID_PATTERN.test(id)) {
    return res.status(400).json({ error: 'invalid meeting id' });
  }

  const storageDir = getStorageDir();
  const transcriptPath = path.join(storageDir, `${id}_meeting-notes.txt`);
  const summaryPath = path.join(storageDir, `${id}_summary.txt`);

  if (!fs.existsSync(transcriptPath)) {
    return res.status(404).json({ error: 'meeting not found' });
  }

  res.json({
    id,
    transcript: fs.readFileSync(transcriptPath, 'utf8'),
    summary: fs.existsSync(summaryPath) ? fs.readFileSync(summaryPath, 'utf8') : null,
  });
});

module.exports = router;
