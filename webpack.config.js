const path = require('path')
const fs = require('fs')
const UglifyJsPlugin = require('uglifyjs-webpack-plugin')
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const WriteFilePlugin = require('write-file-webpack-plugin')

const webpack = require('webpack')

// Get Froide install path
const FROIDE_PATH = require('child_process').execSync(
  'python -c "import froide; print(froide.__path__[0])"'
).toString().trim()

console.log('Detected Froide at', FROIDE_PATH)

const config = {
  entry: {
    main: [
      './frontend/javascript/main.js'
    ]
  },
  output: {
    path: path.resolve(__dirname, 'fragdenstaat_de/theme/static/js'),
    publicPath: process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8080/static/',
    filename: '[name].js',
    library: ['Froide', 'components', '[name]'],
    libraryTarget: 'umd'
  },
  devtool: 'source-map', // any "source-map"-like devtool is possible
  devServer: {
    contentBase: path.resolve(__dirname, 'fragdenstaat_de/theme'),
    headers: { 'Access-Control-Allow-Origin': '*' },
    hot: true,
    proxy: {
      '/static': {
        target: 'http://localhost:8000',
        bypass: function (req, res, proxyOptions) {
          var urlPath = req.path.substring(1)
          urlPath = path.resolve(__dirname, 'fragdenstaat_de/theme', urlPath)
          if (fs.existsSync(urlPath)) {
            return req.path
          }
          return false
        }
      }
    }
  },
  resolve: {
    modules: [
      'fragdenstaat_de/theme/static',
      path.resolve(FROIDE_PATH, 'static'),
      'node_modules'
    ],
    extensions: ['.js', '.json'],
    alias: {
      'vue$': 'vue/dist/vue.esm.js',
      'froide': path.resolve(FROIDE_PATH, '..'),
      'froide_static': path.resolve(FROIDE_PATH, 'static')
    }
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        include: /(\/frontend|node_modules\/(bootstrap))/,
        use: {
          loader: 'babel-loader'
        }
      },
      {
        test: /\.scss$/,
        use: [
          'css-hot-loader',
          MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader',
            options: {
              sourceMap: true
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
    new WriteFilePlugin(),
    new webpack.NamedModulesPlugin(),
    new MiniCssExtractPlugin({
      // Options similar to the same options in webpackOptions.output
      // both options are optional
      filename: '../css/[name].css'
      // publicPath: '../../'
    }),
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: `"${process.env.NODE_ENV}"`
      }
    })
  ],
  optimization: {
    minimizer: [
      new UglifyJsPlugin({
        cache: true,
        parallel: true,
        sourceMap: true // set to true if you want JS source maps
      })
    ].concat(process.env.NODE_ENV === 'production' ? [
      new OptimizeCssAssetsPlugin({
        assetNameRegExp: /\.css$/,
        cssProcessorOptions: {
          discardComments: { removeAll: true }
        }
      })
    ] : []),
    splitChunks: {
      cacheGroups: {
        styles: {
          name: 'styles',
          test: /\.css$/,
          chunks: 'all',
          enforce: true
        }
      }
    }
  }
}

module.exports = config
