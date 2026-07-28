# External Agent Task — V1-B 精选 Shockwave Episode Explorer

状态：Codex 接管收尾，第二轮最终验收通过  
执行者：External Agent  
验收者：Codex  
阶段：V1-B 第一版；精选案例数据 + 桌面端冲击波播放器

## 1. 任务目标

V1-A 已经回答“哪些机场和链路更容易传播延误”。V1-B 第一版必须进一步回答：

> 一次真实延误冲击从哪里开始，沿同一架飞机的轮转链如何传播、放大、被吸收，并最终恢复或观察中断？

本轮不是全量 episode 检索系统。只从冻结的 66,538 个正式 episode 中按可复现规则选出约 12 个具有不同机制特征的案例，做成可播放、可逐步查看的桌面端 Episode Explorer。

V1-B 必须与现有“飞机轮转故事”形成区分：

- 轮转故事：直观展示一架飞机连续飞了哪些航段；
- V1-B：从状态机识别的一次 shockwave episode 出发，解释每一步为何属于传播、放大、追回、恢复或删失。

## 2. 开工前必读

按顺序完整阅读：

1. `PROJECT_STATUS.md`
2. `HANDOFF.md`
3. `tasks/external-agent/EXTERNAL_AGENT_TASK_V1_P0.md` 末尾 Codex 最终 GO 记录
4. `tasks/external-agent/EXTERNAL_AGENT_TASK_V1_A.md` 末尾 Codex 最终验收记录
5. `reports/V1_P0_MECHANISM_AUDIT.md`
6. `data/processed/v1_p0_summary.json`
7. `data/processed/v1_p0_ui_contract.json`
8. `src/airports_under_stress/v1_mechanism.py`
9. `web/app/MechanismSection.tsx`
10. `web/app/dashboard.tsx`、`web/app/globals.css`

冻结前提：V1-P0 与 V1-A 已验收通过。不得修改 episode 定义、状态机、P0 链边、阈值分母或既有科学结论来迎合前端。

## 3. 本轮明确边界

### 必须实现

- 可复现的精选案例生成脚本；
- 约 12 个去重 episode，覆盖多种机制类型；
- 完整且可审计的 episode / step 前端数据；
- 独立的“冲击波案例 / Episode Explorer”导航入口和 section；
- 案例选择、播放/暂停、上一步/下一步、直接点选步骤；
- 当前步骤的延误变化、周转、时间、机场路径和状态解释；
- episode 总结与结局说明；
- 中文默认、英文完整；
- 1366×768 桌面端重点打磨；
- 基础键盘操作、焦点状态和 `prefers-reduced-motion`。

### 本轮禁止实现

- 不做 66,538 个 episode 的全量搜索、筛选或分页；
- 不做 15/30/60 分钟阈值交互，仍冻结 T=15；
- 不做天气、拥堵控制、预测、因果或反事实模拟；
- 不做全美地图实时飞行动画；
- 不增加后端服务或数据库；
- 不为本轮单独进行完整手机端视觉打磨；
- 不提交、不发布。

15/30/60 阈值切换仅作为未来 V1-B2 可选增强项，不得提前混入本轮。

## 4. Desktop-first 与字号硬规则

项目已冻结为 desktop-first。主验收视口为 1366×768。

- 手机端只要求能打开且核心 React 流程不崩；不因卡片重排、字号或长页面密度阻塞本轮；
- 不得撤销 `globals.css` 末尾的 desktop readability floor；
- V1-B 桌面端任何用户需要阅读的正文、标签、时间、状态、机场名称、按钮文字不得小于 11px；
- 关键航班/机场代码、延误分钟和当前状态应明显大于辅助信息；
- 不允许依赖浏览器放大到 125%–175% 才能读清。

## 5. 精选案例规则

新增 `scripts/build_v1b_data.py`，从最终冻结产物读取：

- `data/processed/v1_p0_episodes.parquet`
- `data/processed/v1_p0_steps.parquet`
- `data/processed/p0_chain_links.parquet`
- 已有 V0 中英文机场/航司名称数据

目标选择 12 个左右、episodeId 不重复的案例，至少覆盖：

1. 最深传播：2–3 个；
2. 高初始延误但最终恢复：2 个；
3. 高压力日：2 个；
4. 普通日：2 个；
5. 跨 UTC 午夜：至少 1 个；
6. censored / 观察中断：2 个，且明确它不是“未恢复”的证据。

选取规则必须确定性、可解释、去重。类别发生重叠时按预先写死的优先顺序归入一个主类别，再从该类别下一候选补齐。允许为叙事质量增加如下确定性约束：

- 优先 `depth >= 2`；
- 路径与时间字段完整；
- 精确 step-to-link 匹配全部成功；
- 机场名称可解析；
- 避免 12 个案例过度集中在同一机尾号、同一机场或同一航司。

不得只在前端手写 12 个 episode。最终 JSON 中应保存 `selectionReason` / `selectionCategory`，生成脚本中应保存排序和去重规则。

## 6. Step 数据富化与精确匹配

`v1_p0_steps.parquet` 已包含传播状态，但缺少部分航班展示字段。必须用每个 step 的稳定物理字段精确匹配 `p0_chain_links.parquet`：

- `tailNumber == Tail_Number`
- `prevAirport == PrevOrigin`
- `turnAirport == Origin`
- `nextAirport == Dest`
- `prevArrUTC == PrevActualArrivalUTC`
- `nextDepUTC == ActualDepartureUTC`

每一步必须得到唯一匹配；0 条或多条均应使生成脚本失败，禁止模糊取第一条。

富化字段至少包括：

- 上一航段与下一航段的报告航司、航班号；
- 计划/实际到达 UTC、计划/实际起飞 UTC；
- `prevArrivalDelay`、`nextDepartureDelay`、`delayDelta`；
- 计划/实际周转分钟；
- 三机场代码及中英文城市名；
- `stepType`、`relation`、`depthAfterStep`；
- 用于前端解释的受控中英文状态 key，不在 JSON 中硬写整段营销文案。

不得凭空构造航班号、当地时间、天气、原因或机场连接。

## 7. 前端数据契约

生成 `web/app/v1-b-data.json`。建议结构：

```json
{
  "version": "v1_b_curated_episodes",
  "thresholdMinutes": 15,
  "sourceSummary": {
    "nEpisodes": 66538,
    "nSteps": 125350
  },
  "selectionMethod": {
    "targetCount": 12,
    "categories": []
  },
  "episodes": [
    {
      "episodeId": "...",
      "selectionCategory": "deepest",
      "selectionReason": "...",
      "tailNumber": "...",
      "carrier": "...",
      "depth": 15,
      "initialArrivalDelay": 172,
      "maxDepartureDelay": 162,
      "durationMinutes": 0,
      "outcome": "recovered",
      "terminationReason": "...",
      "observedStartUTC": "...",
      "endUTC": "...",
      "steps": []
    }
  ],
  "disclaimer": "..."
}
```

具体字段可以调整，但必须：

- JSON 不含 NaN、Infinity、动态时间戳；
- 科学字段直接来自冻结产物；
- 生成两次字节级一致；
- 不嵌入全量 episode；
- 体积保持适合静态前端，不为省体积删掉必要步骤。

## 8. V1-B 页面产品设计

新增独立组件，建议 `web/app/EpisodeExplorer.tsx`。放在 V1-A 传播机制之后、方法区之前，并增加清晰导航入口。

### 8.1 Section 开场

中文主标题建议方向：`跟随一次延误，直到它消失。`  
英文：`Follow one delay until it disappears.`

开场短文必须说明：

- 这是从 66,538 个正式 episode 中按规则选择的案例；
- 沿同一机尾号的连续轮转观察；
- “传播”是描述性连续信号，不单独构成因果；
- 默认阈值为 15 分钟。

### 8.2 案例选择器

不要做数据库式表格。用可读的精选案例卡或紧凑横向选择器，显示：

- 类型；
- 起点与路径摘要；
- 机尾号；
- 深度；
- 最终结局。

默认选择最深且数据完整的案例。切换案例后播放器重置到第 0 步并暂停。

### 8.3 冲击波主舞台

核心不是地图，而是横向 episode timeline / shockwave tape。允许横向滚动或在一个主视口内推进，但必须让当前步骤成为视觉焦点。

每一步至少展示：

- `上一机场 → 周转机场 → 下一机场`；
- 航司与航班号；
- 上一航段到达延误；
- 下一航段起飞延误；
- `delayDelta`；
- 计划与实际周转；
- UTC 时刻；
- 传播 / 放大 / 追回 / 恢复状态。

颜色语义必须稳定：危险/放大可使用珊瑚红，传播可使用琥珀色，追回/恢复使用 mint。不得只靠颜色表达状态。

### 8.4 播放控制

必须提供：

- 播放 / 暂停；
- 上一步 / 下一步；
- 直接点击步骤；
- 当前 `第 x / y 步`；
- 重新开始。

建议每步 1.8–2.5 秒。页面离开可视区、切换案例或用户手动操作后应正确停止/重置，不能残留多个 timer。`prefers-reduced-motion` 下不自动播放动画，只允许手动步进。

### 8.5 当前步骤解释

用自然语言回答“这一段发生了什么”，例如：

- 上一班晚到 82 分钟；
- 实际过站比计划多 14 分钟；
- 下一班以 96 分钟延误起飞，延误放大 14 分钟；
- 因此 episode 深度增加到 11。

文案必须由结构化字段和受控模板生成，不得把关联描述成已证明的因果关系。

### 8.6 Episode 总结

始终显示：

- 初始到达延误；
- 传播深度；
- 最大起飞延误；
- 累计放大分钟（沿用冻结定义）；
- episode 持续时间；
- 经过机场数；
- outcome 与 termination reason。

对于 censored：明确写“观察在链断裂或样本结束处停止，不能据此判断之后是否恢复”。

## 9. 无障碍与交互要求

- 播放按钮具有动态可访问名称；
- 步骤使用 button/tab 或等价键盘可操作元素；
- 当前步骤用 `aria-current` 或等价语义；
- 状态不只依赖颜色；
- 切换案例后焦点不应丢失；
- timer 在组件卸载时清理；
- 中英文切换不得丢失当前案例或造成 hydration mismatch。

## 10. 测试与验收

### 数据测试

新增测试至少验证：

- 案例数在约定范围内且 episodeId 全部唯一；
- 必需类别覆盖；
- 每个 episode 与最终 Parquet 科学字段一致；
- 每个 step 唯一精确匹配一条 P0 chain link；
- step 顺序、机场连续性、UTC 单调性正确；
- recovered episode 有 terminal recovery step；
- censored 文案状态不能伪装成 recovered；
- JSON 无非有限数和动态字段；
- 两次生成 hash 一致。

### 前端测试

- 中文和英文关键内容 SSR 存在；
- 12 个左右案例被序列化；
- 播放、暂停、步进和案例切换基础状态测试；
- ESLint 0 error / 0 warning；
- production build 通过；
- 现有 SSR 与数据测试不得回归。

### 浏览器自检

重点检查 1366×768：

- 第一屏能看懂这是一次具体延误传播；
- 不需要浏览器放大即可读清所有必要文字；
- 最深 15 步案例仍可导航，不挤成无法阅读的长条；
- 播放、暂停、上一步、下一步、直接点选均正常；
- 切换 recovered / censored 案例时结局说明正确；
- 中文默认，英文机场和机制术语完整；
- 无 hydration error、console error、timer 泄漏迹象。

手机端仅做一次打开与核心交互 smoke check，不做本轮验收阻塞项。

## 11. 完成与停止条件

完成后在本文末尾追加：

- 实际选择规则与 12 个案例清单；
- 新增/修改文件；
- 数据生成与精确匹配结果；
- 测试命令和原始结果摘要；
- 1366×768 浏览器检查结果；
- 已知限制；
- 明确写出未提交、未发布。

同时更新 `PROJECT_STATUS.md` 和 `HANDOFF.md`，但不得自行写“Codex 验收通过”。完成后停止，等待 Codex 独立验收。

## External Agent 进度记录

**状态：进行中，尚未提交验收。** 记录日期：2026-07-27。

### 已完成的实现

- 新增 `scripts/build_v1b_data.py`，只读取冻结的 `v1_p0_episodes.parquet`、`v1_p0_steps.parquet`、`p0_chain_links.parquet` 与既有 V0 静态名称/每日数据，生成 `web/app/v1-b-data.json`。
- 生成器以固定类别优先级、显式排序和稳定 tie-break 选择 12 个不重复 episode：`deepest` 3 个、`high_delay_recovered` 2 个、`high_pressure_day` 2 个、`normal_day` 2 个、`crosses_midnight` 1 个、`censored` 2 个；payload 保存 `selectionCategory` 与 `selectionReason`。
- 常规 step 以任务规定的 tail、三机场、上一实际到达 UTC、下一实际起飞 UTC 六字段精确关联 P0 chain link；缺失或重复 key 会使生成失败。`recovered_en_route` 通过其前一条已精确匹配的 delayed 航段进行严格 terminal 关联，不使用模糊匹配。
- 已生成 `web/app/v1-b-data.json`：12 个精选 episode，172,570 bytes；最新生成 SHA-256：`83cffdac8e9ae234a1dab3aa29f2b8e31f8d3152c73e0c46c9baca686b57614c`。
- 新增 `web/app/EpisodeExplorer.tsx`，集成双语案例选择、播放/暂停、前后步进、重启、直接选择步骤、当前步骤/episode 摘要、recovered/censored 边界说明、键盘 button 语义、动态 accessible name、`aria-current`、焦点样式、reduced-motion 禁止自动播放、timer 卸载及离开可视区清理。
- 修改 `web/app/dashboard.tsx`：增加 `#episodes` 导航入口，并在 V1-A 机制 section 与方法 section 之间挂载 Explorer。
- 修改 `web/app/globals.css`：增加 desktop-first 的案例选择器、横向 step tape、控制条、详情/总结两列布局与小屏 smoke-safe fallback；V1-B 新增用户可读文字维持 ≥11px。
- 新增 `tests/test_v1b_data.py` 并更新 `web/tests/rendered-html.test.mjs` 的 V1-B SSR 验证。

### 当前验证结果

| 检查 | 结果 |
|---|---|
| `python -m pytest -q tests/test_v1b_data.py` | **4 passed**（仅有既有 `.pytest_cache` 权限 warning） |
| `web/` 中 `npm.cmd test` | **7 passed** |
| `web/` 中 `npm.cmd run lint` | **0 error / 0 warning** |
| `web/` 中 `npm.cmd run build` | **通过** |
| V1-B JSON 生成 | **通过，12 curated episodes** |

### 尚未关闭的验收项 / 风险

1. 根目录完整 Python suite 尚未全绿：现有 `tests/test_v1_mechanism.py::test_cumulative_amplification_not_double_counting` 失败，失败对象为冻结机制 episode `ep-284NV-000479`（累计放大 293.0，大于该旧测试的 286.0 上限）。此失败未由 V1-B 修改引入，尚未修改冻结机制定义或科学产物。
2. 1366×768 浏览器实操验收尚未完成。尝试启动本地 `vinext dev` 后，该进程报告监听 localhost:3001，但当前执行环境无法连接对应端口；因此尚未声称播放器的真实浏览器交互、console/hydration 或手机 smoke check 已通过。
3. 尚未更新 `PROJECT_STATUS.md` 或 `HANDOFF.md`，以免在未完成独立浏览器与全套验证前把阶段写成完成。

**未提交、未发布。** 完成以上阻塞验证并进行独立验收前，本任务仍保持进行中。

## Codex 第一轮验收记录（2026-07-27）

结论：**不通过。数据生成方向基本可用，但当前前端没有达到 Episode Explorer 的产品目标。** 不得只换颜色或隐藏滚动条后再次声称完成。

### 已确认通过

- V1-B 静态数据为 12 个去重 episode，类别数量符合任务；
- 常规步骤使用六字段精确链路匹配，生成器对重复/缺失匹配会失败；
- ESLint 0 warning、production build 通过、SSR 7/7；
- 页面无当前 hydration / console runtime error；
- 现有数据文件包含航班号、机场城市名、周转和计划/实际时间，可支撑更完整的 UI。

### 阻塞问题 1：内部字段直接暴露给用户

真实页面直接显示：

- `deepest`
- `high_delay_recovered`
- `caught_up`
- `amplified`
- `recovered`
- 原始 `terminationReason`

这些是数据 key，不是产品文案。删失案例在选择按钮里甚至复用了完整警告句，导致一个按钮塞入“观察中断：链断裂或样本结束……”整段文字。

必须为 selection category、step state、outcome、termination reason 建立完整中英文受控标签。选择器只显示短标签，例如“最深传播 / 巨大延误后恢复 / 高压力日 / 普通日 / 跨午夜 / 观察中断”；步骤显示“继续传播 / 延误放大 / 正在追回 / 已恢复”。内部 key 只能作为程序字段，不能出现在可见 UI。

### 阻塞问题 2：两个原生横向滚动条破坏页面

1366×768 实测中，案例选择器和 step tape 各出现一条亮白色浏览器原生横向滚动条，页面看起来像未完成的数据表。最深 16 个展示步骤需要用户拖动第二条滚动条，播放到后半段时当前步骤会跑出视口，用户看不到播放器正在发生什么。

返工要求：

- 案例选择器改为 6 个中文机制类型入口 + 当前类型内案例切换，或两行可读卡片网格；不得放 12 个超长原始按钮后依赖横向滚动；
- step timeline 做成真正的舞台导航：允许内部横向轨道，但不得显示亮白原生滚动条；
- 当前步骤变化时必须自动将 active step 平滑或即时居中（reduced motion 下即时）；
- 为长 episode 提供清晰的已完成/当前/未到达进度，而不是 16 个同权按钮；
- active 元素仍应保留当前状态的颜色语义，不能因为 class 变成单独 `active` 而丢失 state class。

### 阻塞问题 3：生成的数据没有转化成故事

JSON 已有航司、航班号、机场英文城市名、计划/实际 UTC、周转、状态和延误变化，但页面只显示三段 IATA 代码和几组分钟数。当前步骤没有航班号、城市名、状态标题，也没有解释为什么判断为传播、放大、追回或恢复。

每个当前步骤至少必须展示：

- `ATL 亚特兰大 → DSM 得梅因 → ATL 亚特兰大` 这类代码 + 城市名；
- 上一航段与下一航段的航司代码和航班号；
- 状态大标题，例如“延误正在被追回”；
- 上一航段晚到、计划/实际周转、下一航段起飞延误和 delayDelta；
- 一句由字段模板生成的自然语言解释；
- UTC 时间使用紧凑可读格式，不直接铺完整 ISO 字符串。

英文模式使用英文城市名；中文模式必须补中文城市名。不得声称“数据里只有英文所以无法实现”，现有 `airport-names-zh.ts` / `v0-data.json` 已有中文映射来源。

### 阻塞问题 4：摘要语义不清且视觉过空

当前摘要出现 `+ 109 min · 2749 min` 这种无标签数字；`recovered (recovered)` 重复且暴露内部 key。页面同时显示“深度 15”与“第 1/16 步”却不解释 terminal recovery step 不增加 depth。详情区只占很少内容，下面留下大片空白，未形成任务书要求的冲击波叙事舞台。

必须：

- 给所有摘要数字明确标签；
- 明确区分“传播深度 15 个延误步骤”和“时间轴共 16 个观察步骤（含最终恢复）”；
- 对累计放大分钟、episode 持续时间、经过机场数、最大延误和结局分别排版；
- recovered 显示恢复发生的机场/步骤；censored 显示具体边界原因及“不代表之后没有恢复”；
- 将当前步骤、进度和 episode 摘要组合成有视觉层级的主舞台，消除无意义大片空白。

### 阻塞问题 5：选择器与案例叙事不足

案例卡只有 raw category、机尾号、深度、outcome，用户不知道为什么值得看。每个案例入口至少显示短中文类型、可读路径摘要、深度和短结局；选中后显示 `selectionReason` 的产品化解释，但不要展示“stable priority 1”这类实现文字。

默认仍选择最深案例。切换 recovered/censored 案例后必须重置、暂停且立即更新边界说明。

### 测试与性能收口

- External Agent 报告的旧机制测试失败来自一个数学上不成立的旧断言：多次正向放大之和并不必然小于 `initial + max`。Codex 已把该测试改为逐 episode 精确核对 `sum(max(delayDelta, 0))`，不得修改冻结科学定义来迎合旧上限；
- 当前 V1-B 数据测试会多次重建 549,388 条 Python 字典索引，独立复验运行数分钟仍未结束。应缓存模块级 payload/索引或拆分轻量 fixture，使常规 V1-B 测试在合理时间内结束；真正的双跑确定性可保留为一个明确的慢测试或直接比较连续生成 hash，但不能让每个测试重复全量索引；
- 增加前端状态/文案测试，至少覆盖中英文类别标签、state label、深度与步骤数区别、censored 短标签与完整边界说明；
- 返工后重新运行 Python V1-B/V1 mechanism、lint、build、SSR，并完成真实 1366×768 浏览器播放到最后一步、案例切换和中英文检查。

仍未提交、未发布。返工完成后在本节之后追加执行记录，停止并等待 Codex 第二轮验收。

## Codex 接管收尾与第二轮最终验收（2026-07-27）

结论：**通过。V1-B 第一版可以冻结。**

External Agent 已完成大部分第一轮返工代码，但其 Claude Code 会话停在半程。Codex 通过本机 CLI 检查发现父交互 session 与后台 session 均处于 idle；向原 session 续发任务无法获得执行，fork 同上下文后模型通道连续 10 次 `api_retry`，最终明确返回 `Unable to connect to API (ConnectionRefused)`，0 tokens / 0 cost。该故障属于外部模型接口连接，不是项目代码阻塞。

Codex 随后直接接管并完成：

- 恢复案例不再错误显示 censored 警告；只有删失案例显示完整观察边界；
- 重新加入离开可视区自动停止 timer，保留 reduced-motion 与步骤自动居中；
- 1366px 桌面案例区由 3×4 调整为 6×2，使播放器控制和时间轴进入首个主要视口；
- 补齐精选案例中原映射缺少的 12 个机场中文名称；未知城市不再渲染为 `DAY DAY` 之类重复代码；
- 中文模式航司名称使用现有中文映射；
- 修正旧机制测试中数学上不成立的累计放大上限，改为精确核对每个 episode 的正向 `delayDelta` 之和，未修改冻结科学定义；
- V1-B 测试缓存昂贵 payload，避免每项测试重复建立 549,388 条链索引；机制测试中的重复全量 episode 构建改为复用 fixture / 小样本确定性测试；
- 清除 pandas groupby deprecation warning 的写法。

最终自动验证：

- `python -m pytest -q tests/test_v1b_data.py`：4 passed；
- `python -m pytest -q tests/test_v0_data.py`：21 passed；
- `python -m pytest -q tests/test_v1_mechanism.py`：29 passed；
- `npm.cmd run lint`：0 error / 0 warning；
- `npm.cmd run build`：通过；
- `npm.cmd run test:ssr`：7/7 passed；
- `git diff --check`：通过。

最终 1366×768 浏览器验收：

- 12 个案例使用双语产品标签，无 `deepest/caught_up/high_delay_recovered` 等 raw key；
- 案例区无原生白色横向滚动条，step tape 隐藏原生滚动条并自动跟随当前节点；
- 最深案例可从 1/16 步进至 16/16，terminal step 显示“已恢复”；
- 自动播放 2 秒后从第 1 步推进到第 2 步，暂停正常；
- censored 案例切换后重置为 1/12，显示具体中断边界与“不代表之后没有恢复”；
- 中英文类别、状态、城市名、航班号和边界文案完整；
- 无当前 hydration、React 或应用 console error。

当前仍未提交、未发布。手机端按冻结策略只保留 smoke-safe，不属于本轮完整视觉验收。
