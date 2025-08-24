// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import tailwindcss from "@tailwindcss/vite";
import AstroPWA from "@vite-pwa/astro";

export default defineConfig({
  base: process.env.BASE_URL || "/",
  integrations: [
    starlight({
      title: "🌟 My Gitstar",
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/Jvcon/MyGitstar",
        },
      ],
      sidebar: [
        {
          label: "Introduction",
          items: [
            // Starlight 根据文件自动生成侧边栏，或手动配置
            { label: "Getting Started", link: "/getting-started" },
            { label: "Starred Repositories", link: "/starred-repos" },
          ],
        },
      ],
      customCss: ["./src/styles/global.css"],
    }),
    AstroPWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico","robots.txt"],
            devOptions: {
        enabled: true,
      },
      manifest: {
        name: "My Gitstar",
        short_name: "Gitstar",
        description: "A web app to manage your starred repositories on GitHub.",
        theme_color: "#412E55",
        background_color: "#1C1425",
        display: "standalone",
        scope: process.env.BASE_URL || "/",
        start_url: process.env.BASE_URL || "/", 
        icons: [
          {
            src: "web-app-manifest-192x192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: 'any'
          },
          {
            src: "web-app-manifest-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: 'any'
          },
        ],
      },
      // 可选：如果需要更精细的 workbox 配置
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,json,webmanifest}"],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/data/'), // 缓存您的数据文件
            handler: 'NetworkFirst', // 网络优先，确保数据最新，但离线时可用
            options: {
              cacheName: 'api-data-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 // <== 1 day
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ],
      },
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
});
