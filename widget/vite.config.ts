import { defineConfig, Plugin } from 'vite';
import { resolve } from 'path';
import fs from 'fs';

function htmlPlugin(): Plugin {
  return {
    name: 'copy-demo-html',
    closeBundle() {
      const srcPath = resolve(__dirname, 'index.html');
      const distPath = resolve(__dirname, 'dist/index.html');
      if (fs.existsSync(srcPath)) {
        let html = fs.readFileSync(srcPath, 'utf-8');
        // Replace dev module script with compiled production bundle
        html = html.replace(/type="module"\s+src="\/src\/main\.ts"/, 'src="/widget.js"');
        fs.writeFileSync(distPath, html, 'utf-8');
      }
    },
  };
}

export default defineConfig({
  plugins: [htmlPlugin()],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/main.ts'),
      name: 'RealEstateAIWidget',
      fileName: () => 'widget.js',
      formats: ['iife'],
    },
    rollupOptions: {
      output: {
        extend: true,
        inlineDynamicImports: true,
      },
    },
    minify: 'esbuild',
    sourcemap: true,
    emptyOutDir: true,
  },
});
