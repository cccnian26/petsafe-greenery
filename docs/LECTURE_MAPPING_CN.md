# 课程技术映射：我们用到了哪些讲课内容，哪些没用到

> 对应课程：COMP5511 Artificial Intelligence Concepts（Dr. Wenqi FAN）
> 用讲义原文核对过，不是凭印象写的。

---

## 一、结论先说

**你的项目几乎已经把整门课的技术都用上了**——而且每一条都接在真实运行的代码里，
不是写在报告里凑数。用不到的主要只有 **L6/L7 的神经网络（CNN/RNN/LSTM）**，
而报告第 2.4 节**已经给了正当理由**（安全判定必须可审计、必须每次一样）。

所以「应该怎么修改」这个问题的答案不是"去补几个技术"，而是：

> **把已经用上的技术，在 PPT 讲稿里说出来。**

教授看到的是你的架构，而不是你的引用列表。

---

## 二、逐条映射（全部经过代码验证）

| 讲次 | 主题 | 用到了吗 | 在哪里 | 证据 |
|---|---|---|---|---|
| **L2** | 搜索：BFS/DFS、A\*、贪心、爬山 | ✅ | `src/agent.py` 工具循环（`MAX_TOOL_ROUNDS=3`，有界 generate-and-test）；`src/tools.py` 的**约束松弛阶梯**（先松湿度再松光照，宠物安全永不松）| 报告 §2.1/§2.2 |
| **L3 KR** | 符号知识表示、PL/FOL、前向链 | ✅ | **`src/kb.py`**：Horn 子句知识库 + 前向链推理引擎（议程算法，每次触发都记录）| `scripts/test_kb_parity.py` **8 项全过**：KB 与生产过滤器在全部 25 个场景上一致 |
| **L3 不确定性** | 贝叶斯推理、信念网络 | ✅ | **`src/bayes.py`**：似然比形式的贝叶斯融合；参数**由数据估出来**（两源重叠 155 种中一致 140 种 = 90.3%，且分歧全单向 → 敏感度/特异度）| `src/aspca_resolver.py:186` 调用 `fuse_verdict()` |
| **L4** | 监督学习、模型选择、偏差-方差、训练/测试划分 | ⚠️ 部分 | **不训练任何模型**（有正当理由，见下）。但用到了纪律本身：评分细则先在 3 个场景开发，再在另外 22 个场景上测量 | 报告 §2.4 |
| **L5** | 无监督学习、聚类、K-means | ✅ | **`src/clustering.py`**：从零实现的 Lloyd 迭代 K-means，对**已通过安全过滤**的候选做聚类，保证调色板在不同微气候簇间分散（不碰安全约束）| `src/evaluate.py:65` 调 `diversity_index()` |
| **L6** | 深度神经网络、激活函数、训练 | ❌ | 不训练网络。用的是现成的 LLM | 报告 §2.4 有说明 |
| **L7** | CNN、RNN、LSTM | ❌ | 同上（LLM 是 transformer，不在讲义覆盖范围）| — |
| **L8** | **专家系统**：知识库 / 推理机 / 知识获取 / 用户界面 | ✅✅ | 知识库 = `data/plants.csv` + `aspca_snapshot.json`；推理机 = `src/tools.py` + `src/evaluate.py`；知识获取 = `scripts/fetch_aspca*.py` / `fetch_ncstate.py` / `fetch_plantfolio.py` / `build_database.py`；用户界面 = `app.py`（Streamlit）| 四要素齐全，是本项目最贴的一条 |
| **L8** | **推荐系统**：数据驱动、候选生成与排序 | ✅ | `src/retrieval.py` 的 BM25（k1=1.5, b=0.75，自己实现）；`src/tools.py:query_pet_safe_plants` = 候选生成 + 排序 + 约束过滤 | `src/baselines.py` 的 B2 就是"纯推荐系统、不加过滤" |
| **L9** | 生成式 AI / LLM：n-gram→word2vec→BERT/GPT→大模型，prompt 补全，副作用 | ✅✅ | 整个架构就是 L9 的"prompt-based completion + 工具使用"；**幻觉的副作用正是本项目的动机**（零样本基线推荐了有毒植物）；讲义里点名的 DeepSeek 正是你现在用的模型 | 报告 §1、§6 |

**统计：10 个主题里 8 个直接用上，1 个部分用，1 个（L6/L7）明确不用且有书面理由。**

---

## 三、唯一没用上的：神经网络（L6/L7）

### 为什么不用（报告 §2.4 已经写好了）

> "There are no labelled examples — no target design for a balcony — so nothing could
> be fitted, and the input is a short brief rather than an image or a sequence.
> More importantly, the component that decides whether a plant is safe for a pet
> must be auditable: it has to give the same answer on every run and machine, and
> its reasoning must be inspectable by a reader who does not trust the model."

**这个答案在学术上是对的，不要为了"用满技术栈"去硬凑一个神经网络。**

### 如果教授追问：可选的三种补救（按性价比排序）

| 方案 | 补什么课 | 工作量 | 风险 | 建议 |
|---|---|---|---|---|
| **A. 什么都不改，把理由讲清楚** | — | 0 | 0 | ✅ **首选**。用现成的"确定性优于不可审计"这条论证 |
| **B. 训练一个"学习型安全基线"做对照** | L4 + L6 | 1–2 天 | 中（要加代码、图、报告段落，报告已满 10 页） | 只在时间充裕时做 |
| **C. 把 LLM 的表示用于聚类** | L5 + L9 | 半天 | 低 | 你已经有 K-means 了，只差 embedding |

### 方案 B 具体怎么做（如果真要做）

用 numpy 从零写一个**两层 MLP**（L6：层、激活函数、反向传播），
在 ASPCA 的 1010 个物种上训练"是否对猫有毒"的二分类器，特征用物种名的 BOW/哈希。

**这个方案真正的价值不是"补技术"，而是产生一个非常有力的对照实验：**

> 学习型模型准确率 X%，但在安全关键类别的召回率只有 Y%；
> 符号规则系统给出 100% 的**可溯源**保证。

这正好把"为什么这个项目不用神经网络"从"辩解"变成"有数据支撑的结论"——
而这恰恰是 L6/L7 之后（也就是 L9 的 prompt-based 时代）更值得讲的东西。

**但**：报告已经 12 页（封面 1 + 正文 10 + 参考文献 1），正文页数是硬上限，
加这个要挤掉别的内容。以 11/29 的提交期限和当前进度，**不建议**。

---

## 四、PPT 怎么改（4 分钟，最重要的改动）

**原 PPT 里一个课程术语都没有。** 我已经把这部分补上了：

`slides/notes.js` 新增 → 每页都有讲稿备注，含**逐页时间预算**和**要念的原话**。

```
slide 01  0:00–0:12  (12 s)  开场 + 一句话论点
slide 02  0:12–0:42  (30 s)  真百合 / 苏铁，两行数据，不要念表格
slide 03  0:42–0:55  (13 s)  三类用户
slide 04  0:55–1:35  (40 s)  核心：任务拆分 → 说出 L9 + L8
slide 05  1:35–2:00  (25 s)  知识库 + 来源一致性 90.3%
slide 06  2:00–2:35  (35 s)  三方法同 prompt → 说出 L8 推荐系统
slide 07  2:35–3:10  (35 s)  核心：念表格 → 说出 L2 搜索
slide 08  3:10–3:35  (25 s)  15 项细则 → 说出 L4 纪律
slide 09  3:35–3:45  (10 s)  局限，只念两条
slide 10  3:45–4:00  (15 s)  一句话结论 + L8/L9 收尾
                         ─────
                         合计 240 s = 4:00 整
```

### 必须在讲稿里说出口的四句话

这四句把项目和课程挂上钩，每句 3–5 秒：

1. **第 4 页**：
   > "The LLM is the Language Model of Lecture 9 — prompt-based completion used
   > as a general task solver. And the filter plus the ground-truth database is
   > an **Expert System** in the sense of Lecture 8: a knowledge base, an
   > inference engine, and a user interface. **The safety-critical decision never
   > goes through the neural network.**"

2. **第 5 页**：
   > "This is the **knowledge acquisition** step of Lecture 8 — the database is
   > built by a reproducible script, not by hand."

3. **第 7 页**：
   > "The agent loop is a bounded **generate-and-test search** in the sense of
   > Lecture 2 — the candidate pool is the open list, the filter closes it, and
   > the cost of the search is the number of model calls, which I report."

4. **第 8 页**：
   > "That is the discipline of **Lecture 4** applied to a non-learned system: the
   > rubric was developed on three scenarios and then measured on the remaining
   > twenty-two, and the model never sees its own score — only the list of items
   > it failed."

### Q&A 1 分钟准备

`slides/notes.js` 的 `QA` 字段里写了 **5 个最可能被问的问题 + 逐字回答**：

| 问题 | 回答要点 |
|---|---|
| "为什么不用神经网络？" | 无标注数据 + 安全判定必须可审计、可复现 |
| "100% 安全是不是过滤器做的，agent 贡献什么？" | 是，而且故意如此；agent 的贡献是 15/15 的完整设计 |
| "你的 ground truth 凭什么可信？" | 溯源到 ASPCA URL、两源 90.3% 一致、KB 形式化实现 + 一致性测试 |
| "完整度分数是不是你自己的主观判断？" | 15 条都有存下来的检测规则，core 5 分就是三区+浇水+光照 |
| "25 个场景够吗？" | 不够，我把它明确写成局限；我保证的是每个场景的确定性保证，不是统计结论 |

---

## 五、你现在最该做的（按顺序）

1. **今天**：把真实实验数据发我 → 我重生成 PPT（第 7 页表格自动填）
2. **今天**：读一遍 `slides/notes.js` 的 10 段备注，**照着念 3 遍**，掐表到 4 分钟
3. **已完成**：报告 §2.4 "Relation to the concepts of the course" 已经把六条映射写成表格
   （Searching / KR+前向链 / 不确定性+贝叶斯 / ML 纪律 / **K-means 聚类** / 专家系统+推荐系统），
   并附了"为什么不用神经网络"的论证。报告已压回 **12 页 = 封面 1 + 正文 10 + 参考文献 1**，
   符合课程 "at most 10 pages of contents" 的要求。
4. **有剩时间再考虑**：方案 B（训练一个学习型基线做对照）

> ⚠️ 按课程说明（`COMP5511_project_spec 2026_updated_Fri.pdf` 原文）：
> - **presentation slides 截止 11/15** —— 已过 2 天
> - **课堂展示 11/20 或 11/27**（5–7 分钟 + Q&A）
> - **报告 + 代码 11/29 23:59 截止，"No late submission is accepted"**
> - 报告格式：A4、12pt Times New Roman、四边 2.5cm、单倍行距、封面 1 页、
>   **正文最多 10 页**、参考文献不限
>
> 如果 slide 文件还没交，**先把现在这版交上去占位**，再用真实数据更新。
