# PetSafe-Greenery · 从零到提交：完整操作手册

> 面向"完全没有代码基础"的你。照着这份文档做，每一步都写了**在哪个网站、点哪里、敲什么、看到什么算成功**。
> 配套代码已经全部写好并跑通，你不需要自己写代码，只需要**按顺序执行命令**并**把结果填进报告**。

---

## 0. 先看清现状：你现在在哪、有多少时间

> ### ✅ 第一件事（30 秒）：确认你拿到的是最新版本
>
> 浏览器经常把同名文件缓存住，所以你**可能**还在用旧版代码（之前就发生过，旧版会报各种看不懂的错）。
> 解压后，在项目文件夹里运行：
>
> ```bash
> python scripts\check_env.py
> ```
>
> 看到这一行就对了：
>
> ```
> [ INFO ] code version: 2026-11-12d
> ```
>
> **不是 `2026-11-12d`？说明你手里是旧包** → 重新下载 `petsafe-greenery-v2026-11-12d.zip`，
> 解压到**一个新的空文件夹**（不要覆盖旧文件夹，旧文件夹里的 `results/` 会污染新结果）。
>
> 本版新增：**DeepSeek 支持**（没有每日限额，不会中途断）、**缓存按 backend 隔离**（修了一个会让
> 离线模拟跑出错误数字的 bug）、**版本自检**（代码被改坏时立刻退出，不会浪费额度）。


| 日期 | 里程碑（来自课程 spec） | 你要交付什么 | 剩余天数 |
|------|------------------------|--------------|----------|
| 2026-10-09 | Proposal 截止 | ✅ 已完成（就是你发我的那份） | — |
| **2026-11-12（今天）** | — | — | — |
| **2026-11-15（周日）** | **Presentation slides 截止** | PPT（5–7 分钟讲完 + Q&A） | **3 天** |
| 2026-11-20 或 11-27 | 课堂汇报（现场，5–7 分钟 + 1–2 分钟提问） | 现场演示 | 8 / 15 天 |
| **2026-11-29（周日）** | **Final report + code 截止** | 英文报告（正文 ≤10 页）+ 代码 zip | **17 天** |

**你 proposal 里写的排期（10/10 开始建库）已经落后了一个月。** 所以真正的顺序是：

```
第 1 步（今天，今晚）：把代码跑起来 + 拿到 API key + 跑通 3 个场景
第 2 步（11/12）：跑完 25 场景 × 3 方法 = 75 次设计生成
第 3 步（11/13）：出图 + 写 PPT 初稿
第 4 步（11/14）：做演示 App（Streamlit）+ 录制备用录屏
第 5 步（11/15）：定稿 PPT → 提交 Canvas
第 6 步（11/16–11/25）：写报告（不要拖到最后一晚，Turnitin 很慢）
第 7 步（11/26–11/28）：报告定稿 + 打包代码 + 再跑一遍确认可复现
第 8 步（11/29 23:00 前）：提交报告 + 代码 zip
```

⚠️ **两个硬提醒**
1. 课程明确写了 *"Turn-it-in score runs very slow near due date. Try to submit 48 hours earlier"* → **11/27 就提交**，别卡 11/29。
2. 晚交每天扣 15%，没有商量。

---

## 1. 先确认：哪些东西我已经替你做完了

项目代码在 `/workspace/petsafe-greenery/`，**全部已写好并验证跑通**。你不用写代码，你要做的是"运行它 + 解读它 + 写成报告"。

| 已完成 | 文件 | 状态 |
|--------|------|------|
| 植物安全数据库（150 种，带猫/狗毒性标签 + 光照 + 水分） | `data/plants.csv` | ✅ 从 ASPCA + NC State 自动采集，150 条全部校验通过 |
| 数据采集脚本（可复现，证明数据不是编的） | `scripts/fetch_aspca.py`、`scripts/fetch_ncstate.py`、`scripts/build_database.py` | ✅ |
| Agent 主程序（Gemini function calling + 确定性筛选 + 审计回路） | `src/agent.py`、`src/tools.py` | ✅ |
| 两个 baseline | `src/baselines.py`（zero-shot / naive RAG） | ✅ |
| 25 个评测场景 | `data/scenarios.csv` | ✅ |
| 自动评估脚本（5 个指标：安全/可存活/双约束/完整性/幻觉率） | `src/evaluate.py` | ✅ |
| **一键环境自检**（告诉你哪里错 + 给出修复命令） | `scripts/check_env.py` | ✅ |
| **三层物种解析器**（库里没有的也能按 ASPCA 判，且带出处） | `src/aspca_resolver.py` | ✅ |
| **ASPCA 全量抓取**（1023 种，同一权威源） | `scripts/fetch_aspca_full.py`、`data/aspca_snapshot.json` | ✅ |
| **ASPCA-aligned 补充库 + 别名表**（980 种 / 3872 个别名） | `scripts/fetch_plantfolio.py`、`data/plantfolio_catalog.json`、`data/plant_aliases.json` | ✅ |
| **两源一致性检查**（覆盖率 + 一致率，写进报告） | `scripts/check_sources.py` | ✅ |
| **设计完整性评分规则**（15 条二值条目，可自动判定） | `src/rubric.py` | ✅ |
| 搭配/护理/注意事项的输出结构 + 完整性补全回路 | `src/schema.py`、`src/prompts.py`、`src/agent.py` | ✅ |
| 报告用的工作流图 + 评分规则表 | `scripts/make_workflow_figure.py`、`scripts/print_rubric.py` | ✅ |
| 出图脚本（7 张图，PNG+PDF） | `scripts/make_figures.py` | ✅ |
| 演示 Web App | `app.py` | ✅ |
| 英文 README（提交用） | `README.md` | ✅ |
| 报告 LaTeX 骨架 | `report/report_skeleton.tex` | ✅ |
| PPT 逐页讲稿 | `docs/SLIDES_OUTLINE.md` | ✅ |

**你唯一必须自己完成的、需要联网/花钱/花时间的部分：**
① 申请 API key（DeepSeek 付费但无日限额 / Gemini 免费但有日限额，见第 2 节）
② 真正跑一遍实验拿到真实数字 ③ 写报告和 PPT。

---

## 2. Phase 1 · 申请 API key（今天，5 分钟）

> **两条路，选一条即可。代码两种都能跑，其他部分一模一样。**
>
> | | 🅰️ **DeepSeek（推荐）** | 🅱️ Gemini（免费） |
> |---|---|---|
> | 日限额 | **无**（只有并发上限） | 有，约 20～500 次/天，看模型 |
> | 要花钱吗 | 要，但很便宜（整个实验 < ¥1） | 不要 |
> | 会不会中途断 | **不会**（不会突然没额度） | 会（额度用完要等第二天） |
> | 适合我吗 | 不想再被额度卡住 → 选这个 | 不想充值 → 选这个 |
>
> ⚠️ **DeepSeek 没有免费额度**，必须先充值才能调 API（新号有时送赠送额度）。
> 不想充值就直接选 🅱️ Gemini。

---

### 🅰️ 方案 A：DeepSeek（推荐 · 没有日限额 · 不会中途断）

**网址**：<https://platform.deepseek.com>

1. 注册 / 登录（手机号或邮箱都行）。
2. 点 **充值（Top up）**，充 **￥20 起步**就够跑完整个实验。
   （离峰价 `deepseek-flash`：输入 \$0.15 / 百万 tokens，输出 \$0.60 / 百万 tokens；
   峰值时段翻倍。整个实验约 0.5M tokens，**花费 < ¥1**。）
3. 打开 <https://platform.deepseek.com/api_keys> → **Create new API key** → 命名（例如 `petsafe`）→ **复制密钥**（`sk-` 开头，只显示一次）。
4. 写进 `.env`（见下面的"把密钥放进 .env"）。

```dotenv
DEEPSEEK_API_KEY=sk-把你的密钥粘在这里
PETSAFE_BACKEND=deepseek
PETSAFE_MODEL=deepseek-flash
```

**跑的时候**（和 Gemini 完全一样的命令）：

```bash
python scripts\run_experiments.py --start 0 --end 3
```

**三个必须知道的点**（我已经写在代码里了，你只要知道原因）：

- **模型名用 `deepseek-flash`**。DeepSeek 已经把旧的 `deepseek-chat` / `deepseek-reasoner` 下线了（2026-07-24），写旧名字会直接报错。`deepseek-flash` 支持工具调用（function calling）、JSON 输出和流式，是官方文档推荐的默认模型。
- **thinking（深度思考）已被我关掉**。DeepSeek 默认开启 thinking，而 *thinking 模式下用工具必须把 `reasoning_content` 原样回传，否则 API 报 400*。关掉之后最稳，代码里每次请求都带 `"thinking": {"type": "disabled"}`。
- **余额不足会返回 HTTP 402**，报错会直接告诉你"去 platform.deepseek.com 充值"。**429 只是并发超限**，等几秒重试就行 —— 和 Gemini 的"日配额用完"是完全不同的两回事。

**报告里要写清楚用的是哪个模型**：代码已经把真实使用的模型名写进 `results/usage.json` 和每个结果文件（`model` 字段），抄进报告的实验设置那一节即可。

---

### 🅱️ 方案 B：Gemini（完全免费，但有日限额）

**网址**：<https://aistudio.google.com/apikey>

1. 用你的 Google 账号登录（Gmail 就行）。
2. 第一次进去会让你接受条款，点接受。
3. 点 **Create API key**（创建 API 密钥）。
4. 选一个项目：默认自动建好，直接用；如果你以前绑过 Google Cloud 付费账单，**一定要新建一个 project**，避免免费额度被扣钱。
5. 复制密钥（形如 `AQ...` 或 `AIza...`，2026 年新密钥以 `AQ.` 开头是正常的）。
6. 密钥只在你自己的电脑/Colab 里用，**绝对不要贴进 PPT、报告正文、GitHub 仓库**。

**免费额度（2026-11 实际情况，自己去核对）**

| 模型 | 免费层 | 日请求量 | 建议 |
|------|--------|----------|------|
| `gemini-3.5-flash-lite` | ✅ 免费 | 约 500 次/天 | **默认用这个** |
| `gemini-3.8-flash` | ✅ 免费 | 约 20 次/天 | 额度太小，只在关键场景用 |
| `gemini-3.6-flash` | ✅ 免费 | 约 20 次/天 | 同上 |
| `gemini-4-argon` / `3.1-pro` | ❌ 需付费 | — | 别用 |

👉 查你自己账号的真实额度：<https://aistudio.google.com/rate-limit>

**为什么选 Flash-Lite**：本项目 25 场景 × 3 方法 × 约 2 次调用 ≈ **150 次调用**。用 3.8 Flash（20 次/天）要跑 8 天，来不及；用 Flash-Lite（500 次/天）**一天就能跑完**。
另外代码里做了**磁盘缓存**：同样的请求再跑一次不花额度，中途断了可以从断点继续。

**写进 `.env`**：

```dotenv
GEMINI_API_KEY=把你的密钥粘在这里
PETSAFE_BACKEND=gemini
PETSAFE_MODEL=gemini-3.5-flash-lite
```

**命令行里设置密钥**（临时方式，关闭终端就没了）

```bash
# macOS / Linux
export GEMINI_API_KEY="把你的密钥粘在这里"

# Windows PowerShell
$env:GEMINI_API_KEY="把你的密钥粘在这里"
```

> 🔁 **两种 key 不要同时写在同一个 `.env` 里**。`PETSAFE_BACKEND` 决定代码读哪一行；
> 写错 backend，代码就会拿错 key 去请求，报 401 而不是告诉你读错了变量。
> `python scripts\check_env.py` 会明确告诉你"当前 backend 是 deepseek，我在找 DEEPSEEK_API_KEY"。

---

## 3. Phase 2 · 选一个"跑代码的地方"（今天，二选一）

零基础建议：**先用 Google Colab（浏览器里，不用装任何东西）跑通，再用本地环境做最终提交**。

### 方案 A：Google Colab（推荐先走这个）

1. 打开 <https://colab.research.google.com>，用同一个 Google 账号登录。
2. 把 `petsafe-greenery` 整个文件夹打包成 zip 上传？**更简单的做法**：直接新建 notebook，用下面这段代码把代码"贴"进去（文件不大）。

   ```python
   # ===== Cell 1：准备环境 =====
   !pip install -q google-genai pandas matplotlib

   import os, json, sys
   from google.colab import userdata
   os.environ["GEMINI_API_KEY"] = userdata.get("GEMINI_API_KEY")  # 左侧 🔑 Secrets 里新建一个 GEMINI_API_KEY
   ```
   > 左侧边栏的 **🔑 Secrets** 点 "Add new secret"，名字写 `GEMINI_API_KEY`，值粘贴你的密钥。点开 notebook 右上角的钥匙图标授权读取。

3. 但**更推荐下面的方案 B**，因为最终要交代码、要做 Streamlit 演示，本地环境更省事。

### 方案 B：本地环境（最终提交用这个）

需要装 Python 3.11+。检查版本：

```bash
python3 --version        # 显示 3.11 以上即可
```

建虚拟环境 + 装依赖（**在项目文件夹里**执行）：

```bash
cd petsafe-greenery
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> 装依赖卡住/超时？换国内镜像：
> `pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`

---

### 方案 B-2：用 VS Code 打开（最终提交就靠它，强烈推荐）

**为什么用 VS Code**：终端、代码编辑器、文件树在一个窗口里；跑演示不用切窗口；最后打包交代码只要"右键→压缩"；装个 LaTeX Workshop 插件还能直接预览报告 PDF。

#### 第 1 步 · 装两个软件

| 软件 | 下载地址 | 注意 |
|------|----------|------|
| VS Code | <https://code.visualstudio.com/download> | Windows 选 **User Installer**（免管理员） |
| Python 3.11+ | <https://www.python.org/downloads/> | ⚠️ 安装界面底部**必须勾上 "Add python.exe to PATH"**，否则命令行找不到 python |

装完 VS Code，按 <kbd>Ctrl</kbd>+<kbd>`</kbd> 打开底部终端，敲 `python --version`，看到 `Python 3.11.x` 就说明装好了。

#### 第 2 步 · 装 3 个 VS Code 插件

点左边最上面那排的**方块图标**（Extensions），搜名字 → Install：

- **Python**（Microsoft 官方）
- **Pylance**（自动补全，红波浪线报错）
- **LaTeX Workshop**（编译和预览报告）

#### 第 3 步 · 打开项目文件夹（⚠️ 必须先做这步，否则后面选不了文件）

`File` → `Open Folder…` → 选中解压出来的 **`petsafe-greenery` 整个文件夹**（不是里面的某个文件）。

> 看到 VS Code 弹出"是否信任此文件夹"→ 点 **Yes, I trust the authors**。

打开后左边就是你的项目结构：`src/`、`scripts/`、`data/`、`docs/`、`report/`、`figures/`。
**下面第 4 步要在这里的文件夹里做**——没打开文件夹，VS Code 的"选择 requirements.txt"和"选 Python 3.11"两个列表都会是空的或找不到选项。

#### 第 4 步 · 建虚拟环境

> 💡 **VS Code 的图形界面挑不明白就直接用终端 3 行**（功能完全等价，30 秒）：
> 按 <kbd>Ctrl</kbd>+<kbd>`</kbd> 打开终端，粘贴下面三行（Windows PowerShell）：
>
> ```powershell
> cd petsafe-greenery
> python -m venv .venv
> .venv\Scripts\Activate.ps1
> pip install -r requirements.txt
> ```
>
> 左下角出现 `('.venv': venv)` 就一样能用。界面那条路是"给这 3 行套了个壳"，不是必须的。


按 <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> → 输入 `create env` →

> ⚠️ **新版 VS Code 的命令名是 `Python: Create Environment...`**（你截图里第 2 行那个）。
> 旧版本才叫 `Python: Create Virtual Environment`。搜 `create env` 两个都能搜到，认准带 **Environment** 的那条。

点完之后依次：

1. **选解释器（Python 版本）**：想用 3.11 就选 `Python 3.11.x`；列表里没有 3.11 时选最上面的 `Python 3.x.x`（任何 3.11 以上的都行），或者选 **`Enter interpreter path...` → Find...** 手动指到 `python.exe`。
2. **选依赖文件**：选 **`requirements.txt`**（VS Code 会自动把依赖装好）。

左下角状态栏会变成 `Python 3.11.x ('.venv': venv)`，说明成功。

> **列表里没有 3.11？** 说明 VS Code 没找到 3.11。先在终端敲 `py -0`（Windows 自带的 Python 启动器）看看装了哪几个版本；
> 如果提示"无法识别的命令"，说明**根本没装 Python**，回第 1 步装（安装时必须勾 Add to PATH），装完**重启 VS Code**（不重启它看不到新装的 Python）。
> 实在挑不明白版本，选列表里任何一个 3.11 以上的就行 —— 这个项目不挑版本。

<details>
<summary>想手动敲命令（PowerShell 终端，Windows）</summary>

```powershell
cd petsafe-greenery
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果第三行报错说"无法加载文件……因为在此系统上禁止运行脚本"，先执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

然后重新激活。

**Mac / Linux** 用的是 `source .venv/bin/activate`（斜杠，小写）。
</details>

#### 第 4.5 步 · ⚠️ 如果 VS Code 开始建 `.venv-1`，直接点 Cancel

VS Code 的界面有时会在你已经手动建好 `.venv` 之后，又弹一次"Creating virtual environment named **.venv-1**"。

**看到 `.venv-1` 就点 Cancel（取消）。** 判断依据看终端提示符：

```
(.venv) PS E:\...\petsafe-greenery>     ← 前面有 (.venv) 就说明虚拟环境已经激活并可用
```

已经激活了，VS Code 再建一个只是重复，还会让你困惑"到底用哪个"。多出来的 `.venv-1` 文件夹之后直接删掉即可。

另外注意 VS Code 可能选到 **Python 3.14**（很新，部分依赖还没有现成 wheel，pip 会尝试用 C 编译器源码编译然后报错）。
**本项目最稳的版本是 3.12 / 3.13。** 如果 3.14 上装依赖失败，换一个：

```powershell
py -3.12 -m venv .venv312
.venv312\Scripts\Activate.ps1
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

（`py -3.12` 会用 Windows 的 Python 启动器指定 3.12；如果提示"找不到版本"，就说明你只装了 3.14，去 python.org 再装一个 3.12，安装时勾 Add to PATH，装完重启 VS Code。）

#### 第 5 步 · 把 API key 放进去（不用敲 export）

在左侧文件树里**右键 → New File**，文件名写 `.env`（开头有个点，别漏），内容写两行：

```
GEMINI_API_KEY=粘贴你的key
PETSAFE_MODEL=gemini-3.5-flash-lite
```

保存即可 —— `src/config.py` 会自动读取这个文件（我加好了，不用你敲任何命令）。

> 🔒 `.env` 已经写进 `.gitignore`，**不会**被打包进提交的 zip，key 不会泄露。

#### 第 6 步 · 先自检（不用 key，30 秒）

在底部终端里（确认左下角显示 `.venv`）：

```powershell
python scripts\check_env.py
```

**这条命令会一次性告诉你哪里不对，并给出对应的修复命令**（不会打印你的 key，只说"有没有找到"）。
输出长这样：

```
[  OK  ] Python 3.11.2 at C:\...\.venv\Scripts\python.exe
[  OK  ] virtual environment active: ...\.venv
[  OK  ] package 'google.genai' is installed
[ FAIL ] no API key found (neither the environment nor a .env file)
[  OK  ] data/plants.csv present (150 species)
--------------------------------------------------------------------
WHAT TO DO NEXT:
  1. Create a file named .env in the project root ...
```

再跑这两个（都不会花钱、不联网）：

```powershell
python scripts\check_database.py
python scripts\smoke_test.py
```

两个脚本都打印 `All checks passed.` 就说明环境完全正常。`smoke_test.py` 会真的走一遍 agent 流程（含安全修复和完整性补全），最后打出 `completeness: 15/15 (core 5/5)`。

#### 第 7 步 · 先跑 3 个场景（要 key，5 分钟）

```powershell
python scripts\run_experiments.py --start 0 --end 3
```

看到结果表就说明 key 和网络都通了。

#### 第 7.5 步 · 三种方法并排看一眼（答辩演示用，强烈建议做一次）

```powershell
python scripts\compare_one.py --scenario s02
```

它会打印**一个场景、三种方法**的完整对比：

1. 场景描述（场地/光照/水分/宠物）
2. 每种方法生成的方案（分区、搭配逻辑、护理、注意事项逐条展开）
3. 指标表（安全 / 可存活 / 双约束 / 完整性 / 幻觉率）
4. **毒性取证**：谁推荐了有毒植物，**以及为什么**——
   - B1：`-> no retrieval at all: this came from the model's own memory`（凭记忆瞎猜的）
   - B2：`-> it WAS in the retrieved top-8; the model chose it anyway`（检索到了，模型自己选的）
   - Agent：`-> the deterministic filter had already removed it before the model could see it`（根本没给模型机会）
5. 每种方法**漏掉了哪几条完整性规则**

> 这段取证输出就是答辩时最有力的证据：它证明安全性差异来自**架构**而不是 prompt。
> 建议在这个场景上跑一次，截图存着。

常用参数：

```powershell
python scripts\compare_one.py --index 4          # 按序号选场景（0 起）
python scripts\compare_one.py --methods agent    # 只看某一个方法
python scripts\compare_one.py --force            # 忽略缓存重跑
```

#### 第 8 步 · 跑完整实验（11/12，1–2 小时）

```powershell
python scripts\run_experiments.py
python scripts\make_figures.py
```

中断了可以**重跑同一条命令**，命中的结果会走缓存，不会重复烧额度。

#### 第 9 步 · 本地跑演示 App（11/13–11/14）

```powershell
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`。**终端窗口别关**，关了 App 就停了。
部署到公网见第 6 节。

#### 第 9.5 步 · 把实验结果填进报告（重要）

报告里所有数字都是 `\todo{}` 占位符，**必须用脚本填，不要手打**（手打一定会和
`results/` 里的原始数据对不上）。

```powershell
python scripts\fill_report.py        # 自动填表 + 写分析草稿 + 检查图和数是否同源
python scripts\build_report.py       # 编译
```

`fill_report.py` 会做四件事：

1. 把 `results/runs/<模型>/summary.csv` 里的数字填进**主结果表**（安全 / 保守安全 /
   存活率 / 双约束 / 完整度 / 目录外率）；
2. 把 `rubric_breakdown.csv` 填进**完整度表**（A1–A3 区、C2–C3 护理、core 分、
   平均缺项）；
3. 把脚注和 **Analysis 段落草稿**填上（草稿里带真实数字，但**措辞要你自己重写**，
   那是你的分析）；
4. **核对图和数是不是同一次运行**：如果 `figures/` 里的图还是模拟的或是别的模型画的，
   它会红色警告，让你先跑 `make_figures.py`。

它永远从 `report/report_skeleton.template.tex`（干净的模板）出发，
所以**换模型重填只要再跑一次**，不会把两套数字叠在一起。

想看还差什么：`python scripts\fill_report.py --check`

> ⚠️ 填完一定要检查：分析段落是**草稿**，请改成你自己的话再提交。

#### 第 10 步 · 编译报告

**最省事的一条（推荐，不需要任何 VS Code 扩展）：**

```powershell
python scripts\build_report.py
```

它会自动找 `pdflatex`、**连续编译两遍**（第二遍解决交叉引用和参考文献），
然后打印页数和错误数，并自动打开 PDF。
正常应该输出：**`完成：12 页，0 个 LaTeX 错误。` + `页数符合要求（封面 1 + 正文 10 + 参考文献 1）`**

> 如果报"没有找到 LaTeX 编译器"，往下看第 2、3 条。

**第 2 条：VS Code 的 LaTeX Workshop（弹出选项框卡住时用这个）**

那个"选 latexmk"的选项框只是让你挑编译方式，**不选也能编译**。两个更稳的入口：

- <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> → 输入 `LaTeX Workshop: Build` →
  选 **Build LaTeX project**（它会自动用默认 recipe = latexmk）；
- 或者输入 `Build with recipe` → 选 `latexmk` / `pdflatex`。

**按 <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>B</kbd> 完全没反应**，通常是两种原因：
① LaTeX Workshop 扩展没装（扩展面板搜 "LaTeX Workshop" 安装）；
② 快捷键被别的扩展抢了（用上面的命令面板代替即可）。
**两种情况都不影响结果**——`build_report.py` 一条命令就绕过去了。

**第 3 条：Overleaf（完全不用装 LaTeX，5 分钟，最不容易出错）**

1. <https://overleaf.com> 注册（免费）
2. New Project → **Upload Project** → 把**整个 `petsafe-greenery` 文件夹**压成 zip 传上去
   （必须含 `report/` 和 `figures/` 两个目录——报告里的图在 `figures/`）
3. Main document 选 `report/report_skeleton.tex`
4. 点 **Recompile** → 右上角预览，右上角下载 PDF

**第 4 条：本机有 MiKTeX 时直接敲命令**

```powershell
cd report
pdflatex -interaction=nonstopmode report_skeleton.tex
pdflatex -interaction=nonstopmode report_skeleton.tex
```

（跑两遍。第一次 MiKTeX 可能问"是否安装缺失的宏包"→ 选 **Yes**，需要联网。）

**怎么判断编译成功**：

| 输出 | 含义 |
|---|---|
| `12 页，0 个 LaTeX 错误` | ✅ 完全符合课程格式 |
| 超过 12 页 | 正文超了 10 页上限，需要压缩 |
| 有 `!` 开头的错误 | 看 `report/report_skeleton.log` 最后几行 |
| `File ... not found` | 图片或 `rubric_table.tex` 没上传（Overleaf 上要传 `figures/`）|

#### 第 11 步 · 打包提交代码

在**文件资源管理器**里右键 `petsafe-greenery` 文件夹 → `压缩为 ZIP 文件` → 改名 `petsafe-greenery.zip` → 上传 Canvas。

> 提交前检查三样：**删掉 `.venv` 文件夹**、删掉 `results/cache` 文件夹、确认没有 `.env`（`.env` 本来就不在包里）。
> `results/offline_demo` 是模拟数据，**也要删掉**，它绝不能出现在报告里。

#### VS Code 常见问题

| 现象 | 原因 / 解法 |
|------|------------|
| 终端里 `python` 不是内部或外部命令 | Python 安装时没勾 Add to PATH → 重装并勾上，或用 `py -3.11` |
| `无法加载文件 Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| `pip install` 卡住 / 超时 | 换镜像：`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/` |
| 提示 `No module named google.genai` | 没激活虚拟环境 → 左下角点 Python 版本 → 选 `.venv` 那个 |
| 429 / RESOURCE_EXHAUSTED | 免费额度用完了。额度按 project 算，按太平洋时间午夜重置 → <https://aistudio.google.com/rate-limit> |
| 想单独跑一个 .py | 打开该文件 → 右上角 ▷ "Run Python File"（在同一个终端里跑） |
| 命令面板搜不到 `Python: Create Virtual Environment` | 新版改名了 → 搜 `create env`，选 **`Python: Create Environment...`** |
| 下拉列表里没有 3.11 / 选不了 `requirements.txt` | ① 没打开项目文件夹 → `File → Open Folder…` 选 `petsafe-greenery` 整个文件夹；② 没装 Python → 终端敲 `py -0` 确认，装完**重启 VS Code** |
| 装完 Python 还是找不到 | 重启 VS Code；或用 `Python: Select Interpreter` → `Enter interpreter path` → `Find...` 手动选 `python.exe` |
| VS Code 开始建 `.venv-1` | 点 **Cancel**。终端提示符前面有 `(.venv)` 就说明环境已可用，多余的 `.venv-1` 文件夹删掉即可 |
| pip 报 "Microsoft Visual C++ 14.0 or greater is required" | VS Code 选了太新的 Python 3.14 → 用 `py -3.12 -m venv .venv312` 换 3.12 再装 |
| 装依赖特别慢 / 一直编译 | 加镜像 `-i https://mirrors.aliyun.com/pypi/simple/`，并改用 Python 3.12 |

---

## 4. Phase 3 · 先跑通 3 个场景（今天，30 分钟）

**先别急着跑全部 25 个**，先用 3 个场景确认整条链路通。

```bash
cd petsafe-greenery
source .venv/bin/activate
export GEMINI_API_KEY="你的密钥"

# 先检查数据库
python scripts/check_database.py

# 只跑 agent 方法的前 3 个场景
python scripts/run_experiments.py --methods agent --end 3
```

**成功的标志**：
- 屏幕上每个场景打印一行 `[   ran] s01  plants=6  safe=1.00  viable=1.00  dual=1.00`
- `results/agent/s01.json` 等文件生成了
- `safe=1.00` 表示推荐了 0 个有毒植物 → **agent 的核心承诺生效了**

**如果报 429**：额度用完了 → 等太平洋时间午夜重置，或换 `--model gemini-3.5-flash-lite`。

---

## 5. Phase 4 · 跑完整实验（11/12，1–2 小时）

### 5.0 太慢？先看这三行（重要）

跑起来慢**是正常的**，但可以大幅加速。实测算过：agent 每个场景要打 **4–6 次 API**（两次基线各 1–2 次），
一次调用要生成一整份 JSON 设计（4 个分区 + 搭配 + 护理 + 注意事项）。

新版已经做了三件事：

| 优化 | 效果 |
|---|---|
| **默认关闭 thinking**（`PETSAFE_THINKING=off`） | Gemini 3.x flash 默认会先"思考"，这一项就占掉大部分等待时间。本项目所有可检查项都由 Python 判定，**不需要模型自己推理** → 单次调用通常从 30–60s 降到 5–15s |
| **实时打印每次调用的耗时与 token** | 直接看见时间花在哪：<br>`[call] agent_tool 6.2s in 812 / out 1450 tok` |
| **429/503 快速失败 + 指数退避 + 备用模型** | 免费额度是共享的，**高峰期模型会返回 503 "high demand"**。新版会退避重试（4s→10s→22s→47s），连续 3 次 503 就**自动切到备用模型**；跑之前还会先"探活"一次，挑一个当前能用的模型，**三个方法用同一个模型**（保证公平） |

```bash
# 想更快：关 thinking + 限制输出长度（4000 tokens 足够写完一份设计）
# 在 .env 里加：
#   PETSAFE_THINKING=off
#   PETSAFE_MAX_TOKENS=4000

python scripts\run_experiments.py --start 0 --end 3
```

> ⚠️ **Gemini 3.5+ 只能用 `thinking_level`，不能用 `thinking_budget`**
> SDK 原文：*"Starting from Gemini 3.5 models, the old thinking_budget will no
> longer be supported and will result in a user error if set."*
> 发错参数会得到 `400 INVALID_ARGUMENT`，整轮实验直接中断。新版已经改用
> `thinking_level`（off→MINIMAL / low→LOW / on→HIGH），并且**任何 400 都会自动用
> 最小配置重试一次**，一个不支持的参数不会再毁掉整轮实验。

跑之前先探测模型是否可用：

```
checking which model is available ... (gemini-3.5-flash-lite)
  -> model in use: gemini-3.5-flash-lite
```

如果看到 `-> gemini-3.5-flash-lite is overloaded; using gemini-3.6-flash for the WHOLE run`，
说明它替你换了模型，**三个方法依然用的是同一个模型**，可以放心。

**遇到 503 怎么办**：这是 Google 侧容量问题，**不是你的 bug**。等几分钟重跑即可——
每次成功的调用都已经写进缓存，重跑**不会重复计费**，会从断掉的地方继续。

### ⚠️ 免费额度是按「模型」算的，这是最容易踩的坑

| 模型 | 免费额度（每天 generate_content 次数） | 够跑完 25 场景 × 3 方法吗 |
|---|---|---|
| `gemini-3.5-flash-lite` | 约 **500** 次 | ✅ 够（约需 200 次） |
| `gemini-3.6-flash` | 约 **20** 次 | ❌ 不够，跑十几个就 429 |
| `gemini-3.8-flash` | 约 **20** 次 | ❌ 不够 |

**所以：`.env` 里只写 `PETSAFE_MODEL=gemini-3.5-flash-lite`，不要配别的。**

新版已经**默认不切换备用模型**了（以前会自动切到 `gemini-3.6-flash`，那等于 20 次就撞墙）。
主模型只是**临时拥堵（503）**时，程序会**原地退避重试**；**不会**换模型。
（想手动允许切换才设 `PETSAFE_MODEL_FALLBACKS=...`，但请先确认那个模型的日额度够。）

**看到这种报错**：

```
429 RESOURCE_EXHAUSTED ... limit: 20, model: gemini-3.6-flash
Please retry in 17h14m50s
```

说明**当天额度已经用完了**（不是 bug，也不是 key 的问题）。新版会直接告诉你：

```
The daily free-tier quota is exhausted for model 'gemini-3.6-flash' (20 requests/day).
It resets in 17h 14m.
```

**怎么办**：
1. **什么都不用改**，等重置（美西午夜 = 北京时间次日 16:00）再跑同一条命令；
2. 已成功的调用都在缓存里，**重跑不会重复扣额度**，会从断掉的地方继续；
3. 想马上跑，就换 `gemini-3.5-flash-lite`（额度多得多）：

```bash
# .env 里
PETSAFE_MODEL=gemini-3.5-flash-lite
```

4. 先用 `--dry-run` 确认脚本没问题，再正式跑。

### 📦 搬了文件夹之后 venv 坏了？（Unable to create process）

**症状**：

```
Fatal error in launcher: Unable to create process using
'"E:\old\path\.venv\Scripts\python.exe"  "E:\new\path\.venv\Scripts\streamlit.exe" run app.py'
```

**原因**：虚拟环境**不能搬家**。`.venv\Scripts\` 里的 `python.exe`、`pip.exe`、
`streamlit.exe` 这些启动器在安装时把解释器的**绝对路径写死在里面**了。
你把文件夹改名/移动之后，`streamlit.exe` 还在新位置，但它指向的解释器还在旧位置 → 报上面这个错。

> 注意：`python.exe` 本身**还能用**（它靠同目录的 `pyvenv.cfg` 找家），坏掉的只是那些启动器。

**30 秒临时可用**（不重装，直接跑）：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

**推荐彻底修好**（2 分钟，一步到位，所有启动器都恢复正常）：

```powershell
cd "E:\cnn gah\5511\project\experiment\petsafe-greenery"
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/
python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
python scripts\check_env.py
```

**别用 `pip install` 直接装**——`pip.exe` 也是坏的，会报同样的错；
**一律用 `python -m pip`**，它在当前解释器下运行，不依赖坏掉的启动器。

**搬文件夹不会丢东西**：`data/`、`results/`、`.env` 全是相对路径，
跟着项目目录一起走；只有 `.venv` 需要重建。

### 📊 实验跑完了，怎么让 PPT 里的数字变成真实数据？

**最省事：把 `results` 整个文件夹发给我**（`results/runs/<模型名>/` 那一层，
或者直接把整个 `results` 目录压缩发我），我这边一条命令就能重生成整套幻灯片。

你自己也能做（不需要我）：

```powershell
python scripts\make_slide_data.py        # 读最近一次 run -> slides/data/results.json
cd slides
node compile.js                          # 重新生成 PPTX
```

- `slides/slide-07.js` 的结果表**自动从 JSON 读数字**，不用手打；
- **离线模拟数据会被拒绝**（编译时打印 `refusing simulated (offline) results`），
  模拟数字不可能混进最终 PPT；
- 源文件在 `slides/slide-01.js` … `slide-10.js` + `slides/compile.js`。

**我需要哪些文件（按重要性）**：

| 文件 | 用来填什么 | 必须？ |
|---|---|---|
| `results/runs/<run>/summary.csv` | 第 7 页结果表、报告统计表 | ✅ 必须 |
| `results/runs/<run>/rubric_breakdown.csv` | 15 项评分细则的逐项通过率 | ✅ 必须 |
| `results/runs/<run>/usage.json` | 调用次数、耗时、模型名 | ✅ 必须 |
| `results/runs/<run>/<method>/*.json` | 单个场景的完整设计（案例页） | 建议 |
| `figures/fig*.png` | 图表（也可以我用 CSV 重画） | 可选 |
| `results/model_comparison.csv` | 两个模型的对比表（如果跑了两个模型） | 有第二套就有 |

**不用给我**：`.env`（里面有你的 API key）、`.venv/`、`results/cache/`。

### 🎓 三个「课堂技术」模块（讲义里的东西真的接在主流程上）

| 模块 | 对应讲次 | 干什么 | 怎么验证 |
|---|---|---|---|
| `src/kb.py` | **L3 知识表示**：Horn 子句、前向链推理 | 把安全与微气候规则写成 `(前提) => 结论`，用议程算法推导可种植清单，**每一次触发都有记录**（可以审阅推理过程）| `python scripts/test_kb_parity.py` —— **8 项全过**：形式化 KB 与生产过滤器在全部 25 个场景上一致 |
| `src/bayes.py` | **L3 不确定性**：贝叶斯公式、信念网络 | 把两个毒性来源当作对隐含真值「有毒」的含噪观测，用似然比形式融合；**参数由实测的 90.3% 来源一致率估出来**，不是拍脑袋 | 被 `src/aspca_resolver.py` 调用 |
| `src/clustering.py` | **L5 无监督学习**：K-means | 从零实现 Lloyd 迭代（不用 sklearn），对**已通过安全过滤**的候选做聚类，让调色板在微气候之间散开 | 被 `src/evaluate.py` 调用（多样性指数）|

**这三个模块是"能讲"的**——教授问"你用了课上讲的技术吗"，你可以说出文件名、
说出为什么用、说出怎么验证。

### 📂 想换个模型再跑一套数据？（结果不会互相覆盖）

**每个「后端 + 模型」都有自己的结果文件夹**，跑第二个模型不会动第一个模型的数据：

```
results/
  runs/
    gemini__gemini-3.5-flash-lite/     ← 第一个模型的数据
      agent/s01.json  zeroshot/s01.json  naive_rag/s01.json
      metrics_agent.csv  summary.csv  rubric_breakdown.csv
      manifest.json                     ← 谁、哪个模型、哪版代码、什么时候跑的
    deepseek__deepseek-v4.1-flash/      ← 第二个模型的数据（互不干扰）
  latest.json                           ← 指向最近跑完的那次
  model_comparison.csv / .md / .tex     ← 两套数据的并排对比表
```

**跑法**（跟平时一模一样，目录自己会分）：

```powershell
# 第一次：Gemini
python scripts\run_experiments.py --backend gemini --model gemini-3.5-flash-lite

# 第二次：DeepSeek（换个模型 id 就行）
$env:DEEPSEEK_MODEL="deepseek-v4.1-flash"
python scripts\run_experiments.py --backend deepseek

# 两套数据并排看
python scripts\compare_models.py --all
```

**重跑只覆盖同一个模型**：同一个模型重跑时，代码会比对配置指纹
（代码版本 + 调色板 + 轮数 + thinking + 模型名）：
- 指纹一致 → 直接用缓存，**不花钱**；
- 指纹不一致（改了代码或参数）→ 只有这个模型的文件被重算重写，**另一个模型的文件不动**。

**旧结果会被自动归位**：升级前的结果都平铺在 `results/` 下。升级后第一次运行时，
它们会被**移动**到各自模型的文件夹里（只移动、不删除），所以两个模型的数据不会混在一起。
屏幕上会打印 `[moved] s01.json (gemini-3.5-flash-lite) -> gemini__gemini-3.5-flash-lite/agent`。

**画图和报告用哪一套**：
```powershell
python scripts\make_figures.py                          # 默认用最近跑完的那次
python scripts\make_figures.py --results results\runs\gemini__gemini-3.5-flash-lite
```

**这个功能有专门的回归测试**：`python scripts\test_result_isolation.py`（不花钱、不碰你的真实结果）。

### 🔁 想换成中转 API / DeepSeek 怎么办（代码已经做好了）

项目里**已经内置了 OpenAI 兼容后端**（纯标准库实现，不需要装任何新包）。
切过去只要改 `.env` 四行：

```bash
PETSAFE_BACKEND=deepseek
DEEPSEEK_BASE_URL=https://sapi.zly163.cn/v1     # 你的中转地址
DEEPSEEK_API_KEY=sk-你的key
DEEPSEEK_MODEL=deepseek-chat                     # 以中转站 /v1/models 列出的为准
```

要点：

1. **端点已验证可用**：`POST https://sapi.zly163.cn/v1/chat/completions` 返回 401（Invalid token）
   = 地址对、协议对、只差真 key。
2. **模型名要自己确认**：中转站的模型名不一定和官方一致，先 GET `https://sapi.zly163.cn/v1/models`
   看列表（需要你的 key）。**不要选 reasoner 版**——它输出思维链、慢好几倍，
   而本项目所有可检查项都是 Python 判定的，思维链没有价值。
3. **三个方法自动用同一个模型**（指纹里含 backend + model）→ 公平性不受影响。
4. **旧的 Gemini 结果会自动作废重跑**（打印 `[stale]`）——
   绝不能把 Gemini 和 DeepSeek 的结果混在同一张表里。
5. **报告里要写清楚用的哪个模型、哪个端点**（放在 Reproducibility 那一节）。
6. 先空跑验证：`python scripts\run_experiments.py --backend deepseek --dry-run --start 0 --end 3`
7. 不花额度的整链自测：`python scripts\test_deepseek_path.py`

**换不换？我的建议：先别急着换。**
你的上一轮已经用 flash-lite 成功跑完 s03 了，失败的只是 zeroshot 的**一次**调用——
那是 Google 免费额度的高峰拥堵，不是代码问题。现在重试已经加长到 10 次（约 6 分钟退避），
大概率能扛过去。官方 API 在报告里也更可信（模型身份可验证）。
**但如果今天必须跑完、或连续几次都撞 503，就切中转**——付费接口没有日配额，也没有高峰排队。

**你用 `deepseek-v4.1-flash` 这类自定义模型名完全可以**，代码不校验模型名，
只保证三个方法用同一个模型。测试脚本也已经改成"以环境变量为准"，不会再误报。

中转站常见的两种兼容问题，代码都已自动兜住（`scripts/test_deepseek_path.py` 里有专门用例）：

| 现象 | 现象解释 | 自动处理 |
|---|---|---|
| HTTP 400 "Unsupported parameter: 'thinking'" | 中转/上游不认识 DeepSeek 专有的 `thinking` 字段 | 去掉该字段重试一次（探针和正式请求都兜） |
| HTTP 401 "Invalid token" | key 不对或没生效 | 报明确错误并停止（不烧额度） |
| HTTP 429 / 503 | 中转排队或上游限流 | 退避重试，最多 10 次 |

**不花额度的整链自测**（假 HTTP 层 + 真 SDK + 真 agent 代码，不需要 key）：

```bash
python scripts\test_gemini_path.py
```

它会跑完整的 gemini 链路（探活 → 工具调用 → 综合 → 修复 → 审计 → 三个方法 → 指标），
并检查 tier 1/2/3 物种都能被正确评估。**改完代码先跑这个**，比用真额度试错快得多。

> ⚠️ **别删 `results/`**：那是缓存 + 真实结果，删了要重跑 200 次 API。
> 想强制重跑用 `--force`，但只在怀疑结果有问题时才用。

**预计总时长**：25 场景 × 3 方法 ≈ 200 次调用。关 thinking 后按 8s/次算 ≈ **25–35 分钟**；
开着 thinking 或碰上高峰可能要 1.5–2 小时。**先跑 3 个场景测速，再决定要不要全量跑。**

> ⚠️ **重要：改了代码或配置之后，旧结果会自动作废。**
> 每个结果文件里都写了一个「配置指纹」（代码版本 + 配色数量 + 工具轮数 + thinking + token 上限）。
> 指纹对不上的场景会被打印成 `[stale] ... -> re-running it` 并**自动重跑**。
> 这样你不会把"旧代码的结果"和"新代码的结果"混在一起写进报告——那是**方法论错误**。
> （你现在 s01 的 12/15 是旧代码跑的，新版会自动重跑它。）

**先空跑一次（不花任何额度）**：

```bash
python scripts\run_experiments.py --backend gemini --dry-run --start 0 --end 3
```

它会检查参数、数据库、场景切片、模型链是否都接好了，打印计划然后退出，**一次 API 都不调**。
看到 `Everything is wired up.` 就说明脚本本身没问题，可以放心开跑。

```bash
# 三个方法 × 25 场景 = 75 个设计
python scripts/run_experiments.py

# 出图（PNG + PDF，报告和 PPT 直接用）
python scripts/make_figures.py
```

产出：

| 文件 | 内容 | 用在哪 |
|------|------|--------|
| `results/summary.csv` | 三种方法的 5 个指标总表 | **报告 Table 1 + PPT 第 5 页** |
| `results/rubric_breakdown.csv` | **15 条规则逐条得分率（诊断用）** | 报告 Discussion |
| `scripts/compare_one.py` | **一个场景、三种方法并排对比 + 毒性取证** | 答辩演示 |
| `results/metrics_<方法>.csv` | 每个场景的指标 | 报告的分组分析 |
| `results/<方法>/s01.json` | 每次生成的完整轨迹（含 tool 调用、审计结果） | 报告的案例分析 + Q&A 备用 |
| `results/usage.json` | 调用次数、token、耗时 | 报告"成本与效率"小节 |
| `figures/fig1_main_metrics.png` | 五个指标的三方法对比 | PPT 主图 |
| `figures/fig2_safety_by_scenario.png` | 25 个场景逐个安全率 | 报告"结果分析" |
| `figures/fig3_breakdown.png` | 按宠物配置分组 | 报告分组表 |
| `figures/fig4_db_composition.png` | 数据库构成 | 报告 Data 章节 |
| `figures/fig5_tool_effect.png` | 增益来自哪一步 | PPT 第 6 页 |
| `figures/fig6_rubric_items.png` | **15 条完整性规则逐条得分率** | 报告 Experiment + PPT 第 8 页 |
| `figures/fig7_completeness_dimensions.png` | 完整性按维度对比 | 报告 Experiment |
| `figures/fig_workflow.pdf` | 五阶段工作流图（脚本生成） | 报告 Description 章节 |

**看逐条诊断（最有用的自查）**：

```bash
cat results/rubric_breakdown.csv
```
每一行是一个方法、每一列是一条规则，值是"在多少比例的场景里拿到了这一分"。你会看到 baseline 丢分集中在哪几条——这段分析直接写进报告的 Discussion。

**跑完先自查**：

```bash
cat results/summary.csv
```

期望看到的形态（数字以你实际跑出来的为准）：
- agent 的 `pet_safety_compliance` = 1.0（100%，因为过滤是确定性的）
- 两个 baseline 的安全率明显低于 1.0（LLM 会推荐百合、发财树、龟背竹等有毒植物）
- agent 的 viability 和 baseline 相当或更高

⚠️ **绝对不要把 `results/offline_demo/` 里的数字写进报告**——那是模拟数据，用来调试管道的。真实实验一定用 `--backend gemini`（默认）。

---

## 6. Phase 5 · 做一个能现场演示的 App（11/13–11/14）

### 6.1 本地先跑起来

```bash
streamlit run app.py
```

浏览器会打开 <http://localhost:8501>。左侧填 API key，中间填阳台描述，点 **Design my planting scheme**。

**演示时最好看的地方**：页面右边有「Safety audit」面板，显示 ✅ 0 toxic plants；再展开「Agent reasoning trace」，能看到模型**调用了工具**、工具返回了候选池。这一屏就把"这是个 agent，不是聊天机器人"讲清楚了。

### 6.2 部署到公网（免费，汇报时更稳）

1. 注册 GitHub（<https://github.com>）→ 新建仓库 `petsafe-greenery`。
2. 把项目文件夹传上去（GitHub 网页上 "Add file → Upload files"，把整个文件夹拖进去；**不要上传 `.venv/`、`results/cache/`**，`.gitignore` 已经写好了）。
3. 打开 <https://share.streamlit.io> → **New app** → 选你的仓库 → Deploy。
4. 部署完成后点 **Advanced settings → Secrets**，加一条 `GEMINI_API_KEY = "你的密钥"` → Save → 重启 app。
5. 你会得到一个 `https://xxx.streamlit.app` 链接，**这个链接写进 PPT**。

### 6.3 兜底方案（强烈建议做）

现场网络挂了、API 超额度了怎么办？
**提前用 OBS / QuickTime 录一段 2 分钟的屏幕录像**，存在你电脑和 U 盘里，PPT 里放一个链接作为 backup。

---

## 7. Phase 6 · 写最终报告（11/16–11/25，别拖）

### 7.1 格式硬性要求（违反直接扣分）

| 项目 | 要求 |
|------|------|
| 纸张 | A4 |
| 字体 | 12pt Times New Roman |
| 页边距 | 四边各 2.5 cm |
| 行距 | 1.0（单倍行距） |
| 封面 | 1 页，**只有**标题 + 姓名 + 学号 |
| 正文 | **最多 10 页**（表格/图/参考文献/附录不计入这 10 页，但内容要"克制"） |
| 语言 | **英文** |
| 参考文献 | 无限长 |
| 排版工具 | **强烈建议用 LaTeX**（课程点名鼓励） |

### 7.2 章节结构（严格按课程给的六段来写）

课程给的评价维度是：Motivation / Description / Implementation / Data / Experiment Setting, Baselines, Performance / Discussions。照抄这个顺序最安全。

```
1. Motivation .............. 0.8 页   问题、为什么重要、给谁用
2. Description ............. 1.2 页   agent 工作流（四阶段）、模型、工具、为什么这么设计
3. Implementation .......... 1.5 页   关键函数、关键变量、伪代码（不要贴真代码！）
4. Data ................... 1.0 页   数据库怎么建的、来源、统计、为什么适合评测
5. Experiment .............. 2.5 页   评测设置、基线、主结果表 + 图、深入分析
6. Discussions ............. 1.5 页   性能直觉解释、局限性、改进方向、insight
   References .............. 不限
```

骨架已经写好：`report/report_skeleton.tex`

```bash
# 评分规则表 + 工作流图（先生成，报告里要引用）
python scripts/print_rubric.py --out report/rubric_table.tex
python scripts/make_workflow_figure.py

# 编译（编译两遍，交叉引用和页码才正确）
cd report
pdflatex report_skeleton.tex
pdflatex report_skeleton.tex
```

骨架**开箱即可编译**（图先是中性占位图，跑完真实实验后自动被替换）。正文 12 页左右（含占位符），填完内容后删减到 ≤10 页正文。
如果没有 LaTeX 环境，用 Overleaf（<https://overleaf.com>）上传 `report/` 目录即可，它自带 Times New Roman 等字体包。

> 不会用 LaTeX 也没关系：Word 里把 Times New Roman 12pt、行距单倍、页边距 2.5cm 设置好即可，**格式合规比用什么工具重要**。

### 7.2b 「搭配 / 护理 / 注意事项」怎么写进报告（这一块现在有硬证据了）

这部分不再是"我让模型输出这些"，而是**可验证的**：

**输出结构强制了四块内容**（`src/schema.py` 的 `DESIGN_SCHEMA`）：

| 内容 | 字段 | 落地例子 |
|------|------|----------|
| **空间结构** | `zones[].layer`（vertical / mid / ground）、`zone_role`、`placement`（含光照位置） | 垂直层：垂吊植物在栏杆；中层：容器植物靠墙；地面层：边缘低矮植物。**必须有一个 `role="grazing"` 的宠物可及区** |
| **搭配逻辑** | `layout_strategy`、`combination_logic`、`plants[].role_in_combination` | "细碎的垂吊叶 vs 宽大的直立叶形成对比；花期层负责色彩，骨架层全年常绿" |
| **护理** | `zones[].maintenance`、`care_instructions[{task, frequency, season}]` | 任务 + 频率 + 季节三件套，频率必须是真实的（"夏季每周两次"） |
| **养护注意事项** | `care_cautions[]` | "吊盆在风大的阳台极易积水烂根，热浪期间每天检查"、"西晒墙面会灼伤叶片"、"宠物会啃食地面层，已全部选用无毒种" |

**Design Completeness Score = 15 条二值条目，机器自动判**（`src/rubric.py`）：

| 维度 | 条目 | 判定规则（摘要） |
|------|------|------------------|
| 空间结构 A1–A3 | 垂直层 / 地面层 / 宠物啃咬区 | `layer` 字段或关键词命中 |
| 搭配逻辑 B1–B3 | 分层策略 / 搭配理由 / 每株的角色 | 字段存在且 ≥25 字符（理由需命中对比/质感/色彩/季相等词） |
| 护理 C1–C3 | ≥3 条护理 / 浇水频率 / 光照位置 | 频率需匹配 daily/weekly/every N days 等正则 |
| 注意事项 D1–D3 | ≥2 条 / 点名具体风险 / 针对本设计 | 风险词表；且必须点名本方案的某个植物或分区 |
| 宠物安全与覆盖 E1–E3 | 安全说明 / 点名宠物 / 每个分区≥2株且都有理由 | 结构判定 |

- 完整 0–15 分；**精简核心 0–5 分** = A1+A2+A3（三个空间分区）+ C2+C3（浇水频率 + 光照位置）——正好是你说的那个 0–5 的思路，我把它扩成了 15 条。
- **三个方法用的是同一套要求**（同一份 prompt 要求 + 同一份 JSON schema），所以比的是架构不是 prompt——这一点必须在报告里写清楚，否则审阅者会质疑公平性。
- 表格直接从代码导出，报告和评分器永远一致：

```bash
python scripts/print_rubric.py                        # markdown 表格
python scripts/print_rubric.py --latex                # LaTeX 表格
python scripts/print_rubric.py --out report/rubric_table.tex
python scripts/print_rubric.py --check results/agent/s01.json   # 给单个设计打分
```

- **完整性补全回路**：agent 生成后，如果确定性评分发现缺项（例如没有宠物啃咬区、没有浇水频率），缺失清单会回传给模型做一轮补全——和安全审计同一套机制。这是报告 Discussion 里非常好的一个点：**可检查的属性就应该由代码检查，再把失败项明确还给模型**。

### 7.2c 「基线推荐的植物不在我们的库里，安全分被低估」这个问题怎么答（重要）

这是审阅者最可能问的问题，你的直觉是对的，但**数据源选错了一个**：

- ❌ **FloraDB / plantfolio 直接拿来扩"安全库"** → 它们**没有**毒性标签。如果用它们推断毒性，一个被标成 safe 的植物可能其实有毒，你的安全性承诺就崩了。
- ✅ **正确做法：三层解析，每条判定都带出处**

| 层 | 数据源 | 权威性 | 作用 |
|---|---|---|---|
| Tier 1 | `data/plants.csv`（150 种，人工核过） | ASPCA + NC State | agent 的候选库 |
| Tier 2 | **ASPCA 全量抓取**（索引 1023 种，**成功解析 1010 种**，13 个空壳页按"无证据不猜"丢弃） | 兽医权威 | 库里没有的，查它 |
| Tier 3 | plantfolio-common-plants（980 种，958 种有毒性标签） | **官方标注 "ASPCA-aligned"**，但自己写了免责声明 → 只做补充 | ASPCA 没列的 species |
| — | `data/plant_aliases.json`（3872 个别名） | 名称归一化 | "Peace Lily Sensation" → 规范学名 |

已经实现好了：

```bash
python scripts\fetch_aspca_full.py     # 抓 ASPCA 全量（我已抓好，你不用跑）
python scripts\fetch_plantfolio.py     # 抓 ASPCA-aligned 补充库（已抓好）
python scripts\check_sources.py        # 覆盖率 + 两个源的一致率
```

**这不是拍脑袋，是量出来的**（`scripts/check_sources.py` 的结果）：

| 检验 | 结果 | 意义 |
|---|---|---|
| 150 种人工库 vs ASPCA 全量 | **0 处分歧** | 你的手工标签确实忠实于 ASPCA |
| ASPCA vs ASPCA-aligned 补充库（155 种重叠） | **140 种一致（90.3%）**，15 种分歧 | 补充库**不能**当权威用 |
| 分歧样例 | 补充库把 Borage / Lovage / Tarragon 标成无毒，ASPCA 标成对猫狗有毒 | 补充库会**漏报**毒性 |

结论就一句话：**补充源只能用来"多覆盖一些物种"，绝不能用来"判定安全"**。这一条直接写进报告，是加分项。

**评估器现在报两个安全数**：

| 指标 | 含义 | 用途 |
|---|---|---|
| `pet_safety_compliance` | **保守版**：只有 ASPCA 认证的才算安全 | 安全承诺用这个 |
| `pet_safety_compliance_resolved` | **公平版**：允许补充源，且只在"能判定的物种"上算 | 三个方法公平比较用这个 |

两者之差就是"你的库有多大"带来的影响，**必须在报告里明确写出来**，不能让读者猜。

同样的处理也给了园艺指标：`horticultural_viability_assessed`（只在知道光照/水分的物种上算）+ `viability_coverage`（能评估的比例）。

> 📌 **报告里这样写（可以直接用）**：
> "The curated catalogue is the agent's candidate pool, not a yardstick for the baselines. To avoid penalising a baseline for naming a species our catalogue happens to omit, every recommended name is resolved against the full ASPCA index (1,023 plants) and, where the ASPCA is silent, against an ASPCA-aligned secondary catalogue, with the provenance of each verdict recorded. We report both a conservative safety rate (ASPCA-certified species only) and a resolved rate over the species that could be judged at all; the agent's advantage is that its 100% safety is a property of the architecture, whereas the baselines' safety depends on the model's memory."

**可选：更大的 agent 候选库**（用来回应"agent 只是因为池子小才安全"）

```bash
python scripts\build_extended_catalogue.py
set PETSAFE_DB_PATH=data/plants_extended.csv   # PowerShell
```

实测：**1363 种**（150 人工 + 447 ASPCA 全量 + 766 ASPCA-aligned），其中 **818 种**对猫狗都安全。
再用同样的命令跑一遍实验，对比安全率和可存活率。**这是加分项，不是必须的**——报告里说明"即使把池子扩到 1000 种，安全性依然由过滤机制保证"就够了。

### 7.3 每章具体写什么（照抄这个思路）

**Motivation**——不要泛泛而谈"AI 很重要"。你的杀手锏是**具体数字**：
> "More than 700 ornamental species carry compounds dangerous to companion animals. ASPCA lists *Lilium* species as causing acute renal failure in cats; *Cycas revoluta* causes liver failure in dogs. In our benchmark of 25 balcony scenarios, a zero-shot LLM recommended a toxic species in X% of scenarios — see Table 1."

**Description**——画一张四阶段流程图（Page 1 就画，能用 PowerPoint 画完截图，或用 draw.io）：
```
用户 brief → ①约束抽取(LLM) → ②确定性筛选(Python/DB) → ③设计合成(LLM) → ④审计与自修正(Python)
                    ↑                                    ↑
              读工具调用                             只用第②步返回的候选
```
关键论点：**安全相关的决策由不会幻觉的确定性代码做，LLM 只负责它擅长的语言理解与空间设计。**
再解释两个 baseline：zero-shot（纯参数记忆）、naive RAG（BM25 检索但**不过滤毒性**）——后者专门用来分离"接地"和"安全过滤"两个变量的贡献。

**Implementation**——用**伪代码**（课程明确说"不要贴真代码"）：
```
Algorithm 1: DualConstraintAgent(brief)
 1: (pets, light, moisture) ← Gemini.parse(brief)
 2: C ← Database.filter(pets, light, moisture)     # 确定性，含约束放宽阶梯
 3: design ← Gemini.compose(C, schema=DESIGN_SCHEMA)
 4: findings ← Auditor.check(design, pets, light, moisture)
 5: if not findings.passed:
 6:     design ← Gemini.repair(design, findings, C)
 7: return design, findings
```
然后写清楚关键实现细节：
- 工具调用的 JSON schema（`src/tools.py`）
- **约束放宽阶梯**：严格查询为空时依次放宽水分→光照，**宠物安全过滤永不放宽**，且放宽会记录并告知用户（这是很好的 discussion 点）
- 缓存机制（`src/llm.py`）：`results/cache/`，key = hash(model, prompt, schema)，保证可复现且省额度
- 评估是独立的确定性代码，从不询问模型"你对吗"

**Data**——这一章最容易拿分，因为你有**真实可复现的数据管线**：
- 数据来源：ASPCA Animal Poison Control（毒性标签，ground truth）+ NC State Extension Plant Toolbox（光照）+ 人工整理（水分）
- 关键统计：150 种，其中对猫狗均无毒 60 种、对猫有毒 90 种、对狗有毒 82 种
- 为什么适合评测：它是**二值硬约束**（有毒/无毒），判定无歧义；且包含真实园艺约束，不是人造玩具任务
- 表格：光照×水分覆盖矩阵（说明有一个空格由放宽阶梯兜底）
- **局限性也要写**：数据库只覆盖 150 种，不是全部 1000+ 种；只覆盖猫/狗，未覆盖兔子等

**Experiment**——
- 设置：25 场景 = 3 光照 × 3 水分 × 4 宠物配置（猫/狗/猫+狗/无宠物对照），随机种子/温度固定
- 基线：B1 zero-shot、B2 naive RAG
- 主结果表（`results/summary.csv` 直接填）：

  | Method | Pet safety ↑ | Horticultural viability ↑ | Dual-constraint ↑ | Completeness (0–15) ↑ | Out-of-DB rate ↓ |
  |---|---|---|---|---|---|
  | B1 Zero-shot | | | | | |
  | B2 Naive RAG | | | | | |
  | **Proposed** | | | | | |

- **第二张表（完整性拆解，强烈建议加）**：

  | Method | zones A1–A3 | care C2–C3 | 核心分 (0–5) | 平均缺失条目数 |
  |---|---|---|---|---|
  | B1 Zero-shot | | | | |
  | B2 Naive RAG | | | | |
  | **Proposed** | | | | |

- **两张新图**（`figures/fig6_rubric_items.png`、`figures/fig7_completeness_dimensions.png`）：
  fig6 是**逐条得分率**，一眼看出 baseline 到底缺哪几项（通常是"宠物可及区""注意事项要具体""安全说明要点名宠物"），这是全篇最有信息量的一张图。

- 深入分析（不要只报数字）：
  - 为什么 agent 安全率是 100%：因为过滤是确定性的，**不是模型"更小心"，而是模型根本没机会看到有毒植物**
  - 为什么 baseline 的安全率低但 viability 不低：LLM 知道哪些植物喜欢半阴，但不知道哪些有毒 → **两个约束是独立的，grounding 解决一个不解决另一个**
  - B1 vs B2 的差说明了 RAG 的作用；B2 vs Proposed 的差说明了**负向过滤**的作用
  - 失败案例分析：从 `results/baseline1_zeroshot/s03.json` 里挑一条 LLM 推荐了百合的设计，放进报告

**Discussions**——
- 局限性：数据库规模有限；只测了 25 个场景和 2 种宠物；一次工具调用的抽取错误会传导（约束抽取准确率可单独报一个指标）；模型版本更新会影响结果
- 改进方向：多轮工具调用（让 LLM 主动查更多）、引入置信度/来源引用、向量检索 + 确定性过滤的组合、扩展到兔子/仓鼠等宠物
- **最有价值的一句 insight**：*在安全攸关的领域，正确的架构是让 LLM 负责它不确定但擅长的部分，把可以确定性判定的约束交给可验证的代码；Agent 的价值不在"更聪明的模型"，而在"把工具接到正确的位置"。*

### 7.4 引用与查重

- 参考文献至少 10 条：ASPCA 页面、NC State、Missouri Botanical、Google AI 文档、openJiuwen、那篇 WebAgents survey（课程给的 [1]）、Gemini API 文档、BM25 原始论文、ASPCA 年度报告等。
- ⚠️ **Turnitin 相似度必须 < 16%（绿色区间）**。
  - 代码提交通常也会被扫 → 注释和文档别直接复制别人的仓库。
  - 报告里**不要复制教材段落**，要改写成自己的话。
  - 提交前 48 小时跑一次 Turnitin（Canvas 里 "Check for Similarity"），有黄灯就改。

---

## 8. Phase 7 · 做 PPT（11/13–11/15）

### 8.0 PPT 已经给你做好了（`docs/PetSafe-Greenery-presentation.pptx`）

10 页、16:9、**每一页都写好了演讲者备注**（备注就是讲稿，打开 PowerPoint 按"演示者视图"看得到）。你只需要做两件事：

1. **把真实数字填进去**（第 7 页表格里的 `-` 换成 `results/summary.csv` 的真实值）；
2. **把两张占位图换成真图**（第 7 页 `fig1_main_metrics`、第 8 页 `fig6_rubric_items`）。

第 2 步在 PowerPoint 里 2 分钟就能做完，**不用碰代码**：

> 右键点那张写着 PLACEHOLDER 的图 → **更改图片** → **来自文件** → 选 `figures/fig1_main_metrics.png`（或 `fig6_rubric_items.png`）

如果你想改版式，源码在 `slides/slide-01.js` … `slide-10.js`（每页一个文件），改完跑：

```bash
cd slides
NODE_PATH="$(npm root -g)" node compile.js
```

**或者更省事**：直接跟我说"帮我把 PPT 重新生成一版"，我拿到你的真实数字后 5 分钟出新版。


**5–7 分钟 + 1–2 分钟 Q&A**。别做 30 页，做 **10 页**。

| 页 | 内容 | 时间 |
|----|------|------|
| 1 | 标题页：题目、姓名、学号 | 15 秒 |
| 2 | **问题**：700+ 种有毒植物；给一个真实案例（LLM 给你推荐百合） | 45 秒 |
| 3 | **动机与用户**：宠物主人 / 景观学生 / 初级设计师 | 30 秒 |
| 4 | **方法**：四阶段流程图（核心页，多留时间） | 60 秒 |
| 5 | **数据库**：150 种、来源、覆盖矩阵（fig4） | 45 秒 |
| 6 | **实验设置**：25 场景、3 方法、4 指标 | 45 秒 |
| 7 | **主结果**：fig1 + summary 表 | 60 秒 |
| 8 | **深入分析**：fig2/fig5 + 一个失败案例（baseline 推荐了百合） | 60 秒 |
| 9 | **演示 / 讨论**：直播 App 或录屏 + 局限性 + insight | 60 秒 |
| 10 | 结论 + 仓库链接 | 20 秒 |

`docs/SLIDES_OUTLINE.md` 里有每一页的**逐字讲稿**，直接改成你的语气即可。

**Q&A 高频问题，提前想好答案：**
1. "为什么不直接用 RAG + LLM 过滤？" → 负向过滤必须确定性和可审计，不能靠 LLM 自觉。
2. "数据库怎么保证正确？" → ASPCA 是权威源，脚本自动采集，每行带 source_url，可逐条追溯。
3. "你的方法有没有可能漏掉有毒植物？" → 只对库内物种做保证；库外物种会被评估器记为 out-of-database 并计入不安全。
4. "只用了一个 LLM、一个模型，泛化性如何？" → 承认局限，说明与模型无关：架构上把确定性放在了正确的位置，换模型不改变安全性下界。
5. "25 个场景够吗？" → 承认样本小，列出已覆盖的 12 种光照×水分组合和 4 种宠物配置，说明这是作业规模下的可行方案。

---

## 9. Phase 8 · 提交（Canvas）

| 交什么 | 入口 | 时间 |
|--------|------|------|
| PPT | Canvas → "Presentation slides submission" | **11/15 23:59** |
| 最终报告 PDF | Canvas → "project report submission" | 11/29 23:59（**建议 11/27**） |
| 源码 zip | Canvas → "project code submission" | 同上 |

**代码 zip 打包**（在项目根目录执行）：

```bash
cd petsafe-greenery
rm -rf results/cache results/offline_demo
zip -r petsafe-greenery-submission.zip . \
  -x "*.venv*" -x "__pycache__*" -x "*.pyc" -x ".cache/*" -x ".git/*"
```

zip 里**必须包含**：README.md、requirements.txt、src/、scripts/、data/plants.csv、data/scenarios.csv、app.py、results/summary.csv、results/metrics_*.csv、figures/。
**不要包含**：.venv/、results/cache/、你的 API key、.env。

**可复现性检查（提交前必做）**：在**一个干净的目录**里 unzip + `pip install -r requirements.txt` + `python scripts/run_experiments.py --end 3`，能跑通才算合格。

---

## 10. 报错速查表

| 报错 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'google'` | 没激活虚拟环境 / 没装依赖 | `source .venv/bin/activate && pip install -r requirements.txt` |
| `429 RESOURCE_EXHAUSTED` | 免费额度用完 | 等太平洋时间午夜重置，或换 `--model gemini-3.5-flash-lite` |
| `API key not valid` | 密钥没设或被 GOOGLE_API_KEY 覆盖 | `unset GOOGLE_API_KEY`，检查 `echo $GEMINI_API_KEY` |
| `FileNotFoundError: Ground-truth database not found` | 在错误的目录下运行 | `cd petsafe-greenery` |
| `pip install` 超时 | 网络 | 加 `-i https://mirrors.aliyun.com/pypi/simple/` |
| `Model not found` | 模型名过期 | 换 `gemini-3.5-flash-lite` 或 `gemini-3.8-flash` |
| Streamlit 页面空白 | 密钥没填进 Secrets | 网页左侧 Secrets 里加 `GEMINI_API_KEY` 后重启 |
| 出图报 `No module named 'matplotlib'` | 缺依赖 | `pip install matplotlib` |
| 结果数字全是 0 或 agent 也推荐了有毒植物 | 你在用 `offline_demo` 的旧结果 | 删掉 `results/offline_demo/`，用默认 gemini backend 重跑 |
| `'ascii' codec can't encode characters in position 53-56` | **API key 里混进了非 ASCII 字符**（从网页复制时带进的中文/全角字符）。SDK 把 key 放在 `x-goog-api-key` 请求头里，而 HTTP 请求头只能是 ASCII，所以请求**根本没发出去**就死了 | 打开项目根目录的 `.env`，把 `GEMINI_API_KEY=` 那行改成**只剩 key 本身**（不要有中文注释、全角字符、结尾空格），然后从 https://aistudio.google.com/apikey 重新复制。运行 `python scripts\check_env.py` 会直接告诉你脏在第几位 |
| 同一报错但检查 key 又是干净的 | Windows 环境变量/控制台编码不是 UTF-8 | **本项目已修好**：所有文件强制 UTF-8 写、失败自动降级为纯 ASCII JSON、控制台自动切 UTF-8、非 ASCII 的请求内容会自动清洗后重试。重新解压新版 zip 即可。仍报错就跑一次 `chcp 65001` 或设 `PYTHONUTF8=1` |
| 控制台显示 `???` / `â€”` 乱码 | 终端代码页不是 UTF-8（**只是显示问题，不影响结果文件**） | 跑一次 `chcp 65001`；或设环境变量 `PYTHONUTF8=1` |
| 路径里有 `&`、空格、中文导致各种怪错 | Windows 路径转义问题 | 把项目挪到纯英文无空格路径，例如 `E:\petsafe-greenery` |

---

## 11. 一句话总结

**不要自己写代码。要做的是：拿 key → 跑 3 个场景验证 → 跑满 25 场景 → 出图 → 把图和数字写进英文报告和 PPT → 提前 48 小时提交。**

> ⚠️ **Windows 用户注意**：如果你遇到过 `'ascii' codec can't encode characters in position 53-56`，
> **99% 是 `.env` 里的 API key 混进了非 ASCII 字符**（从网页复制时带进来的中文或全角字符）。
> 1）先跑 `python scripts\check_env.py`，它会直接告诉你第几位有脏字符；
> 2）把 `.env` 里 `GEMINI_API_KEY=` 那行改成**只剩 key 本身**，重新从
> https://aistudio.google.com/apikey 复制；
> 3）再跑 `python scripts\run_experiments.py --start 0 --end 3`。
>
> 新版 zip 已经加了多重保险（key 自动清洗 + 提示、文件强制 UTF-8、非 ASCII 内容自动重试、
> 失败时把内部 traceback 存到 `results/last_error_traceback.txt`），但**把 key 抄干净才是正解**。

数据库、agent、基线、评估、出图、演示 App、README、报告骨架、PPT 讲稿，都已经在 `/workspace/petsafe-greenery/` 里了。
