---
name: radar-digest
description: 论文雷达语义层——读库出方法索引、方向总结和方法卡。当用户说“USENIX 最新情况/最新技术”“总结最新方法”“XX 方向有什么新东西”“给 XX 建索引”“跑一次雷达”（Stage 1），或“细读第 N 篇”“给 XX 出方法卡”“标记已读”（Stage 2）时使用。读取 src/assets/data/meta_json，产出写入 radar/，跨 run 积累。
---

# radar-digest：方法索引 + 两阶段语义雷达

目标：跨领域寻找可迁移方法。为每个 venue-year 建逐篇方法索引
（method/technique/problem/scenario/evidence/lens），再据此生成方向总结和方法卡。
开始前读取 `radar/config.yml`（interest lens、默认范围、打分维度）和
`radar/state/read_status.json`（已读状态）。

数据源是 `src/assets/data/meta_json/<Publication> - <Year>.json`。Publication 名使用
`data.yml` 的 `name`，例如 `USENIX Sec`、`IEEE S&P`、`ACM CCS`、`NDSS`。

## 进入 Skill 后先同步勾选

扫描 `radar/maps/*.md` 中候选表的 `- [x]` 行，把对应论文写入
`radar/state/read_status.json`（`state=picked`，键为 compact title）。这样编辑器勾选和
会话内点名都能进入 Stage 2。

## 确定范围

- 用户点名 venue/年份时优先采用。
- “最新一年”按会议届次年份而非日历年计算，取库中该 venue 的最新届。
- 分轮次或不完整届必须标注完整度；默认分析最新完整届，并附不完整届增量说明，除非用户明确指定最新届。

## Stage 1：方法索引 + 方向总结

触发：“XX 最新情况/最新技术”“总结最新方法”“建索引”“跑一次雷达”。

### 1. 检查两类覆盖率

目标文件为 `radar/index/<Publication> - <Year>.json`，顶层是论文行数组。

- **行覆盖率**：index 的有效 key 数 / meta_json 论文数。
- **technique-v2 覆盖率**：technique 为合法 v2 数组的 index 行数 / index 行数。旧字符串不计入 v2 覆盖。
- 行缺失时使用 `full` 模式；行已齐但 technique 仍为旧字符串时使用 `technique` 模式。
- 已达到 100% 行覆盖且 100% v2 覆盖时，直接进入方向总结。

### 2. technique-v2 契约

权威定义见 `radar/schema/technique-v2.schema.json`。`technique` 是按逻辑或执行顺序排列的
**0-4 个原子对象**，每个对象必须且只能包含七个字段：

```json
"technique": [
  {
    "name": "可跨论文聚类的机制名称",
    "type": "analysis-method",
    "target": "被操作或分析的对象",
    "action": "一个原子动作",
    "effect": "该动作直接产生的作用",
    "grounding": "explicit",
    "limitation": null
  }
]
```

`type` 只能取以下枚举：

`algorithm`、`model`、`architecture`、`protocol`、`system-mechanism`、
`hardware-mechanism`、`data-construction`、`instrumentation`、`analysis-method`、
`testing-method`、`measurement-method`、`formal-method`、`user-study`、`other`。

抽取约束：

- 一个 atom 只表达一个动作；多阶段流程拆成多个 atom，最多保留四个核心步骤。
- `name` 使用机制名，不能只写论文名或系统名；`target/action/effect` 必须具体且非空。
- `name/target/action/effect/limitation` 使用简洁中文，保留必要的英文术语、算法名和缩写。
- `effect` 只描述机制的直接作用。实验或数据规模、参与者数量、性能数字、提升比例和宣传性结论不得进入 technique 的任何字段；评测方式仍放论文级 `evidence`。
- `grounding=explicit` 仅用于摘要直接支持完整 atom 的情况，此时 `limitation` 必须为 `null`。
- `grounding=partial` 用于摘要只支持较粗粒度机制的情况；字段仍须保持在摘要可支持的粒度，
  `limitation` 必须用非空字符串说明缺失或未验证的细节。`partial` 不授权推断。
- 摘要为 `#`、过薄或无法同时支持 name/target/action/effect 时写 `technique: []`，不得根据常识、标题或旧 technique 脑补。
- method 是论文级一句话“新在哪”；technique 是可复用的有序技术链，两者不重复堆砌。

完整 index 行仍保留 `key/id/title/paper/method/problem/scenario/evidence/lens/date` 等论文级字段。
`key/id/title/paper` 必须从 shard 逐字复制。

### 3. 构建或迁移 index

选择模式：

- `full`（默认）：为尚未索引的论文生成完整 index 行。
- `technique`：保留已有论文级语义，只把旧字符串 technique 迁移为 v2 数组；`--force` 会把
  已是合法 v2 的行也重新分片，适合受控重抽取。

分片命令：

```bash
uv run tools/radar_shard.py --pub "<Publication>" --year <Y> --mode full [--size 40] [--out DIR]
uv run tools/radar_shard.py --pub "<Publication>" --year <Y> --mode technique [--force] [--size 40] [--out DIR]
```

随后使用当前平台可用的子代理并行处理 shard；并发数服从当前平台可用槽位，不写死代理类型、模型或批次数。每个子代理必须：

- 只读指定 shard，只使用其中的 title+abstract，不联网、不读取其他论文文件。
- 对 shard 中每篇论文恰好输出一行，不跳过。
- `full` 模式输出完整 index 行；`technique` 模式每行必须且只能包含
  `key/id/title/paper/technique`。
- identity 字段逐字复制；technique 严格遵守 v2 契约和“不脑补”规则。
- 只把 JSON 数组写入同目录 `out_NN.json`，不加 Markdown 或解释文字。

先只检查，再正式合并：

```bash
uv run tools/radar_index_merge.py --pub "<Publication>" --year <Y> --mode full --check-only [--in DIR]
uv run tools/radar_index_merge.py --pub "<Publication>" --year <Y> --mode full [--in DIR]
uv run tools/radar_index_merge.py --pub "<Publication>" --year <Y> --mode technique --check-only [--in DIR]
uv run tools/radar_index_merge.py --pub "<Publication>" --year <Y> --mode technique [--in DIR]
```

### 4. 质量闸与 coverage 审计

正式写 index 前必须全部满足：

- 每个 out 的行数等于对应 shard 的 count；总行数覆盖 manifest 的 expected keys。
- key/id/title/paper 与 shard 精确一致率为 100%，无重复 key、额外行或漂移行。
- 行级必填字段和 technique-v2 schema 有效率为 100%；atom 数为 0-4、七字段精确、type 枚举合法、grounding/limitation 条件成立。
- `--check-only` 成功；任一非法行都应修复或重跑对应 shard，不允许部分合并后继续。
- 合并后行覆盖率必须为 100%；迁移 scope 的 v2 覆盖率必须为 100%，并明确报告 `[]`、`partial`、`other` 的数量。
- 所有 `type=other` 的 atom 必须逐项人工审计，并说明为何无法归入已有技术形态枚举，不能只做抽样检查。
- 对照摘要做分层人工抽检，覆盖不同 type、空数组和 partial；发现失真时修正抽取规则并重跑该 shard。

完成后清理 `radar/_shards/` 中本次临时目录。

### 5. 从 atom 生成方向总结

写入 `radar/maps/<YYYY-MM>_<scope>.md` 并在会话中呈现；A/B 两段必须分开。

- **A 段（中立）**：按 `type + name + target/action` 的机制相似性聚类。主要计数口径是
  **不同论文数**；atom 数只能作为补充并明确标注，避免多 atom 论文被重复放大。
- 汇总常见 atom 顺序和组合形成的技术链，报告主要 target、action、effect，以及 partial/空数组带来的证据边界。
- 每个主要簇选 2-3 篇代表，按“method → 技术链（target→action→effect）→ problem/scenario/evidence”呈现。
- 高频不等于效果更好；`limitation=null` 只表示摘要未声明限制，不能解释为没有限制。
- **B 段（结合方向）**：再引入 `radar/config.yml` 的 interest lens，用 atom 的 target/effect 寻找命中论文和跨域迁移接口，并显式携带 limitation。
- 候选表继续使用 checkbox；已在 read_status 中 picked/carded 的条目标注出来，避免重复推荐。

## Stage 2：方法卡

触发：“细读 X”“给 X 出方法卡”。

1. 输入为论文 index 行、其有序 technique atom 链和 meta_json 摘要。不得因摘要不足而自动读取论文页或 PDF；仅当用户明确要求细读时，才使用当前平台可用的论文页或开放 PDF 获取能力。
2. 按 `radar/cards/_TEMPLATE.md` 写入 `radar/cards/<slug>.md`。方法卡的“机制”节必须按 atom 顺序重建技术链，并区分摘要已明确的步骤与 partial limitation；深读得到的新信息需标明来源，不能反向伪装成摘要抽取结果。
3. 核心仍是“机制（领域无关描述）”与“迁移假设”；相关卡使用 `[[slug]]` 互链。
4. 更新 read_status：`state=carded`，记录 card 路径。

## read_status.json 约定

键为 compact title（字母数字小写，与 `main.py compact()` 一致）：

```json
{"<compacttitle>": {"title":"原标题","venue":"USENIX Sec - 2025",
  "state":"picked|carded|read|skipped","card":"cards/xxx.md","date":"YYYY-MM-DD"}}
```

## 原则

- index 对全量建，方向总结 A 段保持中立，方法卡只对勾选项生成。
- interest lens 是锚，不是过滤器；视野外的强机制仍进入 index 和 A 段。
- 语义产出只写 `radar/`，绝不修改 `src/assets/data/`。
- 同一 scope 重跑时，index 增量补新增论文；map 按月份另存，不覆盖旧文件。
