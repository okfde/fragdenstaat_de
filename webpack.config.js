const path = require('path')
const fs = require('fs')
const childProcess = require('child_process')

const UglifyJsPlugin = require('uglifyjs-webpack-plugin')
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const WriteFilePlugin = require('write-file-webpack-plugin')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const VueLoaderPlugin = require('vue-loader/lib/plugin')
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin

const webpack = require('webpack')

const devMode = process.env.NODE_ENV !== 'production'
const ASSET_PATH = process.env.ASSET_PATH || '/static/js/';

const ENTRY = {
  main: ['./frontend/javascript/main.ts'],
  food: 'froide_food/frontend/javascript/main.js',
  foodreport: 'froide_food/frontend/javascript/report.js',
  payment: 'froide_payment/frontend/javascript/payment.ts',
  publicbody: 'froide/frontend/javascript/publicbody.js',
  makerequest: 'froide/frontend/javascript/makerequest.js',
  request: './frontend/javascript/request.ts',
  redact: 'froide/frontend/javascript/redact.js',
  tagautocomplete: 'froide/frontend/javascript/tagautocomplete.ts',
  docupload: 'froide/frontend/javascript/docupload.js',
  geomatch: 'froide/frontend/javascript/geomatch.js',
  messageredaction: 'froide/frontend/javascript/messageredaction.js',
  publicbodyupload: 'froide/frontend/javascript/publicbodyupload.js',
  filingcabinet: 'filingcabinet/frontend/javascript/filingcabinet.js',
  document: 'froide/frontend/javascript/document.js'
}

const EXCLUDE_CHUNKS = [
  'main', 'tagautocomplete'
].join('|')

const ENTRY_LIST = []
let CHUNK_LIST = []
for (let key in ENTRY) {
  ENTRY_LIST.push('(' + key + '\\.(css|js))')
  if (EXCLUDE_CHUNKS.indexOf(key) !== -1) { continue }
  CHUNK_LIST.push(key)
}
CHUNK_LIST = CHUNK_LIST.join('|')

const BUILD_FILE_REGEX = new RegExp('.*/(' + ENTRY_LIST.join('|') + ')$')

const config = {
  entry: ENTRY,
  output: {
    path: path.resolve(__dirname, 'fragdenstaat_de/theme/static/js'),
    publicPath: process.env.NODE_ENV === 'production' ? ASSET_PATH : (
      process.env.WEBPACK_DEV_SERVER ? 'http://localhost:8080/static/js/' : '/static/js/'
    ),
    filename: '[name].js',
    chunkFilename: '[name].js',
    library: ['Froide', 'components', '[name]'],
    libraryTarget: 'umd'
  },
  devtool: 'inline-source-map', // any "source-map"-like devtool is possible
  node: false,
  devServer: {
    contentBase: path.resolve(__dirname, 'fragdenstaat_de/theme'),
    headers: { 'Access-Control-Allow-Origin': '*' },
    port: 8080,
    hot: true,
    hotOnly: true,
    proxy: {
      '/static': {
        target: 'http://localhost:8000',
        bypass: function (req, res, proxyOptions) {
          var urlPath = req.path.substring(1)
          urlPath = path.resolve(__dirname, 'fragdenstaat_de/theme', urlPath)
          if (fs.existsSync(urlPath)) {
            // Path exists in local folder
            if (urlPath.match(BUILD_FILE_REGEX)) {
              // console.log('Skip path in favor of hot reload:', urlPath)
              return false
            }
            // console.log('Load path:', urlPath)
            return req.path
          }
          // use proxy
          // console.log('Proxy this:', urlPath)
          return null
        }
      }
    }
  },
  resolve: {
    modules: [
      'fragdenstaat_de/theme/static',
      path.resolve(__dirname, 'node_modules'), // Resolve all dependencies first in fds node_modules
      './node_modules'
    ],
    extensions: ['.js', '.ts', '.vue', '.json'],
    alias: {
      'vue$': 'vue/dist/vue.runtime.esm.js',
    }
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
            loader: 'awesome-typescript-loader',
            options: {
              appendTsSuffixTo: [/\.vue$/],
            }
          }
        ]
      },
      {
        test: /\.js$/,
        include: /(\/frontend|node_modules\/(bootstrap))/,
        use: {
          loader: 'babel-loader',
          options: {
            "presets": [
              ["@babel/preset-env", {
                "targets": {
                  "browsers": ["> 0.25%", "last 2 versions", "ie >= 11", "not dead"]
                }
              }]
            ],
            "plugins": ["@babel/plugin-proposal-object-rest-spread"]
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
              sourceMap: true
            }
          },
          {
            loader: 'postcss-loader',
            options: {
              ident: 'postcss',
              plugins: (loader) => [
                require('autoprefixer')()
              ]
            }
          },
          {
            loader: 'resolve-url-loader',
            options: {
              sourceMap: true
            }
          },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: true,
              includePaths: [
                'node_modules/'
              ]
            }
          }
        ]
      },
      {
        test: /(\.(woff2?|eot|ttf|otf)|font\.svg)(\?.*)?$/,
        loader: 'url-loader',
        options: {
          limit: 10000,
          name: '../fonts/[name].[ext]',
          emitFile: true,
          context: 'fragdenstaat_de/theme/static/js',
          publicPath: '/static/fonts/'
        }
      },
      {
        test: /\.(jpg|png|svg)$/,
        use: {
          loader: 'url-loader',
          options: {
            limit: 8192,
            name: '../img/[name].[ext]',
            emitFile: false,
            context: 'fragdenstaat_de/theme/static/js',
            publicPath: '/static/img/'
          }
        }
      }
    ]
  },
  plugins: [
    // new BundleAnalyzerPlugin({
    //   analyzerPort: 8905
    // }),
    new WriteFilePlugin(),
    new webpack.NamedModulesPlugin(),
    new VueLoaderPlugin(),
    new MiniCssExtractPlugin({
      // Options similar to the same options in webpackOptions.output
      // both options are optional
      filename: '../css/[name].css'
      // publicPath: '../../'
    }),
    new CopyWebpackPlugin([
      {from: 'node_modules/pdfjs-dist/build/pdf.worker.min.js'}
    ]),
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: `"${process.env.NODE_ENV}"`
      },
      global: 'window'
    })
  ],
  optimization: {
    minimizer: [
      new UglifyJsPlugin({
        cache: true,
        parallel: true,
        sourceMap: true // set to true if you want JS source maps
      })
    ].concat(!devMode ? [
      new OptimizeCssAssetsPlugin({
        assetNameRegExp: /\.css$/,
        cssProcessorOptions: {
          discardComments: { removeAll: true },
          mergeIdents: false,
          reduceIdents: false,
          zindex: false
        }
      })
    ] : []),
    splitChunks: {
      cacheGroups: {
        pdfjs: {
          test: /[\\/]node_modules[\\/](pdfjs-dist\/build\/pdf\.js)/,
          name: 'pdfjs',
          chunks: 'all'
        },
        common: {
          test: /[\\/]node_modules[\\/]/,
          chunks (chunk) {
            return CHUNK_LIST.indexOf(chunk.name) !== -1
          },
          name: 'common',
          minChunks: 2,
          minSize: 0
        }
      }
    },
    occurrenceOrder: true
  }
}

module.exports = config
