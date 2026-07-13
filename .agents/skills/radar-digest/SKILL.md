---
name: radar-digest
description: 论文雷达语义层——读库出方法索引+方向总结+方法卡。当用户说"USENIX 最新情况/最新技术"、"总结最新方法"、"XX 方向有什么新东西"、"给 XX 建索引"、"跑一次雷达"（Stage 1），或"细读第 N 篇"、"给 XX 出方法卡"、"标记已读"（Stage 2）时使用。读 src/assets/data/meta_json，产出写 radar/，跨 run 积累。
---

# radar-digest：方法索引 + 两阶段语义雷达

目标：跨领域找可迁移方法。为每个 venue-year 建**逐篇方法索引**（method/problem/
scenario/evidence/lens），在其上做方向总结与方法卡。先读 `radar/config.yml`
（interest lens、默认范围、打分维度）和 `radar/state/read_status.json`（已读状态）。

数据源 = `src/assets/data/meta_json/<Publication> - <Year>.json`（每篇含 title/abstract/paper）。
Publication 名对照 data.yml 的 `name`（如 `USENIX Sec`、`IEEE S&P`、`ACM CCS`、`NDSS`）。

---

## 进入 skill 先做：勾选同步

扫描 `radar/maps/*.md` 里勾选候选表的 `- [x]` 行（用户可能用编辑器打了勾），
把对应论文写入 `read_status.json`（state=picked，键=compact title）。这样用户
"编辑器打勾"和"会话里直接说勾某篇"两条路都能进 Stage 2。

## 定范围

- 用户点名 venue/年份优先。
- "最新一年" = 按会议届次年份算（不是日历年）。取库里该 venue 的最新届。
- **分轮次/不完整届**（如 USENIX 2026 只有 cycle1 的 165 篇）要标注完整度，
  默认分析最新**完整**届并附带不完整届的增量说明，除非用户指名看最新届。

---

## Stage 1：方法索引 + 方向总结

触发："XX 最新情况/最新技术"、"总结最新方法"、"建索引"、"跑一次雷达"。

### 1. 检查 index 覆盖率
目标 = `radar/index/<Publication> - <Year>.json`（JSON 数组，每行见下格式）。
比对 index 的 key 数 vs meta_json 篇数：
- **已全覆盖** → 跳到步骤 3 直接读 index。
- **缺失/未建** → 先建（步骤 2）。若用户只是随口问且缺口很大（几百篇），
  先报量级+预计成本（subagent 抽取，haiku 级很便宜），确认后再建。

index 行格式：
```json
{"key":"compact标题","id":4401,"title":"原标题","paper":"链接",
 "method":"用了什么新算法/机制/模块、新在哪(中文一句)",
 "problem":"解决了什么难题","scenario":"用在什么对象/环境",
 "evidence":"real-world|benchmark|user study|simulation|theory|unknown",
 "lens":["蜜罐/网络欺骗","..."],"date":"YYYY-MM-DD"}
```

### 2. 构建 index（subagent map-reduce）
1. 分片：`uv run tools/radar_shard.py --pub "<Publication>" --year <Y> [--size 40]`
   → 写 `radar/_shards/<Publication> - <Year>/shard_NN.json`（已在 index 的论文自动跳过=增量）。
2. 并行派 subagent，**每批 ≤5 个**（`Agent` 工具，`subagent_type: general-purpose`，
   `model: haiku`——机械抽取用便宜模型）。每个 subagent 的 prompt 固定为：
   - 只读给定 shard 文件、只用 title+abstract（不许联网、不许读别的文件）；
   - 对**每一篇**（不许跳过）产出上面的 index 行格式；
   - **key/id/title/paper 逐字复制**（不得重算 key，否则合并时对不上）；
   - method/problem/scenario 用中文短句、贴摘要不空话；evidence 按验证方式选枚举
     （真实部署=real-world，基准/数据集=benchmark，真人参与=user study，仿真=simulation，
     纯证明=theory，摘要为`#`或太薄=从标题尽力推断并置 unknown）；
   - lens 只在确实相关时标（大多数为 `[]`，从严）；
   - **只把 JSON 数组写进 out 文件**（`out_NN.json`，同目录），不要 markdown 包裹。
3. 合并：`uv run tools/radar_index_merge.py --pub "<Publication>" --year <Y>`
   —— 校验必填字段、按 key 去重并入 index、**剔除 key 不在 meta 的漂移行**、报覆盖率。
4. **质量闸**：
   - 某片 out 行数 < shard 行数（subagent 漏篇）→ 用 `model: sonnet` 重跑该片。
   - 合并后覆盖率 < 100%（key 漂移导致缺口）→ 用不同 `--out` 目录重跑 radar_shard
     （只会挑出未索引的那几篇）→ 派一个 sonnet subagent 补 → `radar_index_merge --in <该目录>`。
   - 随机抽 5 条对照摘要人工核（method/problem/scenario 是否失真）。
5. 建完清理 `radar/_shards/`（临时，已 gitignore）。

### 3. 读 index 出方向总结（两段式）
写 `radar/maps/<YYYY-MM>_<scope>.md` 并在会话呈现。**两段必须分开**：

- **A 段（中立，完全不提用户方向）**：
  - 方向侧重：把 index 按机制聚成簇，簇×规模排序，指出今年重心在哪。
  - 技术倾向：统计方法族频次（如 LLM 驱动 / 形式化验证 / RL / fuzz 变体 / 认证鲁棒 …），
    说清"今年偏好用什么技术手段"。
  - 每个主要方向选 2-3 篇代表，逐篇给"方法 → 解决的问题 → 场景 → 证据"（直接取 index 行）。
- **B 段（结合方向，引入 lens）**：lens 命中的簇与论文、跨域迁移线索、与用户
  研究方向（config.yml interest_lens）的接口。
- **勾选候选表**（checkbox 语法，供编辑器打勾或会话直说）：
  ```
  - [ ] 4401 | Cloak, Honey, Trap | N=4 R=5 T=5 | 用LLM架构弱点造蜜标反制攻击agent
  ```
  已在 read_status 里 picked/carded 的标注出来避免重复推荐。

用户还能在前端"方法索引"页（`/paper/method-index`）自行浏览该 venue-year 全部 index 行
（带搜索和 lens 筛选）。

---

## Stage 2：方法卡（深度，只对勾选项）

触发："细读 X"、"给 X 出方法卡"。

1. 输入 = 该论文的 index 行 + meta_json 摘要；需要更多细节时抓论文页/开放 PDF
   （复用 `analyzers/abstract_enricher.py` 的 `pdf_lookup`，或直接 WebFetch）。
2. 按 `radar/cards/_TEMPLATE.md` 写卡到 `radar/cards/<slug>.md`。核心是"机制（领域无关
   描述）"和"迁移假设"两节。相关卡用 `[[slug]]` 互链。
3. 更新 read_status：state=carded，记 card 路径。

## read_status.json 约定
键 = compact title（字母数字小写，同 main.py compact()）：
```json
{"<compacttitle>": {"title":"原标题","venue":"USENIX Sec - 2025",
  "state":"picked|carded|read|skipped","card":"cards/xxx.md","date":"YYYY-MM-DD"}}
```

## 原则
- index 对**全量**建、方向总结 A 段**中立**、方法卡只对**勾选项**——省贵环节。
- interest lens 是锚不是过滤器：视野外的强机制照样进 index 和 A 段（跨域迁移是本意）。
- 产出只进 `radar/`，绝不改 `src/assets/data/`。
- 同一 scope 重跑：index 增量补新增论文；map 按月份另存不覆盖旧的。
