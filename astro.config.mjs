import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://modeme-automobiles.com',
  outDir: './dist',
  publicDir: './public',
  root: '.',
  srcDir: './src',
  trailingSlash: 'always',
  integrations: [],
  vite: {
    ssr: {
      external: ['sharp']
    },
    preview: {
      allowedHosts: ['animation-worm-revised-honolulu.trycloudflare.com', '.trycloudflare.com']
    }
  }
});
