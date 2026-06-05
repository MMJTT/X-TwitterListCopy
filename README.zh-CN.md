# x-listcopy

使用网页登录 Cookie，把一个 X/Twitter List 的成员复制到你自己的另一个 List。

[English README](README.md)

## 仓库 Description

使用网页登录 Cookie 复制 X/Twitter List 成员，支持 dry-run、安全确认、跳过重复成员和中英文文档。

## 为什么做这个项目

原来的 `Noleli/listcopy` 是一个很早期的 PHP 小工具，依赖 Twitter OAuth 1.0a 和老 REST API。到了 2026 年，这些旧接口和旧 app key 已经无法稳定工作。`x-listcopy` 保留了同一个实用目标，但改用当前 X 网页端实际在使用的 GraphQL 请求流程。

这个工具来自一次真实成功复制：

- 源 List 读取到 `188` 个成员
- 目标 List 复制后有 `185` 个成员
- 剩余 `3` 个被 X 返回 `code 104` 拒绝添加

## 重要说明

本项目与 X Corp. 无关。它使用的是 X 网页端 GraphQL 接口，不是稳定公开 API。X 随时可能修改这些接口。

请只在你拥有或有权操作的账号和 List 上使用。你需要自行遵守 X 服务条款、限流规则和所在地法律法规。

`auth_token` 和 `ct0` 是敏感登录凭据，等同于密码：

- 不要提交到 git
- 不要贴到公开 issue
- 使用后如果想让 Cookie 失效，可以刷新登录态或退出登录

## 功能

- 从公开或当前账号可访问的源 List 读取成员
- 复制到已有目标 List
- 创建新目标 List
- 支持 `--dry-run`，写入前先预览
- 写入操作必须显式加 `--yes`
- 自动跳过目标 List 中已存在的成员
- 兼容 X 当前的一个特殊行为：成员已添加成功，但 GraphQL 响应因为 List banner 字段解码失败而报错
- 零第三方 Python 依赖

## 环境要求

- Python 3.10+
- 浏览器里已经登录 X 账号
- 目标 List 必须属于你的账号，或你有权限创建新 List

## 安装

克隆仓库：

```bash
git clone https://github.com/your-name/x-listcopy.git
cd x-listcopy
```

创建并激活虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装 CLI：

```bash
pip install -e .
```

运行测试：

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## 获取 Cookie

1. 在浏览器打开 `https://x.com`，并确认已经登录。
2. 打开开发者工具。
3. 进入 Application/Storage 面板。
4. 找到 `https://x.com` 的 Cookies。
5. 复制下面两个 Cookie 的值：
   - `auth_token`
   - `ct0`

在本地 shell 中导出：

```bash
export X_AUTH_TOKEN="你的 auth_token cookie"
export X_CT0="你的 ct0 cookie"
```

可选：

```bash
export X_BEARER_TOKEN="当前网页 bearer token"
```

通常不需要设置 `X_BEARER_TOKEN`；工具会自动从 X 前端 bundle 中发现当前公开 web bearer token。

## 使用方法

一定先 dry-run：

```bash
x-listcopy \
  --source "https://x.com/i/lists/2026486577304842549?s=20" \
  --dry-run
```

复制到已有 List：

```bash
x-listcopy \
  --source "https://x.com/i/lists/2026486577304842549?s=20" \
  --dest-list-id "2062729798158565650" \
  --yes
```

创建一个新的私密 List 并复制进去：

```bash
x-listcopy \
  --source "owner/list-slug" \
  --create-list-name "Copied List" \
  --description "Copied with x-listcopy" \
  --private \
  --yes
```

只复制前 10 个成员用于测试：

```bash
x-listcopy \
  --source "https://x.com/i/lists/2026486577304842549" \
  --dest-list-id "2062729798158565650" \
  --limit 10 \
  --yes
```

也可以用模块方式运行：

```bash
python -m x_listcopy --source "owner/list-slug" --dry-run
```

## 支持的 List 写法

```text
1234567890
https://x.com/i/lists/1234567890
https://twitter.com/owner/lists/list-slug
owner/list-slug
```

数字 List ID 最稳定。

## 退出码

- `0`：命令完成，没有成员添加失败
- `1`：命令完成，但至少有一个成员添加失败
- 其他非零值：配置、认证、网络或 GraphQL 失败

## 常见错误

### `Set X_AUTH_TOKEN and X_CT0`

缺少 Cookie 环境变量。

### `Could not find X GraphQL operations`

X 修改了网页前端 bundle。请提交 issue，并说明失败的 operation 名称。

### `Authorization: You aren't allowed to add members to this list`

X 拒绝添加某个成员或拒绝对目标 List 的操作。实际观察中，部分用户可能因为隐私、拉黑、封禁或 X 侧策略检查无法加入 List。

### `DecodeException` 和 `default_banner_media_results`

2026 年 6 月观察到的行为：`ListAddMember` 已经成功添加成员，但响应体里的 List banner 字段解码失败。工具只在 `ListAddMember` 场景下把这个特定响应视作添加成功。

## 安全模型

工具只会从你的本机直接请求 X，不保存 Cookie，不上传 Cookie，也不会把 Cookie 写入磁盘。

推荐流程：

1. 在本地 shell 中导出 Cookie。
2. 先运行 `--dry-run`。
3. 确认后加 `--yes` 正式复制。
4. 关闭当前 shell。
5. 如果想让 Cookie 失效，刷新 X 登录态或退出登录。

## 开发

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src python -m unittest discover -s tests
```

项目结构：

```text
src/x_listcopy/
  client.py      X web GraphQL client
  cli.py         command-line interface
  models.py      dataclasses
  parsing.py     List URL and timeline parsing
tests/
  test_x_listcopy.py
```

## Roadmap

- JSON 输出
- 超大 List 的断点续传文件
- 更清晰的进度摘要

## License

Apache-2.0
