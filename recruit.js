import express from 'express';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static(join(__dirname, 'frontend')));

app.listen(PORT, () => {
  console.log(`SolarSolutions frontend server running at http://localhost:${PORT}`);
  console.log('(The main application is served by Django on port 8000)');
});
