const express = require('express');

const { DISPLAY_NAME } = require('../lib/branding');

const router = express.Router();

router.get('/api/branding', (req, res) => {
  res.json({ displayName: DISPLAY_NAME });
});

module.exports = router;
