const path = require('path')
const LiveReloadPlugin = require('webpack-livereload-plugin')
const UglifyJsPlugin = require('uglifyjs-webpack-plugin')
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const webpack = require('webpack')

// Get Froide install path
const FROIDE_PATH = require('child_process').execSync(
  'python -c "import froide; print(froide.__path__[0])"'
).toString().trim()

console.log('Detected Froide at', FROIDE_PATH)

const config = {
  entry: {
    main: ['./frontend/javascript/main.js']
  },
  output: {
    path: path.resolve(__dirname, 'fragdenstaat_de/theme/static/js'),
    filename: '[name].js',
    library: ['Froide', 'components', '[name]'],
    libraryTarget: 'umd'
  },
  devtool: 'source-map', // any "source-map"-like devtool is possible
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
          MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader',
            options: {
              sourceMap: process.env.NODE_ENV !== 'production'
            }
          },
          // {
          //   loader: 'resolve-url-loader'
          // },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: process.env.NODE_ENV !== 'production',
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
          context: 'fragdenstaat_de/theme/static/',
          publicPath: ''
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
            // context: '',
            publicPath: ''
          }
        }
      }
    ]
  },
  plugins: [
    new LiveReloadPlugin(),
    new MiniCssExtractPlugin({
      // Options similar to the same options in webpackOptions.output
      // both options are optional
      filename: '../css/[name].css'
    }),
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: `"${process.env.NODE_ENV}"`
      }
    })
  ].concat(process.env.NODE_ENV === 'production' ? [
    // new UglifyJsPlugin({
    //   sourceMap: false,
    //   uglifyOptions: {
    //     ie8: true,
    //     ecma: 5,
    //     mangle: false
    //   }
    // }),
    new OptimizeCssAssetsPlugin({
      assetNameRegExp: /\.css$/,
      cssProcessorOptions: { discardComments: { removeAll: true } }
    })] : []),
  optimization: {
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
