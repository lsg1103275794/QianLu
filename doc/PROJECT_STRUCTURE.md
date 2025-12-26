# GlyphMinds 项目结构

## 项目概述
这是一个LLM文本套用模板处理成结构化数据以及实现风格迁移的Web应用，分为前端和后端两部分。所有分析结果将保存到数据库以供风格迁移模块使用。

## 目录结构

```
GlyphMinds/
├── frontend/                 # 前端部分
│   ├── src/                  # 源代码目录
│   │   ├── assets/           # 静态资源
│   │   ├── components/       # 组件目录
│   │   │   ├── analysis/     # 分析相关组件
│   │   │   ├── api/          # API交互组件
│   │   │   ├── charts/       # 图表组件
│   │   │   ├── chat/         # 聊天界面组件
│   │   │   ├── common/       # 通用组件
│   │   │   ├── diagnostics/  # 诊断组件
│   │   │   ├── dialogs/      # 对话框组件
│   │   │   ├── report-generator/ # 报告生成组件
│   │   │   └── style/        # 样式组件
│   │   ├── i18n/             # 国际化文件
│   │   ├── layouts/          # 布局组件
│   │   ├── router/           # 路由配置
│   │   ├── services/         # 服务层
│   │   ├── utils/            # 工具函数
│   │   ├── views/            # 页面视图
│   │   ├── App.vue           # 根组件
│   │   ├── main.js           # 入口文件
│   │   └── shims-vue.d.ts    # Vue类型声明
│   ├── public/               # 公共资源目录
│   ├── dist/                 # 构建输出目录
│   ├── .eslintrc.js          # ESLint配置
│   ├── babel.config.js       # Babel配置
│   ├── package.json          # 项目依赖和脚本
│   ├── package-lock.json     # 依赖版本锁定
│   └── vue.config.js         # Vue配置
│
├── src/                      # 后端主要源代码
│   ├── api/                  # API模块
│   │   ├── routes/           # API路由
│   │   ├── models/           # API模型
│   │   ├── auth.py           # 认证逻辑
│   │   └── __init__.py       # 模块初始化
│   ├── config/               # 配置模块
│   │   └── __init__.py       # 模块初始化
│   ├── core/                 # 核心功能
│   │   ├── analyzers/        # 分析模块
│   │   ├── processing/       # 处理模块
│   │   ├── tasks/            # 任务定义
│   │   └── __init__.py       # 模块初始化
│   ├── data/                 # 数据处理
│   │   ├── style_analysis_cache/  # 风格分析缓存
│   │   ├── uploads/          # 上传文件存储
│   │   └── __init__.py       # 模块初始化
│   ├── database/             # 数据库交互
│   │   └── __init__.py       # 模块初始化
│   ├── providers/            # 服务提供者
│   │   ├── handlers/         # 处理器
│   │   └── __init__.py       # 模块初始化
│   ├── router/               # 路由管理
│   │   └── __init__.py       # 模块初始化
│   ├── services/             # 服务层
│   │   ├── hot_topics/       # 热门话题服务
│   │   ├── report_generator/ # 报告生成器
│   │   └── __init__.py       # 模块初始化
│   ├── utils/                # 工具函数
│   │   └── __init__.py       # 模块初始化
│   ├── validation/           # 数据验证
│   │   └── __init__.py       # 模块初始化
│   └── __init__.py           # 模块初始化
│
├── config/                   # 配置目录
│   ├── providers/            # 提供者配置
│   ├── prompt_templates/     # 提示模板
│   ├── promptPRO/            # 高级提示
│   ├── validation_rules/     # 验证规则
│   ├── __pycache__/          # Python缓存
│   ├── api_configs.json      # API配置
│   ├── app_config.yaml       # 应用配置
│   ├── configs.json          # 通用配置
│   ├── provider_config_template.json # 提供者配置模板
│   ├── providers_meta.json   # 提供者元数据
│   └── __init__.py           # 模块初始化
│
├── cache/                    # 缓存目录
├── data/                     # 数据目录
│   ├── logs/                 # 数据日志
│   ├── output/               # 输出数据
│   │   ├── datasets/         # 数据集
│   │   └── logs/             # 输出日志
│   └── uploads/              # 上传文件
│       └── temp/             # 临时文件
│
├── input/                    # 输入目录
├── logs/                     # 日志目录
├── output/                   # 输出目录
├── resources/                # 资源目录
│   └── dictionaries/         # 字典资源
├── Future/                   # 未来功能开发
├── __pycache__/              # Python缓存
├── .cache/                   # 缓存目录
│   ├── index/                # 索引缓存
│   ├── style_transfer/       # 风格转换缓存
│   ├── text_analysis/        # 文本分析缓存
│   └── text_processing/      # 文本处理缓存
├── .cursor/                  # Cursor IDE配置
│   └── rules/                # IDE规则
├── .vscode/                  # VSCode配置
├── conda_env/                # Conda环境配置
│
├── .gitignore                # Git忽略文件
├── .env                      # 环境变量配置
├── api_streaming_guide.md    # API流式传输指南
├── backend_main.py           # 后端主入口
├── development_log.md        # 开发日志
├── main.py                   # 主入口文件
├── MCP.md                    # MCP文档
├── PROJECT_STRUCTURE.md      # 当前文件
├── README.md                 # 项目说明
├── README_API_IMPROVEMENTS copy.md # API改进说明
├── README_API_IMPROVEMENTS.md # API改进说明
├── requirements.txt          # Python依赖
└── 数据研报功能的实现.md        # 数据研报功能实现文档
```

## 架构说明

### 前端架构
前端基于Vue.js框架开发，采用组件化的设计模式，分为以下几个主要部分：
- **视图层(views)**: 负责页面展示，包含各种功能页面
- **组件层(components)**: 封装可复用UI组件，按功能模块化组织
- **服务层(services)**: 处理API调用和数据逻辑，与后端交互
- **工具层(utils)**: 提供通用功能函数和辅助工具
- **路由(router)**: 管理应用路由和页面跳转
- **布局(layouts)**: 定义页面整体布局结构
- **国际化(i18n)**: 处理多语言支持

前端开发遵循以下原则：
- **组件化开发**: 采用模块分离创建功能组件的原则，每个文件专注于一个特定功能区域
- **结构化设计**: 使组件代码更清晰，样式更易于管理
- **可维护性**: 减少重复代码，公共样式可被多个组件共享
- **易于扩展**: 便于未来进行功能扩展和修改

### 后端架构
后端使用Python开发，主要分为以下模块：
- **API模块(api/)**: 处理前端请求，定义API路由和模型
- **核心功能(core/)**: 实现LLM文本处理和风格迁移的核心逻辑
  - **analyzers/**: 文本分析功能
  - **processing/**: 文本处理逻辑
  - **tasks/**: 任务定义和执行
- **数据处理(data/)**: 管理数据流和转换，处理上传文件
- **服务提供者(providers/)**: 连接不同的LLM服务，提供统一接口
- **配置系统(config/)**: 管理应用设置和API配置
- **数据库(database/)**: 存储分析结果供风格迁移模块使用
- **服务层(services/)**: 实现具体业务逻辑，如报告生成、热门话题分析等
- **工具函数(utils/)**: 提供通用功能和辅助函数
- **验证层(validation/)**: 处理数据验证和输入检查

### 配置系统
项目使用多层次的配置系统：
- **.env**: API配置的唯一真实来源，包含敏感信息
- **config/providers_meta.json**: 仅负责映射关系和前缀定义
- **config/app_config.yaml**: 应用级配置
- **config/prompt_templates/**: 存储LLM提示模板
- **config/validation_rules/**: 定义数据验证规则

### 数据流
1. 前端通过API请求后端服务
2. 后端接收请求，进行文本处理和风格分析
   - API层接收请求并路由到相应处理器
   - 核心处理模块进行文本分析和处理
   - 服务提供者连接LLM服务获取结果
3. 处理结果存储到数据库
4. 风格迁移模块使用存储的分析结果
5. 生成的报告和数据返回给前端展示

### 主要功能模块
1. **文本分析**: 分析输入文本的结构和内容
2. **模板套用**: 将文本应用到预定义模板
3. **风格迁移**: 调整文本风格以符合目标风格
4. **报告生成**: 生成结构化的数据研报
5. **热门话题分析**: 识别和分析热门话题

## 开发规范

1. **模块化开发**: 遵循"模块分离创建功能组件"的原则
2. **代码复用**: 任何新功能开发前先全局查找是否已有相关代码
3. **优先复用**: 已有功能优先复用，避免重复开发
4. **代码审查**: 每次修改或增加代码时进行上下文检查，排查潜在错误
5. **前端规范**:
   - 保持中文交流
   - 修改代码后审查确保不出现未引用却未必删除或注释的问题
   - 修复后检查整体代码确保不会出现新的ESLint错误
6. **API配置**: .env文件是API配置的唯一真实来源，providers_meta.json只负责映射关系和前缀定义
