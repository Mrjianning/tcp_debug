import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import fs from 'node:fs';
import path from 'node:path';

const projectRoot = path.resolve(__dirname, '../..');
const jsonDir = path.resolve(projectRoot, 'src/json');

function jsonTemplateMiddleware() {
  return {
    name: 'tcp-debug-json-template-middleware',
    configureServer(server) {
      server.middlewares.use('/json', (req, res, next) => {
        const urlPath = decodeURIComponent((req.url || '').split('?', 1)[0]);
        const safeName = path.basename(urlPath);
        const filePath = path.resolve(jsonDir, safeName);
        if (!filePath.startsWith(jsonDir) || !safeName.endsWith('.json')) {
          next();
          return;
        }
        if (!fs.existsSync(filePath)) {
          next();
          return;
        }
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(fs.readFileSync(filePath, 'utf8'));
      });
    },
  };
}

export default defineConfig({
  root: __dirname,
  plugins: [vue(), jsonTemplateMiddleware()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8080',
    },
  },
  build: {
    outDir: path.resolve(projectRoot, 'src/dist'),
    emptyOutDir: true,
  },
});
