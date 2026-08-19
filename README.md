# Airports Under Stress

An interactive data study of how flight delays propagate, recover, and interact with weather and scheduled congestion across U.S. aircraft rotations.

一个研究美国航空延误如何沿真实飞机轮转链传播、恢复，并与天气和计划拥挤共同出现的交互式数据项目。

![CI](https://github.com/eastiro/airports-under-stress/actions/workflows/test.yml/badge.svg)

![Airports Under Stress 实际网站首页](web/public/site-preview.png)

## 项目概览

项目使用美国交通部交通统计局（BTS）2026 年 5 月逐航班数据，以机尾号重建飞机的连续轮转关系。网站不是实时航班追踪器，也不提供机场安全排名；它展示的是冻结样本内的描述性网络现象。

- 611,735 条 BTS 逐航班记录
- 549,388 条通过物理连续性检查的轮转关系
- 15 / 30 / 60 分钟三档延误定义敏感性
- 真实连续延误案例、天气分层和计划拥挤分析
- 中文优先，中英双语
- 数据处理、科学审计、前端快照与自动测试完整保留

## V0–V3 研究路线

| 阶段 | 问题 | 主要产出 |
|---|---|---|
| V0 | 哪些机场与航司在样本内承受更高的相对压力？ | 全国网络、机场压力、航司对比、真实轮转故事 |
| V1 | 延误如何沿同一架飞机继续传播，又在哪里被吸收？ | 连续延误 episode、传播与恢复机制、阈值敏感性 |
| V2 | 天气与延误传播如何同时出现？ | 严格 backward weather join、机场分层、多因素描述性调整 |
| V3 | 同一机场排班更密时，延误是否更常继续？ | 全国计划拥挤分析与 54 个满足样本门槛的机场探索器 |

## 科学边界

- BTS Reporting Carrier On-Time Performance 并不覆盖美国天空中的全部航班。
- “传播”表示同一机尾号的相邻航段均超过所选延误门槛，不证明前一航段造成后一航段延误。
- 天气与计划拥挤结果是描述性关联，不是因果估计、预测模型或机场好坏排名。
- V3 机场探索器要求同一机场的松、密排班组各至少 100 次衔接；OMA 因样本不足被排除。
- 详细口径、Gate 与可复现性结果见 [`reports/`](reports/)。

## 本地运行网站

需要 Node.js 22.13 或更高版本。

```bash
cd web
npm ci
npm run dev
```

浏览器打开终端显示的本地地址，通常是 <http://localhost:3000/>。

前端使用仓库中已冻结的 JSON 快照，因此查看网站不需要先下载数百 MB 原始数据。

## 运行前端检查

```bash
cd web
npm run lint
npm run build
npm run test:ssr
```

冻结版验证结果：Python 104 项、SSR 10 项全部通过，ESLint 与生产构建通过。

## 重建研究数据

需要 Python 3.11+。原始 BTS 与天气文件体积较大，不提交到 Git；下载地址、哈希和数据口径记录在审计报告中。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python scripts/download_bts.py --year 2026 --month 5
python scripts/run_p0.py --year 2026 --month 5
python scripts/run_v1_p0.py
python scripts/download_weather_v2_p0.py
python scripts/run_v2_p0_weather_audit.py
python scripts/run_v3_p0_congestion_audit.py
pytest
```

各阶段的前端快照构建器位于 [`scripts/`](scripts/)。请先阅读对应的 [`reports/`](reports/) 与数据字典，再重建下游产物。

## 技术栈

- Python, pandas, PyArrow, pytest
- React 19, TypeScript, vinext, Vite
- Cloudflare Workers-compatible frontend output
- BTS 航班数据与 IEM/ASOS 天气观测

## 仓库结构

```text
src/       核心数据处理与研究逻辑
scripts/   下载、审计和前端快照构建脚本
tests/     Python 数据与科学口径测试
reports/   各阶段审计报告和研究边界
docs/      数据字典与协议
web/       交互式双语网站
data/      原始/处理数据目录说明（大文件被忽略）
```

## Feedback

欢迎通过 GitHub Issues 报告可复现的错误、可读性问题或数据口径疑问。新功能和新的研究问题应作为独立版本讨论，不直接改变冻结的 V3 口径。

## License

Code is released under the [MIT License](LICENSE). External datasets remain subject to their respective source terms and attribution requirements.
