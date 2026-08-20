const express = require('express');

const engineClient = require('../lib/engineClient');

const router = express.Router();

function proxy(handler) {
  return async (req, res) => {
    try {
      res.json(await handler());
    } catch (err) {
      res.status(502).json({ error: 'engine unreachable', detail: err.message });
    }
  };
}

router.get('/api/engine/status', proxy(() => engineClient.getStatus()));
router.post('/api/engine/start', proxy(() => engineClient.start()));
router.post('/api/engine/stop', proxy(() => engineClient.stop()));

module.exports = router;
