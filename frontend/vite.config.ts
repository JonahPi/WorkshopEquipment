import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    sveltekit(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: { enabled: true },
      manifest: {
        name: 'Workshop Inventory',
        short_name: 'Workshop',
        description: 'Personal workshop box and drawer inventory',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#1e3a5f',
        start_url: '/WorkshopEquipment/',
        scope: '/WorkshopEquipment/',
        icons: [
          {
            src: '/WorkshopEquipment/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/WorkshopEquipment/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: '/WorkshopEquipment/icons/icon-180.png',
            sizes: '180x180',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /\/api\//,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'pocketbase-api',
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
            },
          },
          {
            urlPattern: /res\.cloudinary\.com/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'cloudinary-images',
              expiration: { maxEntries: 200, maxAgeSeconds: 86400 },
            },
          },
        ],
      },
    }),
  ],
});
