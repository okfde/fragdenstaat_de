const path = require('path')

const TerserPlugin = require('terser-webpack-plugin')
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const { CleanWebpackPlugin } = require('clean-webpack-plugin')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const VueLoaderPlugin = require('vue-loader/lib/plugin')

const webpack = require('webpack')

const devMode = process.env.NODE_ENV !== 'production'
const ASSET_PATH = process.env.ASSET_PATH || '/static/js/'

const ENTRY = {
  main: ['./frontend/javascript/main.ts'],
  document: 'froide/frontend/javascript/document.js',
  docupload: 'froide/frontend/javascript/docupload.js',
  exam_curriculum: 'froide_exam/frontend/javascript/curriculum.js',
  fds_cms: './frontend/javascript/fds_cms.js',
  filingcabinet: '@okfde/filingcabinet/frontend/javascript/filingcabinet.js',
  food: 'froide_food/frontend/javascript/main.js',
  foodreport: 'froide_food/frontend/javascript/report.js',
  geomatch: 'froide/frontend/javascript/geomatch.js',
  makerequest: 'froide/frontend/javascript/makerequest.js',
  messageredaction: 'froide/frontend/javascript/messageredaction.js',
  moderation: 'froide/frontend/javascript/moderation.js',
  payment: 'froide_payment/frontend/javascript/payment.ts',
  publicbody: 'froide/frontend/javascript/publicbody.js',
  publicbodyupload: 'froide/frontend/javascript/publicbodyupload.js',
  fileuploader: 'froide/frontend/javascript/fileuploader.js',
  redact: 'froide/frontend/javascript/redact.js',
  request: './frontend/javascript/request.ts',
  'request-alpha': ['froide/frontend/javascript/alpha/request-alpha.ts'],
  tagautocomplete: 'froide/frontend/javascript/tagautocomplete.ts',
  campaign_map: 'froide_campaign/frontend/javascript/map.js',
  campaign_questionaire: 'froide_campaign/frontend/javascript/questionaire.js',
  campaign_list: 'froide_campaign/frontend/javascript/list.js',
  lawsuits_table: 'froide_legalaction/frontend/javascript/table.js',
  legal_decisions_listfilter: 'froide_legalaction/frontend/javascript/listFilter.js',
  vegacharts: './frontend/javascript/vegacharts.js'
}

const EXCLUDE_CHUNKS = [
  'main', 'tagautocomplete', 'request-alpha'
].join('|')

const EXCLUDE_MODULES_FROM_COMMON = [
  'leaflet', 'exif', 'uppy', 'tus-js', 'bootstrap-native'
]

const ENTRY_LIST = []
let CHUNK_LIST = []
for (const key in ENTRY) {
  ENTRY_LIST.push('(' + key + '\\.(css|js))')
  if (EXCLUDE_CHUNKS.indexOf(key) !== -1) { continue }
  CHUNK_LIST.push(key)
}
CHUNK_LIST = CHUNK_LIST.join('|')

const config = {
  entry: ENTRY,
  output: {
    path: path.resolve(__dirname, 'fragdenstaat_de/theme/static/js'),
    publicPath: process.env.NODE_ENV === 'production'
      ? ASSET_PATH
      : (
          process.env.WEBPACK_DEV_SERVER ? 'http://localhost:8080/static/js/' : '/static/js/'
        ),
    filename: '[name].js',
    chunkFilename: '[name].js',
    library: {
      name: ['Froide', 'components', '[name]'],
      type: 'umd'
    },
    devtoolModuleFilenameTemplate: 'webpack://[namespace]/[resource-path]?[loaders]'
  },
  devtool: devMode ? 'inline-source-map' : 'source-map', // any "source-map"-like devtool is possible
  node: false,
  devServer: {
    // contentBase: path.resolve(__dirname, 'fragdenstaat_de/theme'),
    headers: { 'Access-Control-Allow-Origin': '*' },
    port: 8080,
    hot: true
  },
  resolve: {
    modules: [
      'fragdenstaat_de/theme/static',
      path.resolve(__dirname, 'node_modules'), // Resolve all dependencies first in fds node_modules
      './node_modules'
    ],
    extensions: ['.js', '.ts', '.vue', '.json'],
    alias: {
      vue$: 'vue/dist/vue.esm.js'
    },
    fallback: { zlib: false }
  },
  module: {
    rules: [
      {
        test: /bootstrap\.native$/,
        use: {
          loader: 'bootstrap.native-loader',
          options: {
            only: ['modal', 'dropdown', 'collapse', 'alert', 'tab', 'tooltip']
          }
        }
      },
      {
        test: /\.worker\.js$/,
        use: { loader: 'worker-loader' }
      },
      {
        test: /\.ts$/,
        exclude: /node_modules/,
        use: [
          // {
          //   loader: 'babel-loader',
          //   options: {
          //     presets: [path.resolve('./node_modules/babel-preset-env')],
          //     babelrc: false,
          //     plugins: [
          //       require('babel-plugin-transform-object-rest-spread')
          //     ]
          //   }
          // },
          {
            loader: 'ts-loader'
          }
        ]
      },
      {
        test: /\.js$/,
        include: /(\/frontend|node_modules\/(bootstrap))/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              ['@babel/preset-env', {
                targets: {
                  browsers: ['> 0.25%', 'last 2 versions', 'ie >= 11', 'not dead']
                }
              }]
            ],
            plugins: ['@babel/plugin-proposal-object-rest-spread']
          }
        }
      },
      {
        test: /\.vue/,
        use: {
          loader: 'vue-loader'
        }
      },
      {
        test: /\.s?css$/,
        use: [
          devMode ? 'vue-style-loader' : MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader',
            options: {
              sourceMap: devMode
            }
          },
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins: [
                  ['autoprefixer']
                ]
              }
            }
          },
          {
            loader: 'resolve-url-loader',
            options: {
              sourceMap: devMode
            }
          },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: devMode,
              sassOptions: {
                includePaths: [
                  'node_modules/'
                ]
              }
            }
          }
        ]
      },
      {
        test: /(\.(woff2?|eot|ttf|otf)|font\.svg)(\?.*)?$/,
        type: 'asset/resource',
        generator: {
          filename: '../fonts/[name][ext]'
        }
      },
      {
        test: /\.(jpg|png|svg)$/,
        type: 'asset',
        parser: {
          dataUrlCondition: {
            maxSize: 4 * 1024
          }
        },
        generator: {
          filename: '../img/[name][ext]'
        }
      }
    ]
  },
  plugins: [
    new CleanWebpackPlugin({
      dry: false,
      cleanStaleWebpackAssets: true,
      protectWebpackAssets: false,
      // relative to static/js directory
      cleanOnceBeforeBuildPatterns: ['**/*', '../css/*'],
      dangerouslyAllowCleanPatternsOutsideProject: true
    }),
    // new BundleAnalyzerPlugin({
    //   analyzerPort: 8905
    // }),
    new VueLoaderPlugin(),
    new MiniCssExtractPlugin({
      // Options similar to the same options in webpackOptions.output
      // both options are optional
      filename: '../css/[name].css'
      // publicPath: '../../'
    }),
    new CopyWebpackPlugin({
      patterns: [
        { from: 'node_modules/pdfjs-dist/build/pdf.worker.min.js' }
      ]
    }),
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: `"${process.env.NODE_ENV}"`
      },
      global: 'window'
    })
  ],
  optimization: {
    minimizer: !devMode
      ? [
          new TerserPlugin(),
          new CssMinimizerPlugin()
        ]
      : [],
    splitChunks: !devMode
      ? {
          cacheGroups: {
            pdfjs: {
              test: /[\\/]node_modules[\\/](pdfjs-dist\/build\/pdf\.js)/,
              name: 'pdfjs',
              chunks: 'all'
            },
            common: {
              test (mod/* , chunk */) {
                // Only node_modules are needed
                if (mod.context && !mod.context.includes('node_modules')) {
                  return false
                }
                // But not node modules that contain these key words in the path
                if (mod.context && EXCLUDE_MODULES_FROM_COMMON.some(str => mod.context.includes(str))) {
                  return false
                }
                return true
              },
              chunks (chunk) {
                return CHUNK_LIST.indexOf(chunk.name) !== -1
              },
              name: 'common',
              minChunks: 2,
              minSize: 0
            }
          }
        }
      : undefined
  }
}

module.exports = config
