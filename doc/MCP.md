
##相关MCP集成##


1.Fetch网页内容抓取

获取 MCP 服务器
一个提供网页内容抓取功能的模型上下文协议服务器。此服务器使大型语言模型能够从网页中检索和处理内容，并将 HTML 转换为 markdown 以便更容易地使用。

获取工具会截断响应，但通过使用 start_index 参数，您可以指定从何处开始提取内容。这让模型可以分块读取网页，直到找到所需的信息。

可用工具
fetch - 从互联网上抓取一个 URL 并将其内容作为 markdown 提取。
url (字符串, 必需): 要抓取的 URL
max_length (整数, 可选): 返回的最大字符数 (默认: 5000)
start_index (整数, 可选): 从此字符索引开始提取内容 (默认: 0)
raw (布尔值, 可选): 获取未经 markdown 转换的原始内容 (默认: false)
提示
fetch
抓取一个 URL 并将其内容作为 markdown 提取
参数:
url (字符串, 必需): 要抓取的 URL
安装
可选项：安装 node.js，这将导致 fetch 服务器使用一种更健壮的 HTML 简化器。

使用 uv（推荐）
当使用 uv 时不需要特定的安装步骤。我们将使用 uvx 直接运行 mcp-server-fetch。

使用 PIP
或者，您可以通过 pip 安装 mcp-server-fetch：

pip install mcp-server-fetch
安装后，您可以使用以下命令以脚本方式运行它：

python -m mcp_server_fetch
或通过npx启动
npx @modelcontextprotocol/inspector node build/index.js

配置
为 Claude.app 配置
在您的 Claude 设置中添加：

使用 uvx
"mcpServers": {
  "fetch": {
    "command": "uvx",
    "args": ["mcp-server-fetch"]
  }
}
使用 docker
"mcpServers": {
  "fetch": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "mcp/fetch"]
  }
}
使用 pip 安装
"mcpServers": {
  "fetch": {
    "command": "python",
    "args": ["-m", "mcp_server_fetch"]
  }
}
自定义 - robots.txt
默认情况下，如果请求来自模型（通过工具），则服务器会遵守网站的 robots.txt 文件；但如果请求是由用户发起的（通过提示），则不会遵守。通过在配置中的 args 列表里添加参数 --ignore-robots-txt 可以禁用这一行为。

自定义 - 用户代理
默认情况下，根据请求是否来自模型（通过工具）或由用户发起（通过提示），服务器将使用以下用户代理

ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)
或

ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)
通过在配置中的 args 列表里添加参数 --user-agent=YourUserAgent 可以自定义用户代理。

调试
您可以使用 MCP 检查器来调试服务器。对于 uvx 安装：

npx @modelcontextprotocol/inspector uvx mcp-server-fetch
如果您已将包安装在特定目录中或正在开发该包：

cd path/to/servers/src/fetch
npx @modelcontextprotocol/inspector uv run mcp-server-fetch
贡献
我们鼓励贡献以帮助扩展和完善 mcp-server-fetch。无论您是想添加新工具、增强现有功能还是改进文档，您的输入都是宝贵的。

有关其他 MCP 服务器和实现模式的例子，请参见： https://github.com/modelcontextprotocol/servers

欢迎提交拉取请求！请随时贡献新想法、错误修复或增强功能，让 mcp-server-fetch 更加强大和有用。

许可证
mcp-server-fetch 采用 MIT 许可证。这意味着您可以自由使用、修改和分发该软件，但需遵守 MIT 许可证的条款和条件。更多详情，请参阅项目仓库中的 LICENSE 文件。

2.