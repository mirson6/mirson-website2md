# 通用文档自动爬虫 - 完整解决方案

## 🎯 核心功能

**一条命令，自动抓取任意文档路径下的所有页面！**

## 📝 使用方法

### 基本用法

```bash
python auto_crawl.py --url <任意文档页面的URL>
```

### 实际示例

#### 示例1：VBA文档

```bash
python auto_crawl.py --url https://dict.thinktrader.net/VBA/start_now.html
```

**效果**：
- ✅ 自动识别路径：`/VBA/`
- ✅ 自动发现6个页面
- ✅ 自动抓取并聚合
- ✅ 输出：`VBA_aggregated.md` (164 KB)

#### 示例2：帮助文档

```bash
python auto_crawl.py --url http://ptrade.local.com:7766/hub/help/api
```

**效果**：
- ✅ 自动识别路径：`/hub/help/`
- ✅ 自动发现该路径下所有 `.html` 页面
- ✅ 自动抓取并聚合
- ✅ 输出：`help_aggregated.md`

#### 示例3：自定义输出文件名

```bash
python auto_crawl.py --url https://example.com/docs/intro --output my_docs.md
```

## 🔍 工作原理

### 1. 路径自动识别

工具会根据给定的URL自动提取基础路径：

```
输入URL → 提取基础路径 → 爬取范围
─────────────────────────────────────
/VBA/start_now.html    →  /VBA/         →  /VBA/*.html
/hub/help/api         →  /hub/help/    →  /hub/help/*.html
/docs/intro.html      →  /docs/        →  /docs/*.html
/api/v2/users         →  /api/v2/      →  /api/v2/*.html
```

### 2. 页面自动发现

从HTML源码中提取所有匹配基础路径的页面链接：

```html
<!-- 页面HTML中的链接 -->
<a href="/VBA/basic_syntax.html">基础语法</a>
<a href="/VBA/control_statement.html">控制语句</a>
<a href="/VBA/system_function.html">系统函数</a>

↓ 自动提取 ↓

发现的页面：
- https://dict.thinktrader.net/VBA/basic_syntax.html
- https://dict.thinktrader.net/VBA/control_statement.html
- https://dict.thinktrader.net/VBA/system_function.html
```

### 3. 自动抓取和聚合

使用Firecrawl API逐个抓取页面，然后合并到单个Markdown文件。

## 📊 实际测试结果

### VBA文档测试

```bash
$ python auto_crawl.py --url https://dict.thinktrader.net/VBA/start_now.html

 Detected base path: /VBA/
 Found 6 pages via HTML extraction

 Discovered URLs:
   1. https://dict.thinktrader.net/VBA/basic_syntax.html
   2. https://dict.thinktrader.net/VBA/code_examples.html
   3. https://dict.thinktrader.net/VBA/control_statement.html
   4. https://dict.thinktrader.net/VBA/operating_mode.html
   5. https://dict.thinktrader.net/VBA/start_now.html
   6. https://dict.thinktrader.net/VBA/system_function.html

 Summary:
   Total URLs discovered: 6
   Successfully scraped: 6
   Failed: 0
   Output: VBA_aggregated.md (163.2 KB)
```

✅ **100%成功率，完整的6个VBA文档页面！**

## 🎨 输出文件结构

生成的Markdown文件包含：

```markdown
---
title: Documentation - Auto Aggregated
aggregated_at: 2026-01-11T10:23:15
total_pages: 6
base_path: /VBA/
discovery_method: automatic_html_link_extraction
source_urls:
  - https://dict.thinktrader.net/VBA/basic_syntax.html
  - https://dict.thinktrader.net/VBA/code_examples.html
  ...
---

# Documentation (/VBA/)

Discovered 6 pages under /VBA/ using automatic link extraction.

---

## 基础语法 | 迅投知识库
*Source: https://dict.thinktrader.net/VBA/basic_syntax.html*
内容...

---

## 控制语句 | 迅投知识库
*Source: https://dict.thinktrader.net/VBA/control_statement.html*
内容...

---

## 系统函数 | 迅投知识库
*Source: https://dict.thinktrader.net/VBA/system_function.html*
内容...

---
```

## ⚙️ 高级选项

### 查看帮助

```bash
python auto_crawl.py --help
```

### 自定义输出文件

```bash
python auto_crawl.py --url <URL> --output custom_name.md
```

### 启用详细日志

```bash
python auto_crawl.py --url <URL> --verbose
```

## 🚀 快速开始

1. **确保Firecrawl运行中**
   ```bash
   docker run -p 3002:3002 -e API_KEY=fc-test firecrawl/firecrawl:latest
   ```

2. **运行爬虫**
   ```bash
   python auto_crawl.py --url https://dict.thinktrader.net/VBA/start_now.html
   ```

3. **查看结果**
   ```bash
   # 生成的文件
   ls -lh VBA_aggregated.md
   
   # 查看内容
   head -50 VBA_aggregated.md
   ```

## 📋 与其他工具对比

| 功能 | auto_crawl.py | auto_crawl_vba.py | simple_vba_aggregator.py |
|------|---------------|-------------------|------------------------|
| 通用性 | ✅ 任意URL | ⚠️ 仅VBA | ⚠️ 仅VBA |
| 自动发现 | ✅ 完全自动 | ✅ 自动 | ❌ 手动配置 |
| 路径识别 | ✅ 自动提取 | ❌ 硬编码 | ❌ 硬编码 |
| 配置需求 | ❌ 零配置 | ❌ 零配置 | ✅ 需配置页面列表 |
| 适用场景 | **所有文档站** | VBA文档 | 已知页面列表 |

## 💡 使用技巧

### 1. 选择合适的起始页面

**推荐**：使用包含导航或索引的页面
- ✅ `https://site.com/docs/index.html` (索引页)
- ✅ `https://site.com/docs/toc.html` (目录页)
- ✅ `https://site.com/VBA/start_now.html` (完整导航)

**不推荐**：单个内容页面
- ❌ `https://site.com/docs/page1.html` (可能没引用其他页面)

### 2. 验证发现的页面

使用 `--verbose` 选项查看详细信息：
```bash
python auto_crawl.py --url <URL> --verbose
```

### 3. 自定义输出文件名

有意义的文件名：
```bash
python auto_crawl.py --url https://site.com/api/v2/users --output api_v2_docs.md
python auto_crawl.py --url https://site.com/guides/intro --output user_guides.md
```

## 🛠️ 故障排除

### 问题：只发现1个页面

**原因**：起始页面没有引用其他所有页面

**解决方案**：
1. 尝试使用索引页或目录页作为起始URL
2. 使用 `--verbose` 查看日志
3. 手动检查页面HTML源码中是否有其他页面链接

### 问题：某些页面没被发现

**原因**：
- 页面使用JavaScript动态加载
- 页面链接不在起始页面的HTML中

**解决方案**：
- 检查页面是否需要在浏览器中JavaScript渲染
- 尝试从不同页面开始（如sitemap、导航页）

### 问题：403 Forbidden

**原因**：网站阻止了请求

**解决方案**：

- 检查是否需要认证
- 检查是否需要特殊的headers
- 联系网站管理员

## 📦 相关文件

- `auto_crawl.py` - **主程序（推荐使用）**
- `auto_crawl_vba.py` - VBA专用版本（已废弃）
- `simple_vba_aggregator.py` - 手动配置版本（已废弃）
- `UNIVERSAL_CRAWLER_README.md` - 完整文档

## 📦 关于firecrawl部署

- 国内docker镜像下载报错的话， 建议走VPN方式

- 如果是IP地址， 可以走hosts映射方式； 如果用VPN，修改docker-composer.yaml文件

  ```
  services:
    playwright-service:
      ...
      environment:
        ...
        NO_PROXY: localhost,127.0.0.1,my-target.local,180.169.107.9
      extra_hosts: 
        - "my-target.local:180.169.107.9"  
      ...
  
    api:
      ...
      environment:
        ...
        NO_PROXY: localhost,127.0.0.1,my-target.local,180.169.107.9
        ENV: local
      extra_hosts: 
        - "my-target.local:180.169.107.9"      
      ...
  ```

  

## ✨ 总结

**`auto_crawl.py`** 是一个通用的、零配置的文档自动爬虫工具：

- ✅ 支持任意URL
- ✅ 自动识别文档路径
- ✅ 自动发现所有页面
- ✅ 自动抓取并聚合
- ✅ 一条命令完成所有操作

**立即开始使用**：
```bash
python auto_crawl.py --url https://dict.thinktrader.net/VBA/start_now.html
```
