# Airports Under Stress — 交接说明

最后更新：2026-07-26

## 接手目标

V0 中英双语站点已经完成并私有发布。接手后的第一目标是根据用户反馈修改文案和视觉细节，冻结 V0；除非用户明确同意，不要直接开始 V1。

除非用户改变方向，暂时不要开始 V1，也不要重做已经完成的数据管线。

## 开始前先看

按顺序阅读：

1. `PROJECT_STATUS.md`：当前总体状态和未完成项。
2. `reports/P0_DATA_AUDIT.md`：数据可行性结论和核心数字。
3. `docs/P0_PROTOCOL.md`：预先冻结的审计规则。
4. `docs/DATA_DICTIONARY.md`：字段和派生指标定义。
5. `web/app/dashboard.tsx`：已经发布的双语交互页面。
6. `web/app/globals.css`：全站视觉系统和语言切换器样式。

## 当前稳定状态

已部署源码提交：

```text
b02076d feat: add Chinese-first bilingual V0
```

当前线上版本：

```text
site: https://airports-under-stress.fizzy-elm-9171.chatgpt.site
Sites version: 2
visibility: owner-only
```

双语版本已经实现：

- 新增 `zh` / `en` 语言状态，默认 `zh`。
- 新增主要界面、排序项、轮转类型和航段状态的双语文案。
- 新增页头 `中文 / EN` 切换按钮。
- 中文化机场榜、航司对比、轮转故事、方法边界和页脚。
- 根据语言切换数字格式、延误单位和无障碍标签。
- 浏览器端切换时更新 `document.documentElement.lang`。
- 中文优先的页面标题、描述和分享元数据。
- 语言切换器的桌面、平板和手机布局。

## 下一步执行顺序

### 1. 收集用户反馈

优先让用户直接查看线上中文版，并记录具体修改意见。建议按以下顺序确认：

- 首页标题与项目副标题。
- “压力指数”“传播”“吸收”等术语。
- 机场榜和机场详情的信息密度。
- 4 个轮转故事是否足够直观。
- 是否需要给机场、城市和航司增加中文译名。

### 2. 修改时保持双语同步

大部分界面文案集中在 `web/app/dashboard.tsx` 的 `ui.zh` 与 `ui.en`。修改中文时检查英文含义是否仍一致；不要复制出第二套页面。

继续保持现有颜色系统：墨黑背景、薄边框、薄荷绿色激活态。不要为了局部意见重做整套视觉方向。

### 3. 每轮修改后验证

数据逻辑：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

网页：

```powershell
npm.cmd test
```

2026-07-26 的稳定结果：数据测试 `9 passed`，前端构建通过，网页测试 `1 passed`。

### 4. 发布

重点检查：

- 页头在桌面与手机宽度下是否拥挤。
- 中文长标题和机场详情指标是否自然换行。
- 切换到英文后所有主要区域是否同步变化。
- 图表悬停提示、按钮、ARIA 标签和轮转状态是否随语言变化。
- 中英切换不改变当前机场排序、选中机场和选中轮转故事。

每次通过验证后更新已有 Sites 项目，不要创建新项目：

```text
project_id: appgprj_6a64f2917a94819181201cc9f2e1d54a
site: https://airports-under-stress.fizzy-elm-9171.chatgpt.site
visibility: owner-only
```

## 文件地图

| 路径 | 用途 |
|---|---|
| `scripts/download_bts.py` | 下载并校验 BTS 原始月度数据 |
| `scripts/run_p0.py` | 执行 P0 数据审计与链路重建 |
| `scripts/build_v0_data.py` | 生成网页使用的 V0 聚合数据 |
| `src/airports_under_stress/` | 时间处理、下载和审计核心逻辑 |
| `tests/` | Python 数据逻辑测试 |
| `reports/P0_DATA_AUDIT.md` | P0 最终审计报告 |
| `web/app/v0-data.json` | 网页的固定 V0 数据快照 |
| `web/app/dashboard.tsx` | 已发布的中英双语主交互页面 |
| `web/app/globals.css` | 全站视觉与响应式样式 |
| `web/app/layout.tsx` | 页面语言和 SEO/分享元数据 |
| `web/tests/rendered-html.test.mjs` | 服务端渲染验收测试 |
| `web/.openai/hosting.json` | 已有 Sites 项目配置 |

## 数据复现

如需从头复现 2026 年 5 月数据：

```powershell
python scripts/download_bts.py --year 2026 --month 5
python scripts/run_p0.py --year 2026 --month 5
python scripts/build_v0_data.py
```

不要为了前端文案修改重新下载数据。`web/app/v0-data.json` 已经是 V0 使用的数据快照。

## 产品与叙事边界

项目最有价值的不是“做一个延误排行榜”，而是把逐航班记录还原成同一架飞机的轮转链，再观察压力如何传播或被吸收。简历和文书应强调：

- 处理跨时区、跨午夜、取消、备降和物理连续性。
- 用 611,735 条记录重建 549,388 条有效轮转关系。
- 主动区分描述性传播信号与因果结论。
- 从数据审计、可复现管线到交互式数据产品的完整闭环。

## 等用户确认的内容

接下来优先让用户对已发布的中文版提出意见：

1. 项目中文副标题是否准确、是否够有记忆点。
2. “压力指数”“传播”“吸收”等术语是否自然。
3. 首页信息密度是否过高。
4. 机场、航司等专有名词是否需要中文译名，还是保留官方英文。
5. 轮转故事是否足够直观，能不能让非航空背景的人快速理解。

用户确认这些内容后，再把 V0 冻结为一个干净提交并开始规划 V1。
