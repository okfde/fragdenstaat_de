import { resolve } from 'node:path'
import * as url from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import devManifest from 'vite-plugin-dev-manifest'
import { sentryVitePlugin } from '@sentry/vite-plugin'
import autoprefixer from 'autoprefixer'

const __dirname = url.fileURLToPath(new URL('.', import.meta.url))
const outputDir = resolve(__dirname, 'build')

// helper function to resolve scripts from froide projects
// (froide_campaign, list.js) => node_modules/froide_campaign/frontend/javascript/list.js
const r = (project, file) =>
  resolve(__dirname, 'node_modules', project, 'frontend', 'javascript', file)

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  // eslint-disable-next-line no-undef
  base: process.env.ASSET_PATH || '/static/',
  publicDir: false,
  resolve: {
    alias: {
      '~froide': resolve(__dirname, 'node_modules/froide')
    },
    dedupe: ['bootstrap', 'vue', 'pdfjs-dist'],
    extensions: ['.mjs', '.js', '.ts', '.vue', '.json']
  },
  build: {
    manifest: true,
    emptyOutDir: true,
    outDir: outputDir,
    sourcemap: true,
    rollupOptions: {
      input: {
        audio_player: './frontend/javascript/audio-player.ts',
        bookpub: './frontend/javascript/bookpub.js',
        campaign_list: r('froide_campaign', 'list.js'),
        campaign_map: r('froide_campaign', 'map.js'),
        campaign_questionaire: r('froide_campaign', 'questionaire.js'),
        document: r('froide', 'document.js'),
        docupload: r('froide', 'docupload.js'),
        exam_curriculum: r('froide_exam', 'curriculum.js'),
        fds_cms: './frontend/javascript/fds_cms.js',
        fileuploader: r('froide', 'fileuploader.js'),
        filingcabinet: r('@okfde/filingcabinet', 'filingcabinet.js'),
        food: r('froide_food', 'food.js'),
        foodreport: r('froide_food', 'report.js'),
        geomatch: r('froide', 'geomatch.js'),
        lawsuits_table: r('froide_legalaction', 'table.js'),
        legal_decisions_listfilter: r('froide_legalaction', 'listFilter.js'),
        main: './frontend/javascript/main.ts',
        makerequest: r('froide', 'makerequest.js'),
        messageredaction: r('froide', 'messageredaction.js'),
        moderation: r('froide', 'moderation.js'),
        payment: r('froide_payment', 'payment.ts'),
        proofupload: r('froide', 'proofupload.js'),
        publicbody: r('froide', 'publicbody.js'),
        publicbodyupload: r('froide', 'publicbodyupload.js'),
        redact: r('froide', 'redact.js'),
        request: r('froide', 'request.ts'),
        tagautocomplete: r('froide', 'tagautocomplete.ts'),
        vegacharts: './frontend/javascript/vegacharts.js'
      },
      output: {
        sourcemap: true,
        entryFileNames: '[name].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name.endsWith('.css')) {
            return 'css/[name][extname]'
          } else if (
            assetInfo.name.match(/(\.(woff2?|eot|ttf|otf)|font\.svg)(\?.*)?$/)
          ) {
            return 'fonts/[name][extname]'
          } else if (assetInfo.name.match(/\.(jpg|png|svg)$/)) {
            return 'img/[name][extname]'
          }

          console.log('assetInfo', assetInfo)
          return 'js/[name][extname]'
        }
      }
    }
  },
  server: {
    port: 5173,
    origin: 'http://127.0.0.1:5173',
    fs: { allow: ['..'] }
  },
  plugins: [
    vue(),
    devManifest(),
    mode === 'production' &&
      sentryVitePlugin({
        telemetry: false
      })
  ],
  css: {
    devSourcemap: true,
    postcss: {
      plugins: [autoprefixer]
    }
  }
}))
