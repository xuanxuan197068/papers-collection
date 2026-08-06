# radar/ — 语义雷达产出层

论文数据本体在 `src/assets/data/`（保持上游 schema 不动）；一切语义扩展产出放这里，
由当前平台的 `radar-digest` Skill 在会话内生成，跨 run 积累。Codex 使用
`.agents/skills/radar-digest/`，Claude Code 使用 `.claude/skills/radar-digest/`；两份 Skill
共享相同的 schema、抽取约束、质量闸和 Stage 1/2 语义。

```
config.yml                 interest lens（研究方向锚）、默认范围、打分维度
schema/technique-v2.schema.json  technique-v2 权威契约
index/<Pub> - <Year>.json   逐篇方法索引；technique-v2 为 0-4 个有序原子对象
state/read_status.json     勾选/已读/成卡状态（跨 run 反馈信号，按 compact-title 键控）
state/missing_abstracts.json  抓取链没找到摘要的论文（tools/fetch_new.py 维护）
maps/<YYYY-MM>_<scope>.md  Stage 1 方向图谱（全量、按机制簇聚合、N/R/T 排序）
cards/<slug>.md            Stage 2 方法卡（只对勾选论文，模板见 cards/_TEMPLATE.md）
```

两阶段用法：会话里说"总结最新方法"跑 Stage 1 出图谱 → 从图谱勾选感兴趣条目 →
"细读第 X 篇 / 给 XX 出方法卡"跑 Stage 2。

## technique-v2 与迁移

每个 technique atom 必须且只能包含
`name/type/target/action/effect/grounding/limitation`。Stage 1 以不同论文数为主要计数单位，
按 type/name/target/action 聚类；Stage 2 按 atom 顺序重建技术链。旧 technique 字符串只在
迁移期由前端兼容，不属于 v2 coverage。

默认 `full` 模式用于补齐完整 index 行：

```bash
uv run tools/radar_shard.py --pub "<Publication>" --year <Y> --mode full
# 使用可用子代理填写 out_NN.json 后：
uv run tools/radar_index_merge.py --pub "<Publication>" --year <Y> --mode full --check-only
uv run tools/radar_index_merge.py --pub "<Publication>" --year <Y> --mode full
```

`technique` 模式只迁移已有行的 technique；`--force` 会重新分片已是合法 v2 的行：

```bash
uv run tools/radar_shard.py --pub "NDSS" --year 2025 --mode technique
# 使用可用子代理填写 out_NN.json 后：
uv run tools/radar_index_merge.py --pub "NDSS" --year 2025 --mode technique --check-only
uv run tools/radar_index_merge.py --pub "NDSS" --year 2025 --mode technique
```

NDSS 2025 是首个试点。正式合并前必须达到 100% shard 行数、identity 一致和 schema
有效；合并后分别报告 meta 行覆盖率、technique-v2 覆盖率，以及空数组、partial、other 数量。
