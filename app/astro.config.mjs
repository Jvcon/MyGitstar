// @ts-check
import { defineConfig } from "astro/config";

import starlight from "@astrojs/starlight";

import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
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
          ],
        },
      ],
      customCss: [
        './src/styles/global.css',
      ],
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
});
