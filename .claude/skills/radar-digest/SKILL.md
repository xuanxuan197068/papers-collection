---
name: radar-digest
description: 论文雷达语义层——两阶段读库总结。当用户说"总结最新方法"、"XX 方向有什么新东西"、"跑一次雷达/初筛"、"出方向图谱"（Stage 1），或"细读第 N 篇"、"给 XX 出方法卡"、"标记已读"（Stage 2）时使用。读 src/assets/data/meta_json，产出写 radar/，跨 run 积累。
---

# radar-digest：两阶段语义雷达

目标：跨领域找可迁移方法（新机制 × 原始场景 × 解决的问题 × 迁移假设），
为用户的论文提供方法支撑。先读 `radar/config.yml`（interest lens、默认范围、
打分维度）和 `radar/state/read_status.json`（已读状态）。

## Stage 1 初筛（广度，全量，廉价）

触发："总结最新方法"、"跑一次雷达"、"看看 <venue/年份> 有什么新东西"。

1. **定范围**：用户点名优先；否则按 config 的 default_scope（最近一年 × 全 venue）。
   数据源 = `src/assets/data/meta_json/<Publication> - <Year>.json`。
2. **提取标题清单**（全量）。论文多时用脚本抽 `id/title` 两列再读，不要整文件
   读进上下文；摘要只对簇代表作抽读（每簇 2-3 篇）用于校准簇的定性。
3. **聚类成机制簇**（不是逐篇列表，也不是词频）：按"用什么机制解决什么问题"
   归簇，簇名用机制语言（如"用欺骗环境反制恶意 agent"而非"LLM security"）。
4. **写方向图谱** `radar/maps/<YYYY-MM>_<scope>.md`：
   - 头部：范围、论文总数、生成日期；
   - 每簇：簇名、规模、代表论文（编号+标题+venue）、与 interest lens 的关联注记；
   - 尾部：**勾选候选表**——对 lens 关联最强的 10-20 篇给 N/R/T 预评分并排序，
     每篇一行（编号｜标题｜venue｜N/R/T｜一句话机制）。
   - 已在 read_status 里 picked/carded/read 的论文标注出来，避免重复推荐。
5. **呈现给用户勾选**。用户的勾选写入 read_status（state=picked）。

## Stage 2 细查（深度，只对勾选项，贵）

触发："细读 X"、"给 X 出方法卡"。

1. 从 meta_json 拿摘要；摘要为 `#`（lazy venue）或需要细节时，抓论文页/开放 PDF
   （复用 `analyzers/abstract_enricher.py` 的 `pdf_lookup`，或直接 WebFetch）。
2. 按 `radar/cards/_TEMPLATE.md` 写卡到 `radar/cards/<slug>.md`（slug=小写连字符短名）。
   核心是"机制（领域无关描述）"和"迁移假设"两节——写给未来复用的自己。
3. 更新 read_status：state=carded，记 card 路径。

## read_status.json 约定

键 = compact title（字母数字小写，同 main.py compact()）：

```json
{
  "<compacttitle>": {
    "title": "原标题", "venue": "USENIX Sec - 2025",
    "state": "picked | carded | read | skipped",
    "card": "cards/xxx.md",
    "date": "YYYY-MM-DD"
  }
}
```

## 原则

- 图谱对**全量**做，卡只对**勾选项**做——省贵环节。
- interest lens 是锚不是过滤器：视野外的强机制照样入图谱（跨域迁移是本意）。
- 产出只进 `radar/`，不改 `src/assets/data/`。
- 同一 scope 重跑：读旧 map + read_status 做增量视角（新增了什么、哪些已处理），
  新 map 文件按月份另存，不覆盖旧的。
