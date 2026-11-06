# 八篇论文的 LLM 评分流程与稳定性核对

核对日期：2026-10-19（Asia/Shanghai）。本记录接续 `report.md`，核对正文、相关附录及评分提示；没有运行裁判或复现实验。USENIX 采用官网正式 PDF；两篇 ICSE 采用作者在 arXiv 的全文。下文“未明确报告”仅针对所核对版本的论文文字，不断言作者实现中一定没有该措施。

## 阅读结论

这些论文没有共同采用一套完整的裁判稳定性方案。应区分三类证据：同一输入重测的波动、改变裁判或提示后结论的变化、与人工或任务真值的一致性。后两类不能替代第一类。重复攻击或生成新回答，也不能直接测量固定回答上的裁判波动。

## 1. Source Code Summarization in the Era of Large Language Models

- 定位：§IV-A、Fig. 2、§V；作者 PDF 第 6、7、11 页。
- 输入源代码及多份候选摘要，按准确、自然简洁、便于理解等标准给每份摘要 1–5 分，要求固定输出格式。
- 控制：§V 明确 RQ2–RQ5 的 GPT-4 裁判 temperature=0。§IV-A 另记默认温度 1，存在报告口径不完全统一的问题。
- 有效性：15 名志愿者评分，与自动分数进行 Spearman 相关分析。
- 缺口：未明确报告同一摘要重复评分的方差或分数一致率。人工相关性衡量的是对齐程度。
- [作者全文](https://arxiv.org/html/2407.07959)

## 2. An Exploratory Study of ML Sketches and Visual Code Assistants

- 定位：§IV-E.3、Fig. 2，及后续模型比较段；作者 PDF 第 5–6 页。
- 输入 Notebook、任务说明、评分检查项。裁判逐项答 True/False，再计算 Outline/Instantiation Accuracy，而非直接给一个笼统质量分。
- 约束与校验：用正确 Notebook 测试裁判，再手动删去对应代码，检查它是否发现缺失；用这些结果修订问题和提示。另有人工子样本验证，裁判判断准确率为 92.6%（outline）和 78.3%（instantiation）。隐藏生成模型名称以缓解来源偏差。
- 缺口：未明确报告裁判温度及同一输入重复投票。§IV-E.3 称 GPT-4，后文称 GPT-4o 兼任裁判，型号描述不统一。校验准确性不等于证明重测稳定性。
- [作者全文](https://arxiv.org/html/2412.13386)

## 3. SoK: Data Reconstruction Attacks Against Machine Learning Models: Definition, Metrics, and Benchmark

- 定位：§6.1、Table 4；官网 PDF 第 12 页（正文 p.5611）。
- 输入一张目标图和六张候选重建图；GPT-4o 选择最相似候选，只返回索引。
- 直接重测：同一查询重复五次，分别统计多数票、全票、选择频率；另以 InternVL 2.5、Claude 3.7 对照总体趋势。
- 边界：论文报告保留了投票分歧；未明确交代该步骤温度、候选位置随机化及平票处理。跨模型趋势相符也不能消除共享偏差。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-wen.pdf)

## 4. Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack

- 定位：§4.2.1、§4.3、§5.1.3–6；官网 PDF 第 8–10 页。
- 输入任务目标及回答，GPT-4 输出成功标记、0–100 完成度和理由。Secondary Judge 检查理由并可修正受安全约束影响的判定；另有 Refusal Judge。
- 随机性设置：论文统一 temperature=0.5，整套 Crescendomation 独立运行十次。后者混合了攻击生成、目标回答和裁判变化，不能解释为对固定回答判十次再投票。
- 校验：内容审核 API 提供补充证据，并人工复核表现最好的提示／问题；第二裁判本身仍可能误判。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-russinovich.pdf)

## 5. PAPILLON: Efficient and Stealthy Fuzz Testing-Powered Jailbreaks for LLMs

- 定位：§4.3、评分提示框、§5.1、§7、Table 8；官网 PDF 第 10–11、14–15 页。
- 搜索时先以 RoBERTa 筛有害回答，再让 GPT-3.5 Turbo 根据目标与回答打 1–10 分；提示定义两端含义，限定输出格式，默认以 8 为阈值。最终实验另外用 GPT-4 评价相关性。
- 校验：30 名志愿者检查不同分数区间的成功判定，以此支持阈值 8；Table 8 的 8 分及以上样本与人工判定一致。
- 缺口：未明确报告评分温度或固定回答上的重复评分。两级筛选和阈值校验主要处理判据有效性及成本，不是重测方差验证；表中一致性只适用于所检样本。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-gong-xueluan.pdf)

## 6. SelfDefend: LLMs Can Defend Themselves against Jailbreaking in a Practical Manner

- 定位：§5.1–5.2；官网 PDF 第 7–8 页。
- MultiJail 中让 GPT-4 判断目标回答是否满足越狱目标，再计算 unsafe rate；其他多项攻击主要使用拒答关键词规则。
- 参数边界：§5.1 给目标模型和防御模型设置 temperature=0、n=1 等；§5.2 没有单独给外部 GPT-4 裁判列出同等参数。不能把前一设置直接当作裁判配置。
- 缺口：未明确报告对同一回答重复评分、投票或裁判重测一致率。采用已有协议不等于完成稳定性验证。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-wang-xunguang.pdf)

## 7. Refusal Is Not an Option: Unlearning Safety Alignment of Large Language Models

- 定位：§5.1.3、§5.5、App. C.1、Table 8；官网 PDF 第 8、12、20 页。
- 使用 Llama-Guard-3-8B 判断 safe/unsafe，unsafe 回答比例构成 Harmfulness Score。
- 做法：采用安全专用模型，将输出限制为分类；人工检查异常的 unsafe 回答，识别重复、破碎内容造成的误判，并对受影响的比较作标注或排除。
- 缺口：没有单独报告裁判解码参数、同一回答多次判定或评分方差。人工发现的异常说明还需检查语义误判，不能只关注数值是否稳定。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-song-minkyoo.pdf)

## 8. TwinBreak: Jailbreaking LLM Security Alignments based on Twin Prompts

- 定位：§4 Evaluation Metrics、App. 8.3、Fig. 10；官网 PDF 第 8、20–21 页。
- 部分测试集采用 LlamaGuard3-8B 的默认模板，按 safe/unsafe 计算 ASR；StrongREJECT 使用 benchmark 的微调 Gemma-2B 裁判，给出 0–1 分，再对整个数据集求平均。
- 做法：复用固定模型和既有评测协议；论文承认 LlamaGuard 的误报、漏报及对拒答关键词的偏重。
- 缺口：对整个数据集求均值不是对同一回答重复评分。未单独报告裁判重测方差或投票机制。
- [官网全文](https://www.usenix.org/system/files/usenixsecurity25-krauss.pdf)

## 对实验设计的建议（以下为本次分析建议，不是八篇共同遵循的标准）

1. 将“裁判是否稳定”和“裁判是否正确”分开验证；前者固定待评输出，后者用人工或可执行真值对照。
2. 固定模型版本、rubric、提示、解码设置和输出解析规则；记录无法解析或拒绝评价的情况。
3. 对固定校验集重复判定，例如五次；分类报告一致率／翻转情况，连续分数报告样本内标准差或范围，随后检查方法排序是否变化。不要只报告整个测试集的均值。
4. 比较候选时改变候选顺序；用少量真实样本制定分数锚点，对高分歧样本人工复核。校准样本应与正式测试隔离。
5. 降低温度只处理采样控制，无法证明评分有效；重复投票也可能保留系统偏差。对可执行任务，同时保留测试通过、真实触发等直接证据。
