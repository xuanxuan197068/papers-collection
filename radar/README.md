# radar/ — 语义雷达产出层

论文数据本体在 `src/assets/data/`（保持上游 schema 不动）；一切语义扩展产出放这里，
由 `.claude/skills/radar-digest` 在 Claude Code 会话内生成，跨 run 积累。

```
config.yml                 interest lens（研究方向锚）、默认范围、打分维度
state/read_status.json     勾选/已读/成卡状态（跨 run 反馈信号，按 compact-title 键控）
state/missing_abstracts.json  抓取链没找到摘要的论文（tools/fetch_new.py 维护）
maps/<YYYY-MM>_<scope>.md  Stage 1 方向图谱（全量、按机制簇聚合、N/R/T 排序）
cards/<slug>.md            Stage 2 方法卡（只对勾选论文，模板见 cards/_TEMPLATE.md）
```

两阶段用法：会话里说"总结最新方法"跑 Stage 1 出图谱 → 从图谱勾选感兴趣条目 →
"细读第 X 篇 / 给 XX 出方法卡"跑 Stage 2。
