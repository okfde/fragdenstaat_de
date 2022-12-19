import { resolve } from 'path'
import { defineConfig } from 'vite'
import devManifest from 'vite-plugin-dev-manifest'
import autoprefixer from 'autoprefixer'
import vue from '@vitejs/plugin-vue2'

const outputDir = resolve(__dirname, 'build')

// https://vitejs.dev/config/
export default defineConfig({
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
        campaign_list:
          'node_modules/froide_campaign/frontend/javascript/list.js',
        campaign_map: 'node_modules/froide_campaign/frontend/javascript/map.js',
        campaign_questionaire:
          'node_modules/froide_campaign/frontend/javascript/questionaire.js',
        document: 'node_modules/froide/frontend/javascript/document.js',
        docupload: 'node_modules/froide/frontend/javascript/docupload.js',
        exam_curriculum:
          'node_modules/froide_exam/frontend/javascript/curriculum.js',
        fds_cms: './frontend/javascript/fds_cms.js',
        fileuploader: 'node_modules/froide/frontend/javascript/fileuploader.js',
        filingcabinet:
          'node_modules/@okfde/filingcabinet/frontend/javascript/filingcabinet.js',
        food: 'node_modules/froide_food/frontend/javascript/food.js',
        foodreport: 'node_modules/froide_food/frontend/javascript/report.js',
        geomatch: 'node_modules/froide/frontend/javascript/geomatch.js',
        lawsuits_table:
          'node_modules/froide_legalaction/frontend/javascript/table.js',
        legal_decisions_listfilter:
          'node_modules/froide_legalaction/frontend/javascript/listFilter.js',
        main: './frontend/javascript/main.ts',
        makerequest: 'node_modules/froide/frontend/javascript/makerequest.js',
        messageredaction:
          'node_modules/froide/frontend/javascript/messageredaction.js',
        moderation: 'node_modules/froide/frontend/javascript/moderation.js',
        payment: 'node_modules/froide_payment/frontend/javascript/payment.ts',
        publicbody: 'node_modules/froide/frontend/javascript/publicbody.js',
        publicbodyupload:
          'node_modules/froide/frontend/javascript/publicbodyupload.js',
        redact: 'node_modules/froide/frontend/javascript/redact.js',
        request: 'node_modules/froide/frontend/javascript/request.ts',
        tagautocomplete:
          'node_modules/froide/frontend/javascript/tagautocomplete.ts',
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
  plugins: [vue(), devManifest()],
  css: {
    postcss: {
      plugins: [autoprefixer]
    }
  }
})
