# 本地论文检索：威胁情报、情报收集与威胁信息获取

检索日期：2026-10-28（Asia/Shanghai）。

范围：本地 `src/assets/data/meta_json/` 的 117 个文件、16,338 条记录（16,327 个去重标题），覆盖 2001–2026 年、11 个会议/期刊。
检索 6 组标题与摘要关键词得到 221 篇候选。经标题筛选和重点候选摘要核对，整理 38 篇重点相关论文及 7 篇方法或场景延伸材料。

依据为本地标题和摘要，并参考已有方法索引与阅读状态；没有联网补充或核对全文。年份、题名和论文链接均来自本地元数据。相关性分组是本次人工语义判断，不代表论文质量排名或所有相关论文的完整清单。库内有 183 条记录缺少有效摘要；关键词召回也可能漏掉未使用这些表达的论文。

## 优先阅读路线

- **主动获取新的威胁信息**：S01（自动聊天）→ S06（诱饵账号）→ H04（响应式网络望远镜）→ H02（协同蜜罐）。
- **发现和利用新的情报源**：S02（地下市场鉴定评论）→ S03（Twitter 安全事件）→ S04 / S05（Telegram）。
- **从报告中提取可用知识**：E01（IOC）→ E02（TTP 提取综述）→ E04（Sigma 规则）；E05 / E06 衔接到日志分析。
- **验证收集是否有价值**：Q02（评估指标）→ Q05（公开 STIX 数据质量）→ Q01（传播链测量）→ Q06（IOC 发布时效）；地下市场采集另读 Q10。

IOC 指失陷指标，如恶意 IP、域名或文件哈希；TTP 指攻击者的战术、技术与过程。

## 情报源发现与信息获取

| 编号 | 论文与出处 | 信息来源 | 方法及相关性 |
|---|---|---|---|
| S01 | [Into the Deep Web: Understanding E-commerce Fraud from Autonomous Chat with Cybercriminals](https://www.ndss-symposium.org/ndss-paper/into-the-deep-web-understanding-e-commerce-fraud-from-autonomous-chat-with-cybercriminals/)<br>NDSS 2020 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2020.json:425>) | 黑产人员的一对一即时通信 | Aubrey 将求职、索取资源等问答模式建模为有限状态机，自动与真实电商欺诈人员聊天，获取攻击工具、号码和供应链关系。<br>**相关性：**主动交互式情报获取；本次最直接匹配之一。 |
| S02 | [Understanding and Analyzing Appraisal Systems in the Underground Marketplaces](https://www.ndss-symposium.org/ndss-paper/understanding-and-analyzing-appraisal-systems-in-the-underground-marketplaces/)<br>NDSS 2024 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2024.json:615>) | 地下市场的商品试用与鉴定评论 | 发现鉴定评论是被低估的 CTI 来源，并构建覆盖 41 类情报的提取模型，从中获取工具、服务和技术细节。<br>**相关性：**发现新情报源，并比较不同内容类型的情报产出。 |
| S03 | [Tweezers: A Framework for Security Event Detection via Event Attribution-centric Tweet Embedding](https://www.ndss-symposium.org/ndss-paper/tweezers-a-framework-for-security-event-detection-via-event-attribution-centric-tweet-embedding/)<br>NDSS 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2025.json:665>) | Twitter 安全相关推文 | Tweezers 使用以安全事件属性为中心的推文嵌入发现安全事件，并支持事件趋势分析与高信息量账号识别。<br>**相关性：**持续收集安全事件情报，同时发现后续值得跟踪的消息源。 |
| S04 | [DarkGram: A Large-Scale Analysis of Cybercriminal Activity Channels on Telegram](https://www.usenix.org/conference/usenixsecurity25/presentation/roy)<br>USENIX Sec 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2025.json:2495>) | Telegram 网络犯罪活动频道 | DarkGram 用 BERT 识别恶意帖子，测量凭据、恶意软件和黑客资源等内容，并跟踪新出现的频道。<br>**相关性：**黑产频道发现、内容分类及持续监测。 |
| S05 | [Stayin' Alive: How Global Stolen Data Markets Thrive on Telegram](https://www.usenix.org/conference/usenixsecurity26/presentation/marjanov)<br>USENIX Sec 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2026.json:365>) | Telegram 被盗数据交易频道及共享文件 | 通过一年期纵向数据集研究被盗数据市场，分析语言分布、数据类型、频道迁移及 gateway channels 的作用。<br>**相关性：**跨语言情报采集、频道扩展与来源存续性；研究包含人工整理渠道。 |
| S06 | [TBTrackerX: Fantastic Trigger Bots and Where to Find Malicious Campaigns on X](https://www.ndss-symposium.org/ndss-paper/tbtrackerx-fantastic-trigger-bots-and-where-to-find-malicious-campaigns-on-x/)<br>NDSS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2026.json:2235>) | X 上受到关键词触发的恶意社交机器人 | TBTrackerX 通过 honeytrap 账号采集触发型机器人的回复，分析休眠、突发活动和协同行为。<br>**相关性：**用诱饵账号主动引出恶意活动，获取常规静态抓取不易观察的行为。 |
| S07 | [Clues in Tweets: Twitter-Guided Discovery and Analysis of SMS Spam](https://doi.org/10.1145/3548606.3559351)<br>ACM CCS 2022 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2022.json:1815>) | Twitter 用户举报帖中的短信截图 | SpamHunter 自动寻找垃圾短信举报帖，从附带截图中提取短信内容，持续积累多语言新样本并分析攻击活动。<br>**相关性：**把受害者公开举报转化为可持续更新的威胁数据源。 |
| S08 | [Reading Thieves' Cant: Automatically Identifying and Understanding Dark Jargons from Cybercrime Marketplaces](https://www.usenix.org/conference/usenixsecurity18/presentation/yuan-kan)<br>USENIX Sec 2018 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2018.json:655>) | 地下论坛与正常语料 | Cantreader 比较词语在正常和地下语料中的语义差异，发现暗语，并用投影学习寻找揭示含义的上位词。<br>**相关性：**解决情报采集中看不懂黑话、关键词规则覆盖不足的问题。 |
| S09 | [Breaking Free from Ivory Tower: Evaluating and Enhancing Real-world Chinese Underground Adversarial Jargon Detection](https://doi.ieeecomputersociety.org/10.1109/SP63933.2026.00233)<br>IEEE S&P 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/IEEE S&P - 2026.json:1915>) | 真实中文地下经济对抗性黑话 | 构建真实扰动黑话数据集，提出 JADE，结合扰动分类、数据增强、外部知识检索及模型适配来检测和恢复黑话。<br>**相关性：**适合中文黑产语义识别；提供真实规避条件下的情报内容理解方法。 |
| S10 | [How to Learn Klingon without a Dictionary: Detection and Measurement of Black Keywords Used by the Underground Economy](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=7958608)<br>IEEE S&P 2017 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/IEEE S&P - 2017.json:405>) | 搜索引擎结果、关联查询及黑产网页 | KDES 从搜索结果推断黑关键词，利用关联查询扩展词表，并提取相关页面中的邮箱、手机号和即时通信账号。<br>**相关性：**从种子关键词扩展情报线索及联系方式。 |
| S11 | [Vulnerability Disclosure in the Age of Social Media: Exploiting Twitter for Predicting Real-World Exploits](https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/sabottke)<br>USENIX Sec 2015 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2015.json:745>) | Twitter 漏洞披露与利用讨论 | 分析 Twitter 中的漏洞信息，并构建基于 Twitter 的利用检测器，支持判断漏洞是否会在现实环境中被利用。<br>**相关性：**获取早期漏洞利用信号与确定响应优先级。 |

## 蜜罐、遥测与主动测量

| 编号 | 论文与出处 | 信息来源 | 方法及相关性 |
|---|---|---|---|
| H01 | [HoneyPLC: A Next-Generation Honeypot for Industrial Control Systems](https://doi.org/10.1145/3372297.3423356)<br>ACM CCS 2020 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2020.json:175>) | 面向 PLC 的高交互蜜罐 | HoneyPLC 支持多种 PLC 型号和厂商，通过更逼真的服务模拟诱使攻击者交互并收集恶意软件与攻击样本。<br>**相关性：**面向工控的原始威胁数据采集。 |
| H02 | [Cyber-Physical Deception Through Coordinated IoT Honeypots](https://www.usenix.org/conference/usenixsecurity25/presentation/guan)<br>USENIX Sec 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2025.json:275>) | 具有物理与网络依赖的协同 IoT 蜜罐 | CPDS 将设备间依赖建模为 Prolog 规则，根据攻击者动作协调蜜罐，维持跨设备、跨层交互的一致性。<br>**相关性：**通过更可信的交互环境暴露攻击者方法与策略；本库已有方法卡。 |
| H03 | [HoneySat: A Network-based Satellite Honeypot Framework](https://www.ndss-symposium.org/ndss-paper/honeysat-a-network-based-satellite-honeypot-framework/)<br>NDSS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2026.json:1095>) | 仿真 CubeSat 的高交互卫星蜜罐 | HoneySat 为缺乏真实攻击数据的卫星场景构建交互式采集环境；摘要报告采集到 22 次真实对抗交互。<br>**相关性：**在稀缺威胁数据领域构建情报采集入口。 |
| H04 | [Spoki: Unveiling a New Wave of Scanners through a Reactive Network Telescope](https://www.usenix.org/conference/usenixsecurity22/presentation/hiesgen)<br>USENIX Sec 2022 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2022.json:245>) | 对互联网扫描流量作出响应的网络望远镜 | Spoki 响应扫描器的 TCP 握手，获取传统被动网络望远镜看不到的后续数据，研究两阶段扫描。<br>**相关性：**通过有限响应增加观测深度，获取扫描后的真实载荷。 |
| H05 | [To Catch a Ratter: Monitoring the Behavior of Amateur DarkComet RAT Operators in the Wild](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=7958609)<br>IEEE S&P 2017 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/IEEE S&P - 2017.json:415>) | 运行 DarkComet 样本的受控蜜罐环境 | 运行野外 RAT 样本并监测远程操作者的交互，重建人工操作序列，分析其意图和行为。<br>**相关性：**从恶意软件样本进一步获取真人攻击者的行为情报。 |
| H06 | [Phoneypot: Data-driven Understanding of Telephony Threats](https://www.ndss-symposium.org/ndss2015/ndss-2015-programme/phoneypot-data-driven-understanding-telephony-threats/)<br>NDSS 2015 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2015.json:615>) | 大规模电话号码蜜罐 | Phoneypot 利用接近四万个号码接收电话，分析自动拨号、语音钓鱼、呼叫模式及电话拒绝服务活动。<br>**相关性：**补充受害者投诉数据缺失的电话威胁信号。 |
| H07 | [ScannerGrouper: A Generalizable and Effective Scanning Organization Identification System Toward the Open World](https://doi.org/10.1145/3719027.3765053)<br>ACM CCS 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2025.json:3085>) | 蜜罐等监测系统捕获的服务探测流量 | ScannerGrouper 分析首个服务探测载荷，汇合多服务分类器，并使用开集模型和增量更新识别扫描组织。<br>**相关性：**将采集到的探测行为转化为组织线索；也契合本库开集识别方向。 |
| H08 | [Catch-22: Uncovering Compromised Hosts using SSH Public Keys](https://www.usenix.org/conference/usenixsecurity25/presentation/munteanu)<br>USENIX Sec 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2025.json:445>) | 已知恶意 SSH 公钥与互联网扫描 | Catch-22 利用 SSH 公钥认证的挑战行为检测服务器是否存在恶意密钥，从少量已知情报发现更多受控主机。<br>**相关性：**威胁情报扩展与验证；摘要也讨论蜜罐样本对攻击活动的代表性偏差。 |

## 情报提取、组织与应用

| 编号 | 论文与出处 | 信息来源 | 方法及相关性 |
|---|---|---|---|
| E01 | [Acing the IOC Game: Toward Automatic Discovery and Analysis of Open-Source Cyber Threat Intelligence](https://doi.org/10.1145/2976749.2978315)<br>ACM CCS 2016 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2016.json:605>) | 技术博客等非结构化公开文本 | iACE 分析候选 IOC、上下文词与语法关系，通过图挖掘生成同时携带指标及上下文的 OpenIOC 条目。<br>**相关性：**公开文本自动提取威胁情报的经典工作。 |
| E02 | [SoK: Automated TTP Extraction from CTI Reports – Are We There Yet?](https://www.usenix.org/conference/usenixsecurity25/presentation/buechel)<br>USENIX Sec 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2025.json:2385>) | 自然语言 CTI 报告与既有提取方法 | 系统化梳理并统一评测自动 TTP 提取，指出本体歧义、数据集不可比和真实场景性能等问题。<br>**相关性：**了解从 IOC 提取走向高层攻击行为提取的研究现状与评测缺口。 |
| E03 | [A Decade-long Landscape of Advanced Persistent Threats: Longitudinal Analysis and Global Trends](https://doi.org/10.1145/3719027.3765085)<br>ACM CCS 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2025.json:2145>) | 六个来源中的 APT 技术报告与威胁组织档案 | 结合规则检索和大语言模型搜索，分析 2014–2023 年的 1,509 份 APT 档案，整理组织、攻击方式和长期趋势。<br>**相关性：**从分散公开报告构建可分析的长期威胁知识。 |
| E04 | [From Texts to Rules: Generating Sigma Rules with Large Language Models from Cyber Threat Reports](https://www.usenix.org/conference/usenixsecurity26/presentation/cai)<br>USENIX Sec 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2026.json:1415>) | 含 shell 命令的网络威胁报告 | SIGMERGE 经由信息提取、攻击描述生成和语义中间层，把报告中的命令及 TTP 转化为 Sigma 检测规则。<br>**相关性：**验证获取到的文本情报能否转成实际检测能力；重点在情报应用。 |
| E05 | [KnowHow: Automatically Applying High-Level CTI Knowledge for Interpretable and Accurate Provenance Analysis](https://www.ndss-symposium.org/ndss-paper/knowhow-automatically-applying-high-level-cti-knowledge-for-interpretable-and-accurate-provenance-analysis/)<br>NDSS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2026.json:1265>) | 高层 CTI 知识与低层系统事件 | KnowHow 用 gIoC 表达主体、客体和动作，将系统事件标识提升到自然语言层，并结合攻击步骤的时序逻辑检测 APT。<br>**相关性：**连接报告语义与底层日志；重点在情报应用。 |
| E06 | [POIROT: Aligning Attack Behavior with Kernel Audit Records for Cyber Threat Hunting](https://doi.org/10.1145/3319535.3363217)<br>ACM CCS 2019 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2019.json:1075>) | CTI 中的关系描述与内核审计记录 | POIROT 将 CTI 关系构成的查询图与审计日志的溯源图进行非精确图匹配，寻找攻击活动并重建步骤。<br>**相关性：**让关系型情报参与威胁狩猎；重点在情报应用。 |
| E07 | [Threat Intelligence Computing](https://doi.org/10.1145/3243734.3243829)<br>ACM CCS 2018 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2018.json:1175>) | 安全观测、领域知识与图数据库 | 通过领域专用图语言与分布式图数据库，把威胁假设编码、证据挖掘和交互式数据检查统一为图计算。<br>**相关性：**提供威胁知识组织和交互式分析的计算框架。 |
| E08 | [NEXUS: Towards Accurate and Scalable Mapping between Vulnerabilities and Attack Techniques](https://www.ndss-symposium.org/ndss-paper/nexus-towards-accurate-and-scalable-mapping-between-vulnerabilities-and-attack-techniques/)<br>NDSS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2026.json:1545>) | CVE 描述与 MITRE ATT&CK 技术 | NEXUS 从非结构化漏洞描述提取攻击者行为，并建立 CVE 到 TTP 的映射，处理数据缺口与分布不均。<br>**相关性：**将漏洞信息补充成带攻击行为上下文的情报。 |
| E09 | [ThreatMAMBA: Achieving High-Robustness Cyber Threat Attribution During the Evolution of Attacks](https://doi.org/10.1109/TIFS.2026.3685967)<br>TIFS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/TIFS - 2026.json:2965>) | CTI 中的 IOC、TTP 及时间关系 | ThreatMAMBA 构建异构、时序知识图，结合状态空间选择与对比学习，在攻击演进过程中进行威胁归因。<br>**相关性：**情报融合与早期归因；重点在获取后的推理。 |

## 情报质量、共享与获取价值

| 编号 | 论文与出处 | 信息来源 | 方法及相关性 |
|---|---|---|---|
| Q01 | [Actively Understanding the Dynamics and Risks of the Threat Intelligence Ecosystem](https://www.ndss-symposium.org/ndss-paper/actively-understanding-the-dynamics-and-risks-of-the-threat-intelligence-ecosystem/)<br>NDSS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2026.json:105>) | 在情报生态中传播的带水印样本及网络 IOC | 通过主动测量追踪情报提交、提取、共享及处置链条，识别选择性共享、传播瓶颈和提取不足等问题。<br>**相关性：**研究获取渠道的实际行为、传播时延与信息流失。 |
| Q02 | [Reading the Tea leaves: A Comparative Analysis of Threat Intelligence](https://www.usenix.org/conference/usenixsecurity19/presentation/li)<br>USENIX Sec 2019 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2019.json:555>) | 公开及商业威胁情报源 | 定义表征情报 feed 的指标，对多个来源的覆盖与准确性进行系统比较，并以外部测量辅助评估。<br>**相关性：**搭建情报采集质量评估的基础指标。 |
| Q03 | [A different cup of TI? The added value of commercial threat intelligence](https://www.usenix.org/conference/usenixsecurity20/presentation/bouwman)<br>USENIX Sec 2020 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2020.json:245>) | 商业供应商、开放情报 feed 与使用者访谈 | 比较商业与开放情报的重叠、覆盖和时效，并用访谈解释用户如何判断商业情报的价值。<br>**相关性：**选择采购、聚合或自行采集渠道时的实证参考。 |
| Q04 | [Helping hands: Measuring the impact of a large threat intelligence sharing community](https://www.usenix.org/conference/usenixsecurity22/presentation/bouwman)<br>USENIX Sec 2022 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2022.json:645>) | COVID-19 Cyber Threat Coalition 共享社区 | 研究大规模志愿共享是否带来新增覆盖，以及基于 VirusTotal 的质量门槛如何影响情报纳入与主题偏移。<br>**相关性：**考察社区采集相对于既有来源的增量价值。 |
| Q05 | [Sharing cyber threat intelligence: Does it really help?](https://www.ndss-symposium.org/ndss-paper/sharing-cyber-threat-intelligence-does-it-really-help/)<br>NDSS 2024 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/NDSS - 2024.json:715>) | 十个公开来源中的 STIX 数据 | CTI-Lense 从数量、及时性、覆盖和质量分析 STIX 共享，检查数据类型偏斜、错误信息与检测规则缺失。<br>**相关性：**公开结构化情报的系统采集与质量评估。 |
| Q06 | [Can IOCs Impose Cost? The Effects of Publishing Threat Intelligence on Adversary Behavior](https://doi.org/10.1145/3719027.3765026)<br>ACM CCS 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2025.json:445>) | 商业 IOC feed 与真实网络流量元数据 | 对比 IOC 发布前后的活动，发现不少指标发布时其资源已被攻击者放弃，并分析公开情报与对手行为的关系。<br>**相关性：**判断采集到的 IOC 是否仍然新鲜、可行动。 |
| Q07 | [APT to Disagree: A Comparative Analysis of Attribution in Commercial TI](https://doi.org/10.1109/SP63933.2026.00215)<br>IEEE S&P 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/IEEE S&P - 2026.json:2535>) | 七家供应商的长期 IOC 与归因 feed | 归一化异构 feed 并统一威胁组织名称，比较厂商的组织覆盖以及组织、国家归因的一致性。<br>**相关性：**多源融合时处理命名差异、单源信息和归因冲突。 |
| Q08 | [High Stakes, Low Certainty: Evaluating the Efficacy of High-Level Indicators of Compromise in Ransomware Attribution](https://www.usenix.org/conference/usenixsecurity25/presentation/van-der-horst)<br>USENIX Sec 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2025.json:2485>) | 勒索软件事件报告与专家访谈 | 评估高层 IOC 对归因的有效性，揭示高层行为特征区分度不足、低层指标易变等问题。<br>**相关性：**避免把收集到的行为模式直接当作可靠的攻击者身份证据。 |
| Q09 | [Updatable Multi-Party Private Set Intersection for Real-Time Collaborative Threat Intelligence](https://doi.org/10.1109/TIFS.2026.3707440)<br>TIFS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/TIFS - 2026.json:4745>) | 多组织持续更新的威胁指标集合 | 提出可更新多方隐私集合求交协议，使新增及过期指标的处理成本与更新量相关，支持动态协作。<br>**相关性：**跨组织、保护隐私的共同威胁发现；主要贡献为共享协议。 |
| Q10 | [Measurement by Proxy: On the Accuracy of Online Marketplace Measurements](https://www.usenix.org/conference/usenixsecurity22/presentation/cuevas)<br>USENIX Sec 2022 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2022.json:1205>) | 地下市场公开抓取与查获的后台数据库 | 比较代理观测与实际交易数据，并模拟抓取频率、限流和一致性的影响，揭示覆盖不足及估计偏差。<br>**相关性：**直接帮助设计情报收集实验与报告漏采、覆盖偏差。 |

## 延伸阅读

| 编号 | 论文与出处 | 信息来源 | 方法及相关性 |
|---|---|---|---|
| X01 | [A Search Engine Backed by Internet-Wide Scanning](https://doi.org/10.1145/2810103.2813703)<br>ACM CCS 2015 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2015.json:435>) | 持续互联网扫描 | 介绍 Censys 的扫描、处理和查询架构，使协议 banner 和派生字段可检索。<br>**相关性：**获取资产及暴露面上下文的基础设施方法；范围比 CTI 更广。 |
| X02 | [Identifying the Scan and Attack Infrastructures Behind Amplification DDoS Attacks](https://doi.org/10.1145/2976749.2978293)<br>ACM CCS 2016 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2016.json:1125>) | 放大型 DDoS 的扫描与攻击流量 | 通过扫描指纹与 TTL 三边定位关联扫描器和实际攻击基础设施。<br>**相关性：**补充攻击基础设施发现、关联与定位方法。 |
| X03 | [Poster: Agentic Shell Honeypot Using Structured Logging](https://doi.org/10.1145/3719027.3760731)<br>ACM CCS 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2025.json:3455>) | 多轮 shell 蜜罐交互 | HoneyAgents 结合多代理分工、结构化日志和分层规划，提高 LLM shell 蜜罐的状态一致性与响应真实性。<br>**相关性：**为长期交互采集提供支撑；明确为 Poster，不能与完整论文的证据量等同。 |
| X04 | [Schrödinger’s RAT: Profiling the Stakeholders in the Remote Access Trojan Ecosystem](https://www.usenix.org/conference/usenixsecurity18/presentation/rezaeirad)<br>USENIX Sec 2018 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/USENIX Sec - 2018.json:665>) | VirusTotal、过期 RAT 控制域名与 sinkhole 流量 | 注册过期控制域名收集连接，分析 RAT 生态，并排除扫描器和沙箱等非真实感染流量。<br>**相关性：**采集新观测点及清理伪威胁观测的方法。 |
| X05 | [SoK: Digging into the Digital Underworld of Stolen Data Markets](https://doi.ieeecomputersociety.org/10.1109/SP61157.2025.00037)<br>IEEE S&P 2025 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/IEEE S&P - 2025.json:375>) | 被盗数据市场相关研究文献 | 回顾十五年被盗数据市场研究，讨论市场迁移、观测周期缩短、语言多样性和覆盖不足。<br>**相关性：**开展地下情报源研究前的综述性入口。 |
| X06 | [Securing Cyber-Physical Systems via Advanced Cyber Threat Intelligence Methods](https://doi.org/10.1145/3658644.3690865)<br>ACM CCS 2024 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/ACM CCS - 2024.json:4145>) | 工控、卫星与自动驾驶 CPS 场景 | 描述通过 PLC 威胁分类、卫星蜜罐和自动驾驶沙箱扩展 CPS 威胁情报的方法。<br>**相关性：**摘要自述为 dissertation research description，应作为研究方向材料阅读。 |
| X07 | [R3S: Attack-Mitigation Reasoning in Security Knowledge Graphs](https://doi.org/10.1109/TIFS.2026.3725546)<br>TIFS 2026 · [本地摘要](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/src/assets/data/meta_json/TIFS - 2026.json:4815>) | 漏洞、攻击技术和缓解措施构成的安全知识图 | R3S 构建分层对手知情缓解图，并动态协调语义、结构信号进行攻击与缓解推理。<br>**相关性：**适合情报获取之后的知识组织和防御决策，采集本身不是核心。 |

## 检索与排除说明

覆盖显式 CTI / IOC、地下情报源、主动采集、安全知识提取、基础设施发现、社交平台及 TTP 等六组表达；具体正则、命中位置、全部候选摘要和源文件 SHA-256 见同目录 retrieval.json。
排除仅泛泛提到 cyber threats / cybercrime、通用知识图攻击、普通网络流量分类等弱命中。智能合约中以诈骗为目的的 honeypot 未当作防御型采集蜜罐纳入。
E04–E09 中多篇重点在情报应用、关联或推理，Q09 重点在共享协议；均在相关性说明中作了区分。X03 是 Poster，X06 是 dissertation research description。
H02 已有方法卡：[Cyber-Physical Deception Through Coordinated IoT Honeypots](<C:/Users/14636/Desktop/学习/方向调研/papers-collection/radar/cards/coordinated-iot-honeypots.md>)。本次没有新增勾选、已读或方法卡状态。

检索材料保存在 radar/searches/，没有修改论文数据或已有方法索引。

复现关键词召回与报告生成：

```powershell
python radar/searches/2026-10-28_threat-intelligence/search_local.py
```

screening.json 保存本次人工选择及摘要依据下的中文说明；重跑只复现召回和组装，不会自动执行新的语义筛选。
