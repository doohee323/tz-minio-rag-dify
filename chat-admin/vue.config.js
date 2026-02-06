const { defineConfig } = require('@vue/cli-service')
const path = require('path')
const fs = require('fs')

// Load env-frontend for VUE_APP_* (e.g. VUE_APP_CHAT_GATEWAY_API_KEY)
try {
  const envPath = path.resolve(__dirname, 'env-frontend')
  if (fs.existsSync(envPath)) {
    fs.readFileSync(envPath, 'utf8').split('\n').forEach(line => {
      const m = line.match(/^([^#=]+)=(.*)$/)
      if (m) {
        const key = m[1].trim()
        const val = m[2].trim().replace(/^["']|["']$/g, '')
        if (key.startsWith('VUE_APP_')) process.env[key] = val
      }
    })
  }
} catch (e) {}

const ENVIRONMENT = process.env.ENVIRONMENT || 'development'
const FRONTEND_PORT = process.env.FRONTEND_PORT || '8080'
const isProduction = ENVIRONMENT === 'production'

module.exports = defineConfig({
  transpileDependencies: true,
  outputDir: 'dist',
  publicPath: '/',
  filenameHashing: !isProduction,
  productionSourceMap: !isProduction,
  devServer: {
    host: '0.0.0.0',
    port: parseInt(FRONTEND_PORT),
    historyApiFallback: true,
    proxy: {
      // Admin APIs -> chat-admin (8000)
      '/v1/admin': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/docs': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/redoc': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/openapi.json': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/cache': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      // Chat APIs (conversations, chat, chat-token) -> chat-gateway (8088)
      '/v1': { target: 'http://127.0.0.1:8088', changeOrigin: true }
    }
  },
  configureWebpack: {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src')
      }
    }
  },
  chainWebpack: config => {
    config.plugin('html').tap(args => {
      args[0].templateParameters = {
        BASE_URL: process.env.BASE_URL || '/'
      }
      return args
    })
  }
})
