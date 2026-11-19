# PPT 讲稿大纲（5–7 分钟 + 1–2 分钟 Q&A）

**规则**：10 页，平均每页 35–40 秒。**不要**念屏幕上的字；每页只讲一句话的核心论点。
把 `results/summary.csv` 的真实数字填进第 7 页；把 `figures/*.png` 拖进第 5、7、8 页。

---

## 第 1 页 · 标题（15 秒）

**屏幕**
```
PetSafe-Greenery: A Dual-Constraint Agentic Workflow for
Pet-Friendly Balcony and Courtyard Planting Design
CHEN Niannian · 26063619G
COMP5511: Artificial Intelligence Concepts
```

**讲**：Good morning. I built an AI agent that designs planting schemes for balconies where a cat or a dog lives — and that cannot recommend a plant that would poison the animal.

---

## 第 2 页 · 问题（45 秒）

**屏幕**：三张图/图标 + 一行大字
> "Beautiful for you. Fatal for your cat."

- 左：真百合 *Lilium* → 猫急性肾衰竭（ASPCA）
- 中：苏铁 *Cycas revoluta* → 犬肝衰竭
- 右：黄金葛 *Epipremnum aureum* / 白鹤芋 *Spathiphyllum* → 草酸钙针晶

**讲**：
Seven hundred plus ornamental species are dangerous to cats or dogs. True lilies cause acute renal failure in cats. Sago palm causes liver failure in dogs. Pothos and peace lily are in almost every balcony plant shop in Hong Kong.
The problem is not that these plants are rare. It is that **LLMs recommend them**. I asked a zero-shot LLM for a cat-friendly sunny balcony, and it proposed a peace lily. That is not a reasoning error — it is a **fact the model cannot check for itself**.

---

## 第 3 页 · 动机与用户（30 秒）

**屏幕**：三个用户卡片 + 目标
> Pet-owning residents · Landscape-architecture students · Junior planting designers
> Design space: balcony / courtyard / rooftop terrace

**讲**：The users are people who cannot judge toxicity themselves. The task is a genuine two-constraint optimisation: horticultural viability **and** veterinary safety, simultaneously.

---

## 第 4 页 · 方法（60 秒）★核心页

**屏幕**：五阶段流程图（**已经生成好**：`python scripts/make_workflow_figure.py` → `figures/fig_workflow.pdf`）

```
Brief ─► ①LLM 抽取约束 ─► ②Python 确定性筛选 ─► ③LLM 合成设计 ─► 最终方案
                    (毒性+光照+水分)            │
                                            ▼
        ④a Python 安全审计 ──(违规)──► LLM 修正
        ④b Python 完整性评分(15条) ─(缺项)─► LLM 补全
```

**讲**：
My question is: **if a constraint can be checked deterministically, should an LLM be allowed to decide it?**
My answer is no — so I split the task. The LLM does what it is good at: reading the brief and composing a spatially organised design. Python does what the LLM is bad at: deciding whether a plant is poisonous.
Stage three is the key: a deterministic filter over a curated database removes every species toxic to any pet in the house, then keeps only species that match the light and moisture. The model then only sees what is already safe. Finally a deterministic auditor re-checks the finished design; if it finds a violation, the model gets one repair round.
One more detail: if the strict filter returns nothing, horticultural constraints may be relaxed — but **the pet-safety filter is never relaxed at any level**. That asymmetry is the whole safety argument.

And because safe plants are not enough, the output contract obliges the design to contain four things beyond the species: the **spatial structure** — a vertical layer, a mid layer, a ground layer, and one zone the pet can actually reach; the **combination logic** — how the plants work together in height, texture, colour and seasonal rhythm; the **care** — what to do, how often, in which season; and the **care cautions** — what goes wrong with this particular scheme.

---

## 第 5 页 · 数据库（45 秒）

**屏幕**：`figures/fig4_db_composition.png` + 右侧数字
> 150 species · 60 non-toxic to both · 90 toxic to cats · 82 toxic to dogs
> ASPCA Animal Poison Control (toxicity) + NC State Extension (light) + curated (moisture)

**讲**：
The ground truth is 150 species, and it is built by scripts, not by hand — every toxicity label is parsed from the ASPCA page of that species, with the source URL stored on the row. A species whose page has no explicit toxicity statement is dropped: an unverified label is worse than no label.
Sixty species are safe for both cats and dogs; ninety are toxic to cats. That balance is what makes the safety metric discriminative instead of trivially satisfied.

---

## 第 6 页 · 实验设置（45 秒）

**屏幕**：3 个方法卡 + 25 场景矩阵
> 25 scenarios · 3 light × 3 moisture × 4 pet configurations (cat / dog / multi-pet / no-pet control)
> B1 zero-shot · B2 naive BM25 RAG without safety filtering · Proposed

**讲**：
Twenty-five scenarios, each a realistic brief with a structured ground truth. The scenarios cross three light classes, three moisture classes and four pet configurations.
Three methods. Baseline one is the plain LLM with no tools. Baseline two retrieves by BM25 keyword similarity but **deliberately does not filter toxicity** — that baseline is what separates "grounding" from "safety filtering" in the results.
Four metrics, all computed by deterministic Python against the same database. The evaluator never asks the model whether it was right.

---

## 第 7 页 · 主结果（60 秒）

**屏幕**：`figures/fig1_main_metrics.png` + 下方 summary 表

| Method | Safety ↑ | Viability ↑ | Dual ↑ | Completeness ↑ (0–15) |
|---|---|---|---|---|
| B1 zero-shot | *填* | *填* | *填* | *填* |
| B2 naive RAG | *填* | *填* | *填* | *填* |
| **Proposed** | *填* | *填* | *填* | *填* |

（完整性 = 15 条二值规则、代码自动判定；同一张表也可用 0–5 的核心分：A1+A2+A3 三个空间分区 + C2 浇水频率 + C3 光照位置）

**讲**：
The headline result: the agent's pet-safety compliance is exactly 100%, while both baselines are far below. And the reason is architectural, not prompt-based — the model is **never given the opportunity** to pick an unsafe species, because the filter removes them before the model sees the list.
Notice the second result, which I find more interesting: **viability is competitive across all three methods**. The baselines are not bad at horticulture. They just cannot know which of the plants they like are lethal.

---

## 第 8 页 · 深入分析（60 秒）

**屏幕**：`figures/fig5_tool_effect.png` + `figures/fig6_rubric_items.png`（逐条得分率）

**讲**：
Two separate increments. Adding retrieval improves viability — the model stops inventing plants. Adding the negative filter fixes safety. Neither fix substitutes for the other.
Here is a real failure from the zero-shot baseline: a cat household, and the model proposed a true lily because it is a beautiful, sun-loving balcony flower. The proposed pipeline cannot produce this output; the species is not in the pool the model receives.

The second finding is about **design quality**, which is a different axis from safety. A design can be perfectly safe and still be useless — six safe plants with no spatial structure, no maintenance advice and no warning about the watering regime. So completeness is scored by a deterministic rubric of fifteen binary items — never by an LLM judging an answer. This is the per-item view: the baselines are not uniformly weaker, they lose points on exactly the items that require reasoning about the design as a whole — a zone the pet can actually reach, cautions that name a specific plant, a safety note that names the animal.

One caveat I want to state myself: our guarantee applies to species **in the database**. We measure that separately — the out-of-database rate, which counts recommended species that do not exist in our catalogue at all.

---

## 第 9 页 · 局限与展望（45 秒）

**屏幕**：左右两栏
> Limitations: 150 of 1000+ species · cats and dogs only · 25 scenarios · brief-parsing errors propagate
> Outlook: iterative tool use · per-species provenance in the answer · dense recall + deterministic filtering · more species

**讲**：
The limitations are real: the catalogue is a fraction of the ASPCA list, we model cats and dogs only, and a mis-parsed brief still propagates into the candidate pool — the relaxation ladder guarantees safety, not optimality.
The takeaway I would defend is this: **the safety floor here comes from the architecture, not from the model.** Swap in a stronger LLM and the design gets prettier; the toxicity guarantee does not move.

---

## 第 10 页 · 结论 + 演示入口（20 秒）

**屏幕**
> Every checkable constraint belongs in code.
> 150-species ground truth · reproducible data pipeline · 25-scenario benchmark · live demo
> github.com/<你的用户名>/petsafe-greenery · https://<你的>.streamlit.app

**讲**：
To summarise: in safety-critical applications the useful question is not which model is cleverest, but which decisions are allowed to remain unverifiable. My demo is live at this address — let me show you the agent running.

---

# Q&A 预案（1–2 分钟）

| 问题 | 回答要点 |
|------|----------|
| 为什么不直接 RAG + 让 LLM 过滤？ | 负向过滤必须确定性、可审计、可复现，不能依赖模型"自觉"；而且 LLM 过滤会把安全判断从代码里拿掉。 |
| 数据库怎么保证正确？ | 全部来自 ASPCA，每行带 source_url，可逐条追溯；脚本自动采集 + 校验脚本；没有明确毒性陈述的物种直接丢弃。 |
| 你的方法会不会漏掉有毒植物？ | 只对库内物种有保证；库外物种被评估器记为 out-of-database 并计入不安全指标（这个指标是单独报告的）。 |
| 只有一个模型，泛化性如何？ | 安全性下界与模型无关（架构决定），但设计质量与模型有关——这是诚实的分工，我已在报告中声明。 |
| 25 个场景够吗？ | 覆盖了 12 种光照×水分组合和 4 种宠物配置；作业规模下的可行方案，样本量是明确写出的局限。 |
| 设计质量是 LLM 打分吗？ | 不是。15 条二值规则全部由确定性代码判定，规则表直接从代码导出到报告，评分器和论文表格不可能对不上。 |
| 三个方法的 prompt 一样吗？ | 一样。三个方法共用同一份输出契约与同一份 JSON schema，唯一的差别是有没有接地、有没有做负向过滤——所以比的是架构，不是 prompt。 |
| 约束抽取（LLM）出错怎么办？ | 目前用 ground truth 评估安全性并单独报告抽取准确率；改进方向是让 agent 主动多轮澄清。 |
| 你的指标是 LLM-as-judge 吗？ | 不是，全部是确定性 Python 代码对数据库做集合运算，可复现。 |
| 代码能跑吗？ | 仓库里有 README 和一键脚本；数据管线（3 个脚本）也是可复现的，报告里写了怎么重跑。 |

# 上台前 10 分钟检查清单

- [ ] 演示链接能打开（手机热点也要能开）；录屏备份已就绪
- [ ] API key 额度没被跑完（演示只调 1–2 次）
- [ ] PPT 字号 ≥ 20pt，图能看清（别在 PPT 里塞整张 5 联图，放大关键的一张）
- [ ] 第 7 页数字和 `results/summary.csv` 一致（老师可能对着报告问）
- [ ] 报告 PDF 已提交 Canvas（Turnitin 绿/黄确认过）
- [ ] 代码 zip 已提交，里面没有 API key
- [ ] 提前 10 分钟到教室，投影仪试一遍
