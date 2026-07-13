---
name: fetch-papers
description: 更新论文库——从 DBLP 拉取顶会最新论文并补齐摘要。当用户说"帮我获取最新论文"、"更新论文/更新XX会议"、"抓一下 NDSS/USENIX/CCS/S&P 2026"、"加一个新会议/期刊"、"fetch new papers" 时使用。驱动 tools/fetch_new.py + main.py --analyze，人工在环，汇报后由用户决定是否 commit。
---

# fetch-papers：论文库更新流程

本仓库有两条更新链。本 skill 驱动**自有链**（DBLP + 摘要兜底）；上游作者的
bib/csv+爬虫链是备用（见 AGENTS.md "Two update chains"）。

## 工作流

1. **确定范围**。用户点名了 venue/年份就用它们；说"最新论文"则对 data.yml 中
   全部 venue 检查当前年与下一年（今天日期决定）。venue 的 data.yml key：
   `oakland` `ccs` `usenix_security` `ndss` `ase` `icse` `issta` `fse` `sosp` `asplos`。

   可选先跑**完整性审计**看哪里有缺口（本地 vs DBLP vs 上游）：
   ```
   git fetch upstream        # 刷新上游对比
   uv run tools/audit_completeness.py [--venue KEY] [--recent 2] [--no-dblp]
   ```
   输出每 venue-year 的三方篇数 + 建议动作（gap 用与 fetch_new 相同的模糊匹配算，
   不误报措辞差异）。据此靶向 fetch_new（自有链补）或 merge 上游（见下）。

2. **检查 DBLP 是否有数据**（dry-run 不写任何文件）：

   ```
   uv run tools/fetch_new.py --venue <key> --year <YYYY> --dry-run
   ```

   - 目标 site 还没标 `source: dblp` 时（新年份），先在 data.yml 补 site 条目（见下节），再 dry-run。
   - 报告 "DBLP has no data yet" = 该年 proceedings 还没上 DBLP（如 USENIX 会前数月）。
     如实告知用户，该 venue 到此为止，**不要**硬抓。

3. **正式抓取**（增量、幂等，已有条目的摘要/链接不会被覆盖）：

   ```
   uv run tools/fetch_new.py --venue <key> --year <YYYY>
   ```

   多 venue 就逐个跑。全量跑所有标记 site：不带 `--venue`。

   **默认策略 full-slow**：标题全量入库，摘要三源兜底慢速补齐（限速已带随机抖动
   防触发限流）。大体量 venue（AI/ML 几千篇）或想挂机补摘要时，用挂机模式：
   ```
   uv run tools/fetch_new.py --loop 30       # 每轮跑完 sleep ~30 分钟再来一轮
   ```
   每轮增量+幂等（已有摘要跳过、自动 --retry-missing 重试失败项），可服务器 24h
   常驻把摘要补到 100%，Ctrl-C 退出。lazy 策略只作临时手段。

4. **重新生成前端 JSON**：

   ```
   uv run main.py --analyze
   ```

5. **汇报**，格式：每 venue-year 的 DBLP 总数 / 新增数 / 摘要命中分布
   （arxiv/s2/pdf/failed，fetch_new 结尾自带 report）+ `git diff --stat -- src/assets/data`
   摘要。仍缺摘要的论文在 `radar/state/missing_abstracts.json`，提醒用户可
   `--retry-missing` 重试或人工补。

6. **等用户确认后才 commit**。commit message 风格照上游：`update <venue> <year>`。

## data.yml 约定

新年份 site 条目（追加到该 venue 的 sites 列表**开头**，年份降序）：

```yaml
    - year: 2027
      source: dblp
      official_file: '<prefix>27.json'
```

official_file 前缀表：oakland→`oakland` ccs→`ccs` usenix_security→`uss`
ndss→`ndss` ase→`ase` icse→`icse` issta→`issta` fse→`fse` sosp→`sosp`
asplos→`asplos`（两位年份后缀，如 `ndss26.json`）。

新 venue 模板（**只能追加到 data.yml 文件末尾**，禁止调整已有 venue 顺序——
paper id 是遍历序号，重排会导致全量 id 变动）：

```yaml
neurips:
  name: NeurIPS
  category: ai-ml
  dblp_toc_template: conf/nips/neurips{year}
  abstract_policy: lazy        # AI/ML 大体量会议建议 lazy：标题全量入库，摘要勾选后按需补
  sites:
    - year: 2025
      source: dblp
      official_file: 'neurips25.json'
```

- `abstract_policy: full`（默认）= 抓取时补齐全部摘要；`lazy` = 摘要留 `#`，
  由 radar-digest Stage 2 按需补。用户可用 `--policy full|lazy` 临时覆盖。
- `dblp_toc_template` 不确定时先开 https://dblp.org/db/conf/<stream>/ 人工确认
  volume 命名（如 FSE 在 `conf/sigsoft`、ASE 在 `conf/kbse`、NeurIPS 早年
  `nips{year}` 近年 `neurips{year}`——年份不规则时在 site 级用 `dblp_toc` 覆盖）。

## 注意事项

- **USENIX 2026 目前仍走上游爬虫链**（DBLP 未建 TOC，2026-07 确认）。DBLP 上线后：
  给该 site 加 `source: dblp` + `official_file: 'uss26.json'` 即切换，增量合并不丢已有摘要。
- 假新增防护：fetch_new 对 DBLP 与站点标题做模糊去重（ratio≥0.9），日志里
  `[dup]` 行属正常。若怀疑漏判/误判，人工核对报告里的新增标题。
- 上游数据字段集合不可改（title/abstract/paper/publication/...），扩展信息一律进 `radar/`。
- fresh clone 后先跑 `uv run tools/rebuild_official_cache.py`（见 AGENTS.md）。
