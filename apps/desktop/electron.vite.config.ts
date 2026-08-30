import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()]
  },
  preload: {
    plugins: [externalizeDepsPlugin()]
  },
  renderer: {
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src/renderer/src'),
        '@ui': resolve(__dirname, 'src/renderer/src/ui'),
        '@application': resolve(__dirname, 'src/renderer/src/application'),
        '@domain': resolve(__dirname, 'src/renderer/src/domain'),
        '@infrastructure': resolve(__dirname, 'src/renderer/src/infrastructure')
      }
    },
    plugins: [vue()]
  }
})
