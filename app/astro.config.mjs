import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [
    starlight({
      favicon: '/images/favicon.png',
      title: '🌟 My GitStar',
      social: {
        github: 'https://github.com/Jvcon', // 请替换为您的用户名
      },
      
      // 3. 禁用 Starlight 默认的页面导航（因为我们将用自定义 Header 完全接管）
      sidebar: [],

      // 4. [核心] 声明我们要覆盖 Starlight 的默认 Header 组件
      components: {
        Header: './src/components/header.astro',
      },
    }),
    tailwind({
      // 禁用 Tailwind 的基础样式，以免与 Starlight 冲突
      applyBaseStyles: false,
    }),
  ],
});
