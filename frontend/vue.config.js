module.exports = {
  devServer: {
    port: 3002,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // pathRewrite: { // pathRewrite 通常不需要，除非后端路径不同
        //   '^/api': '/api' 
        // },
        ws: false, // 如果你不用 WebSocket，可以明确关闭
        buffer: false, // 尝试添加 buffer: false (可能不被 http-proxy-middleware 直接支持，但无害)
        onProxyRes: (proxyRes, req, res) => {
          // 尝试移除可能导致缓冲的头部
          delete proxyRes.headers['content-length'];
          delete proxyRes.headers['transfer-encoding'];
          // 强制设置头部暗示不要缓冲 (对某些代理有效)
          proxyRes.headers['X-Accel-Buffering'] = 'no'; 
          // console.log(`代理响应头 (路径: ${req.url}):`, JSON.stringify(proxyRes.headers)); // 注释掉日志
        },
        onProxyReq: (proxyReq, req) => {
          // 可以保留日志方便调试
          // console.log(`代理请求: ${req.method} ${req.url} -> ${proxyReq.path}`); // 注释掉日志
        },
        onError: (err, req, res) => {
          console.error('代理错误:', err);
          // 发送错误响应给客户端
          res.writeHead(500, {
            'Content-Type': 'text/plain',
          });
          res.end('Proxy Error: Could not connect to backend.');
        }
      }
    },
  },
  // 添加publicPath配置，确保资源加载路径正确
  publicPath: '/',
  // 添加生产模式配置
  productionSourceMap: false // 关闭生产环境的source map
} 