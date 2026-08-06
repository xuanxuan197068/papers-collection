---
name: fetch-papers
description: 更新论文库——审计 DBLP/本地差异，探测当前年与下一年，从 DBLP 拉取会议或期刊论文并补齐摘要，处理多卷 TOC、限流与中断恢复，再重建前端数据。当用户说“获取最新论文”“更新论文/会议/期刊”“抓 NDSS/USENIX/CCS/S&P”“检查有没有新论文”“加新 venue”或“fetch new papers”时使用。驱动 tools/fetch_new.py + main.py --analyze，人工在环，汇报后由用户决定是否 commit。
---

# fetch-papers：论文库更新流程

本仓库有两条更新链。本 skill 驱动**自有链**（DBLP + 摘要兜底）；上游作者的
bib/csv+爬虫链是备用（见 CLAUDE.md "Two update chains"）。

## 工作流

1. **确定范围并保护现场**。先运行 `git status --short --branch`，记录已有未提交改动，
   后续只碰更新链文件。用户点名了 venue/年份就用它们；说“最新论文”则从 `data.yml`
   动态读取**全部** venue（包括期刊和后来追加的 venue），检查当前年与下一年。不要维护
   硬编码 key 列表，它会漏掉 TIFS 等新增项。

   可选先跑**完整性审计**看哪里有缺口（本地 vs DBLP vs 上游）：
   ```
   git fetch upstream        # 刷新上游对比
   uv run tools/audit_completeness.py [--venue KEY] [--recent 2] [--no-dblp]
   ```
   输出每 venue-year 的三方篇数 + 建议动作（gap 用与 fetch_new 相同的模糊匹配算，
   不误报措辞差异）。据此靶向 fetch_new（自有链补）或 merge 上游（见下）。

   `--recent` 只审计 `data.yml` 已有年份，**发现不了尚未配置的新年份**。审计后还要打开
   每个 venue 的 DBLP stream，人工确认当前年/下一年是否已有正式 TOC。区分主论文集与
   companion/workshop；不要把 companion 当作主会论文加入。

2. **检查 DBLP 是否有数据**（dry-run 不写任何文件）：

   ```
   uv run tools/fetch_new.py --venue <key> --year <YYYY> --dry-run
   ```

   - 目标 site 还没标 `source: dblp` 时，先在官方 DBLP venue 索引确认 TOC key。只有确认
     TOC 已有论文后才持久化新 site；不要留下“有配置但没有 official_cache JSON”的空年份，
     否则 `main.py --analyze` 可能读取不到输入文件。
   - TOC 命名不一定等于模板。多卷会议（如 ASPLOS）必须把所有卷写成 `dblp_toc` 列表，
     然后 dry-run 合并去重；见下方配置示例。
   - 报告 "DBLP has no data yet" = 该年 proceedings 还没上 DBLP（如 USENIX 会前数月）。
     如实告知用户，该 venue 到此为止，**不要**硬抓。
   - 只在每个 TOC 的 venue XML 由主站或官方镜像成功返回、总数合理时信任结果。如果日志
     出现 5xx、timeout、search API fallback、总数突然变小或恰好只有 100 条，先冷却后重试；
     搜索 API 可用于发现，不能作为大型 venue 的完整性证明。多卷 TOC 任一卷失败也要重试。

3. **正式抓取**（增量、幂等，已有条目的摘要/链接不会被覆盖）：

   ```
   uv run python -u tools/fetch_new.py --venue <key> --year <YYYY>
   ```

   多 venue **逐个 venue-year 跑并保存每次 report**。这样一个 venue 失败不会丢失整批
   `missing_abstracts` 状态，也避免宿主截断超长输出。只有已完整 dry-run、需要无人值守时，
   才不带 `--venue` 全量运行。`-u` 让直接终端尽早刷新进度；脚本会把 Windows 输出设为 UTF-8。

   **默认策略 full-slow**：标题全量入库，摘要三源兜底慢速补齐（限速已带随机抖动
   防触发限流）。大体量 venue（AI/ML 几千篇）或想挂机补摘要时，用挂机模式：
   ```
   uv run python -u tools/fetch_new.py --loop 30       # 每轮后约 30 分钟再来一轮
   ```
   每轮增量+幂等（已有摘要跳过、自动 --retry-missing 重试失败项），可服务器 24h
   常驻把摘要补到 100%，Ctrl-C 退出。lazy 策略只作临时手段。

   写入以 venue 为边界：一个 venue 摘要处理完才写 `official_cache/<file>.json`；
   `radar/state/missing_abstracts.json` 在本次命令结束时保存。因此中途崩溃时，已写完的 venue
   会保留，正在处理的 venue 会重做。直接幂等重跑即可。若停止宿主等待后发现 `uv/python`
   子进程仍存活，先核对 PID/启动时间并终止该次任务，避免两个进程并发写同一缓存。

4. **重新生成前端 JSON**：

   ```
   uv run main.py --analyze
   ```

   `official_cache/` 被 gitignore；不要强制提交它。提交候选是 `data.yml`、更新链脚本、
   `radar/state/missing_abstracts.json` 和重建后的 `src/assets/data/`。fresh clone 可由已提交的
   meta_json 运行 `tools/rebuild_official_cache.py` 重建缓存。

5. **验证并汇报**：

   ```
   git diff --check
   uv run python -u tools/fetch_new.py --dry-run   # 最终应 new=0；异常 TOC 定向重试
   npm run build                                   # Windows 策略拦截 npm.ps1 时用 npm.cmd run build
   git diff --stat -- src/assets/data
   ```

   核对每个 venue-year 的生成 meta_json 数量与可信 DBLP 总数；全部 JSON 应可解析。汇报
   DBLP 总数 / 本地总数 / 新增数 / 摘要命中分布（arxiv/s2/pdf/failed）。仍缺摘要的论文在
   `radar/state/missing_abstracts.json`，提醒用户稍后用 `--retry-missing` 重试或人工补。

   论文 `id` 是 `data.yml` 遍历时的运行序号：给靠前 venue/year 增加论文会顺延后面所有
   论文的 id，所以大量历史 meta_json 和 `data.json` 变化可能是预期结果。用标题、数量和
   顺序验证，不要仅凭 diff 很大就回滚。

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

多卷 site 使用一个合并后的 official JSON，加 TOC 列表：

```yaml
    - year: 2026
      source: dblp
      official_file: 'asplos26.json'
      dblp_toc:
        - conf/asplos/asplos2026-1
        - conf/asplos/asplos2026-2
```

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

- 不依赖 skill 内的日期结论；每次都重新探测 DBLP。USENIX 等年份在 DBLP TOC 上线前继续
  使用现有站点爬虫/缓存；上线后再切 `source: dblp`，增量合并不会覆盖已有摘要。
- `git fetch upstream` 后先看 `git diff --stat HEAD..upstream/main`。若 upstream 已换架构或不再
  保留同路径 meta_json，审计里的 upstream `-` 表示“不可比较”，不是 0 篇；不要为了数据更新
  直接 merge 一个大规模不兼容上游。
- 假新增防护：fetch_new 对 DBLP 与站点标题做模糊去重（ratio≥0.9），日志里
  `[dup]` 行属正常。若怀疑漏判/误判，人工核对报告里的新增标题。
- 上游数据字段集合不可改（title/abstract/paper/publication/...），扩展信息一律进 `radar/`。
- fresh clone 后先跑 `uv run tools/rebuild_official_cache.py`（见 CLAUDE.md）。
