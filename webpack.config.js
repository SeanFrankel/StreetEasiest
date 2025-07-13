const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const sass = require('sass');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

const options = {
    entry: {
        'main': `./static_src/javascript/main.js`,
    },
    resolve: {
        extensions: ['.js'],
    },
    output: {
        path: path.resolve(`./static_compiled/`),
        filename: 'js/[name].js',
        clean: true,
    },
    plugins: [
        new CopyPlugin({
            patterns: [
                {
                    from: path.resolve(`./static_src/images`),
                    to: path.resolve(`./static_compiled/images`),
                }
            ],
        }),
        new MiniCssExtractPlugin({
            filename: 'css/[name].css',
        }),
        new CleanWebpackPlugin()
    ],
    module: {
        rules: [
            {
                test: /\.(scss|css)$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    {
                        loader: 'css-loader',
                        options: {
                            sourceMap: true,
                        },
                    },
                    {
                        loader: 'postcss-loader',
                        options: {
                            sourceMap: true,
                            postcssOptions: {
                                plugins: [
                                    'tailwindcss',
                                    'autoprefixer',
                                    'postcss-custom-properties',
                                    ['cssnano', { preset: 'default' }],
                                ],
                            },
                        },
                    },
                    {
                        loader: 'sass-loader',
                        options: {
                            sourceMap: true,
                            implementation: sass,
                            sassOptions: {
                                outputStyle: 'compressed',
                            },
                        },
                    },
                ],
            },
            {
                test: /\.(ttf|woff|woff2)$/,
                exclude: /node_modules/,
                type: 'asset/resource',
                generator: {
                    filename: 'fonts/[name][ext]'
                }
            }
        ],
    },
    externals: {
        // gettext: 'gettext',
    },
};

const webpackConfig = (environment, argv) => {
    const isProduction = argv.mode === 'production';

    options.mode = isProduction ? 'production' : 'development';

    if (!isProduction) {
        const stats = {
            builtAt: false,
            chunks: false,
            hash: false,
            colors: true,
            reasons: false,
            version: false,
            modules: false,
            performance: false,
            children: false,
            assets: false,
        };

        options.stats = stats;
        options.devtool = 'inline-source-map';

        options.devServer = {
            compress: true,
            overlay: true,
            clientLogLevel: 'error',
            contentBase: false,
            writeToDisk: true,
            host: '0.0.0.0',
            allowedHosts: [],
            port: 3000,
            publicPath: '/static/',
            index: '',
            stats,
            proxy: {
                context: () => true,
                target: 'http://localhost:8000',
            },
        };
    }

    return options;
};

module.exports = webpackConfig;
