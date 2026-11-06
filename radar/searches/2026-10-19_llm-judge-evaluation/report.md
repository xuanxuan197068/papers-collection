# 本地论文库中的 LLM 实验裁判：原文核对记录

核对日期：2026-10-19（Asia/Shanghai）。

检索范围：`src/assets/data/meta_json/` 的 117 个会议／期刊年份文件，共 16,338 条记录。检索本地题名与摘要后，对选定论文访问原文核对；没有遍历全部论文全文。先检索 LLM-as-a-judge、LLM/GPT 与 judge/score/evaluation 等组合，再扩展安全、越狱与代码评估相关题名。摘要没有提到裁判并不表示论文未使用裁判，以下是已核实实例清单，不是穷尽统计。

确认 12 篇：8 篇将 LLM 用于实验结果评价，4 篇研究评估方法本身。另列相关测量研究 1 篇，以及容易混淆的检索命中。未修改原始论文数据。论文 ID 是核对时的本地值，长期检索应优先使用题名／DOI。

USENIX 条目核对会议官网正式 PDF；软件工程条目核对作者在 arXiv 提供的全文，会议归属按本地库记录。作者版本的标题、章节或实验细节可能与正式出版版不同，正式引用时应再核对出版版本。下文 Code-DiTing 的作者版标题为 *A Reasoning-Based Metric for Functional Alignment in Code Evaluation*。

## A. 直接用于实验结果评价的 8 篇

### A1. Source Code Summarization in the Era of Large Language Models

- 本地：ICSE 2025，ID 9794，`ICSE - 2025.json`。
- 原文位置：实验 RQ1 的评估方法比较；后续 RQ 沿用选定的 GPT-4 评分方法。
- 裁判与输出：GPT-4 等模型按 1–5 分评价代码摘要质量；提供源代码、参考摘要及候选摘要。
- 校验：15 名志愿者评分，计算自动评分与人工评分的 Spearman 相关性。参数描述需结合两处阅读：§IV-A 评价段记默认 temperature=1；§V 明确 RQ2–RQ5 使用 GPT-4 裁判时设 temperature=0，以降低评分波动。原文表述不完全统一，不能只引用前一处。详见 `stability-review.md`。
- [作者全文](https://arxiv.org/html/2407.07959) · [本地出版入口](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=11029737)

### A2. An Exploratory Study of ML Sketches and Visual Code Assistants

- 本地：ICSE 2025，ID 9776，`ICSE - 2025.json`。
- 原文位置：§IV-E.3 LLM-as-a-Judge；§V 展示实验结果。
- 裁判与输出：GPT-4 系列模型按子任务检查生成的 Jupyter Notebook，汇总 Outline Accuracy 与 Instantiation Accuracy。§IV-E.3 写 GPT-4，后续模型比较段写 GPT-4o 兼任裁判，原文型号描述不完全统一。
- 校验：对子样本进行人工复核。裁判的 outline 判断准确率为 92.6%（63/68），实例化细节判断准确率为 78.3%（36/46）。这些数字衡量裁判，不是代码生成工具的效果。
- [作者全文](https://arxiv.org/html/2412.13386) · [会议官网](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/116/An-Exploratory-Study-of-ML-Sketches-and-Visual-Code-Assistants)

### A3. SoK: Data Reconstruction Attacks Against Machine Learning Models: Definition, Metrics, and Benchmark

- 本地：USENIX Sec 2025，ID 4408，`USENIX Sec - 2025.json`。
- 原文位置：§6.1，Table 4；属于后续实验分析，不局限于标题为 Evaluation 的 §5。
- 裁判与输出：GPT-4o 从六个候选重建图像中选择最接近目标图像的一张。每组重复五次，汇总多数票、全票及被选择频率；并用 InternVL 2.5、Claude 3.7 对照。
- 边界：这是一组候选间的视觉选择，不是直接给单张图像打绝对分；重复或换模型也不能直接等同于人工一致性验证。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-wen.pdf)

### A4. Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack

- 本地：USENIX Sec 2025，ID 4245，`USENIX Sec - 2025.json`。
- 原文位置：§4.2.1 Self-Evaluation；§5.1.3 Evaluation Models；§5.1.6 Evaluations Metrics。
- 裁判与输出：GPT-4 裁判返回是否成功、目标完成百分比和解释；汇总 ASR 与 judge score。
- 校验：Secondary Judge 检查主裁判理由，另用内容审核 API，并人工复核表现最好的提示与问题。人工复核范围不代表覆盖全部输出。裁判反馈同时也参与攻击过程。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-russinovich.pdf)

### A5. PAPILLON: Efficient and Stealthy Fuzz Testing-Powered Jailbreaks for LLMs

- 本地：USENIX Sec 2025，ID 4244，`USENIX Sec - 2025.json`。
- 原文位置：§4.3 Two-level Judge Module；§5.1 Experimental Setup。
- 搜索期：RoBERTa 先筛有害内容，GPT-3.5 Turbo 再检查内容与目标的关系，以 1–10 分评分，默认判定阈值为 8。
- 最终实验：论文明确另外使用 GPT-4 评价输出与有害问题的相关性，报告 ASR、Average Queries。应区分搜索期反馈与最终评估；不能把阈值 8 当作通用标准。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-gong-xueluan.pdf)

### A6. SelfDefend: LLMs Can Defend Themselves against Jailbreaking in a Practical Manner

- 本地：USENIX Sec 2025，ID 4246，`USENIX Sec - 2025.json`。
- 原文位置：§5.2 Datasets and Attack Setup，Metrics 段。
- 裁判与输出：MultiJail 多语言实验采用 GPT-4 判定回答是否达到越狱目标，计算 unsafe rate。
- 边界：其余多项攻击采用拒答关键词规则计算 ASR。不能把论文所有实验的 ASR 都解释为 GPT-4 裁判结果；用于防御的 LLM 与实验裁判也应分开记录。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-wang-xunguang.pdf)

### A7. Refusal Is Not an Option: Unlearning Safety Alignment of Large Language Models

- 本地：USENIX Sec 2025，ID 4136，`USENIX Sec - 2025.json`。
- 原文位置：§5.1.3 Evaluation Datasets and Metrics；§5.5 讨论异常输出。
- 裁判与输出：采用 LLaMA-Guard-8B 判断 safe/unsafe，再以 unsafe 比例计算 Harmfulness Score；参考文献指向 Llama-Guard-3-8B。
- 边界：这是专门训练的 LLM 安全裁判，不是通用 GPT 自由评分。论文识别到重复、破碎回答可能被判为 unsafe，另行分析并在比较中排除相关情形。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-song-minkyoo.pdf)

### A8. TwinBreak: Jailbreaking LLM Security Alignments based on Twin Prompts

- 本地：USENIX Sec 2025，ID 4241，`USENIX Sec - 2025.json`。
- 原文位置：§4 Evaluation，Evaluation Metrics 段；App. 8.3。
- 裁判与输出：对 AdvBench、HarmBench、JailbreakBench 使用 LlamaGuard3-8B 判断 safe/unsafe，再统计 ASR；对 StrongREJECT，采用该 benchmark 自带的微调 Gemma-2B 裁判，输出 0–1 分后取均值。
- 边界：这是明确引用现成 benchmark 裁判的例子。同一篇论文在不同数据集上也可能采用不同裁判，ASR 与连续分数不能混为同一指标。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-krauss.pdf)

## B. 研究裁判／评估方法本身的 4 篇

### B1. Can LLMs Replace Human Evaluators? An Empirical Study of LLM-as-a-Judge in Software Engineering

- 本地：ISSTA 2025，ID 11535，`ISSTA - 2025.json`。
- 原文位置：§4.1.3 人工评分、§4.2.4 输出式裁判、§4.3 Meta-Evaluation、§5 结果。
- 方法：比较代码翻译、生成、摘要任务中的自动裁判与人工评分；输出式方法通常使用 GPT-4o，包括 G-Eval、BatchEval、Vanilla。为不同任务制定 1–5 分规则，也研究成对比较。
- 用途：适合参考评分量表及裁判可靠性的验证；不能把某任务的人类对齐结果直接视作所有任务通用。
- [作者全文](https://arxiv.org/html/2502.06193) · [出版入口](https://doi.org/10.1145/3728963)

### B2. SE-Jury: An LLM-as-Ensemble-Judge Metric for Narrowing the Gap with Human Evaluation in SE

- 本地：ASE 2025，ID 8084，`ASE - 2025.json`。
- 原文位置：§III-A–C 裁判设计；§IV-C/D 评估和实现；§V-A/B 结果。
- 方法：以 GPT-4o-mini 为主要底座，组合不同提示策略；从 20 个人工标注样本选择策略组合，并将这些样本排除出正式测试。另以 DeepSeek-Chat 检验底座影响。
- 校验：与人工分数比较 Kendall/Spearman 相关性及 Cohen's κ。这里的 ensemble 主要是多种策略，不应自动理解为多个不同模型；摘要任务仍有明显人类一致性差距。
- [作者全文](https://arxiv.org/html/2505.20854)

### B3. Code-DiTing: Automatic Evaluation of Code Generation without References or Test Cases

- 本地：ASE 2025，ID 7891，`ASE - 2025.json`。
- 原文位置：作者版 §IV Methods、§V Experiments and Analysis。
- 方法：以 DeepSeek-R1 蒸馏模型为基础训练 1.5B/7B 代码裁判，根据题目与代码判断功能正确性，并产生理由；推理时七次多数投票。
- 校验：以执行测试得到的标签检验裁判，报告 Acc、F1、MCC。裁判使用时无需测试，不等于构建和验证裁判时也无需测试。
- [作者全文（标题不同）](https://arxiv.org/html/2505.19502) · [作者代码](https://github.com/Code-DiTing)

### B4. S-Eval: Towards Automated and Comprehensive Safety Evaluation for Large Language Models

- 本地：ISSTA 2025，ID 11543，`ISSTA - 2025.json`。
- 原文位置：§3.4 Automatic Safety Evaluation；§4.1.2 指标；§4.2 裁判验证。
- 方法：微调 Qwen-14B-Chat 为安全评估模型 Mc，提供风险标签、分数及解释，再计算 Safety Score 和 ASR。
- 校验：使用人工标注的中文、英文问答各 1,000 条测试裁判，比较规则、GPT-4-Turbo 与 LLaMA-Guard-2，报告 balanced accuracy、Precision、Recall。
- [作者全文](https://arxiv.org/html/2405.14191) · [出版入口](https://doi.org/10.1145/3728971)

## C. 相关的大模型打分测量研究

### GPTracker: A Large-Scale Measurement of Misused GPTs

本地 IEEE S&P 2025，ID 366，`IEEE S&P - 2025.json`。§4.2 与附录 Figure 15a 用 gpt-4o-mini-2024-07-18 根据 GPT 元数据评估各禁用场景风险，输出 0–1 分；每次重复三遍取平均，再结合人工复核。这是测量研究的数据筛查／风险评分，不宜等同于对生成方法的实验结果评分。[作者全文](https://xinyueshen.me/static/papers/SP25-GPTracker.pdf) · [作者代码](https://github.com/TrustAIRLab/GPTracker)

## D. 容易误收的实例

- **LLM-Fuzzer: Scaling Assessment of Large Language Model Jailbreaks，USENIX Sec 2024**：§3.4/§4.1 的主 oracle 是微调 RoBERTa-large。附录比较 GPT-4 等分类方法，不宜据此称其主实验使用 GPT-4 裁判。[官网原文](https://www.usenix.org/system/files/usenixsecurity24-yu-jiahao.pdf)
- **Optimization-based Prompt Injection Attack to LLM-as-a-Judge，ACM CCS 2024**：本地题名与摘要命中，但裁判是攻击对象。此项未进行本轮全文核对，不能据此纳入“裁判被用于最终实验评分”的确认清单。[本地出版入口](https://doi.org/10.1145/3658644.3690291)

## 针对实验设计的阅读建议

以下为根据上述实例整理的建议：

1. 需要把开放式输出转成质量分：优先读 A1 与 B1，关注每档分数的定义和人工相关性验证。
2. 需要检查复杂任务是否完成：优先读 A2，关注任务清单与裁判判断准确率；其两种细粒度判断的可靠性不同。
3. 需要评价攻击／防御效果：优先读 A4–A8，明确最终输出是绝对分、二分类还是汇总比例。
4. 需要控制成本或提高稳定性：参考 A5 的分级判定、B2 的策略组合、B3 的专用裁判和投票。但多次投票并不自动消除系统偏差。
5. 论文中应分别报告：裁判模型及版本、输入、rubric、分数范围和阈值、重复及汇总规则、人工／可执行真值的校验。搜索或优化反馈与最终评估尽可能分开说明。

这些实例说明顶会论文确实采用 LLM judge，但“前人用了”不等于某个裁判对新任务已被验证有效。最值得借鉴的是裁判的验证方案。
