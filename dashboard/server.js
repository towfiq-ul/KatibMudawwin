const express = require('express');
const path = require('path');

const notesRouter = require('./src/routes/notes');
const configRouter = require('./src/routes/config');
const engineRouter = require('./src/routes/engine');
const brandingRouter = require('./src/routes/branding');
const { DISPLAY_NAME } = require('./src/lib/branding');

const app = express();
const PORT = process.env.PORT || 5173;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.use(notesRouter);
app.use(configRouter);
app.use(engineRouter);
app.use(brandingRouter);

app.listen(PORT, () => {
  console.log(`${DISPLAY_NAME} dashboard listening on http://localhost:${PORT}`);
});
