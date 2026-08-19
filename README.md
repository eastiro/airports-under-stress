# Airports Under Stress

![Python](https://img.shields.io/badge/python-3.12+-blue)
![CI](https://github.com/eastiro/airports-under-stress/actions/workflows/test.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)

用美国交通部（BTS）的逐航班数据研究：一架飞机的延误，如何沿着当天的轮转链传播、被吸收，或在机场网络中放大。

这个仓库目前只做 **P0 数据可行性审计**。P0 不搭网站、不训练预测模型，先回答最重要的问题：数据能否支撑一个严谨、可复现、适合写进简历和申请文书的项目。

## P0 边界

- 时间范围：2026 年 5 月，BTS 当前最新完整月份。
- 数据粒度：美国国内定期客运航班，逐航班记录。
- 核心主键：航班日期、承运航司、航班号、出发机场、计划出发时间。
- 轮转标识：`Tail_Number`（机尾号）。
- 进入 V0 前必须验证：
  - 已执行航班的机尾号缺失率足够低；
  - 同一机尾号的相邻航段能形成物理连续的 `上一站终点 = 下一站起点`；
  - 跨时区和跨午夜经过统一 UTC 时间轴后可可靠处理；
  - 取消、备降、缺失记录不会被悄悄塞进普通链路；
  - 我们推断的延误传播信号，与 BTS 的 `LateAircraftDelay` 有可解释的关系，但不冒充官方因果标签。

## 数据覆盖声明

BTS Reporting Carrier On-Time Performance 不是“美国天空中的所有航班”。2025 年起，强制报告范围是达到法定收入门槛的报告承运人，以及它们在可报告机场执行的美国国内定期、不经停客运航班。项目会在所有页面和结论中保留这条边界。

## 一键复现

```powershell
python scripts/download_bts.py --year 2026 --month 5
python scripts/run_p0.py --year 2026 --month 5
pytest
```

运行结束后，核心交付物位于：

- `reports/P0_DATA_AUDIT.md`：可行性结论和所有关键指标；
- `data/processed/p0_metrics.json`：机器可读指标；
- `data/processed/p0_chain_links.parquet`：通过物理连续性检查的轮转链边；
- `data/processed/p0_chain_samples.csv`：人工可读的典型链路样本。

## 版本路线

- **P0**：一个月数据审计与 Go / No-Go 结论。
- **V0**：描述性数据产品，展示机场压力、航司/机场对比和真实轮转链案例。
- **V1**：级联与恢复机制，给出传播率、吸收率、脆弱链路和可复现实验。
- **V2**：加入 NOAA 天气，区分外部冲击与网络内部传播。
- **V3**：情景模拟器，测试航班或机场受到冲击后的网络响应。

## 官方来源

- BTS Reporting Carrier On-Time Performance 数据表
- BTS 字段定义页
- BTS 2025 Reporting Directive No. 39

具体链接和下载校验值会写入 P0 报告。

