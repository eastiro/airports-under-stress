# V2 天气数据字典

## 来源

主源：Iowa State University Environmental Mesonet（IEM）ASOS/METAR archive：

`https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py`

它是大学维护的航空气象档案，不是 NOAA NCEI 最终归档数据。每份原始响应旁保存请求参数、下载时间、HTTP 状态、字节数和 SHA-256；动态下载时间不进入科学产物哈希。

## 原始字段与单位

| 字段 | 含义 | 原始单位 |
|---|---|---|
| `station` | IEM 站点代码，可能是 IATA 或 ICAO | — |
| `valid` | 观测有效时刻 | 请求固定为 UTC |
| `lat` / `lon` | 站点位置 | 十进制度 |
| `elevation` | 站点海拔 | 米；IEM 已是米，不再乘 0.3048 |
| `tmpf` / `dwpf` | 气温 / 露点 | 华氏度 |
| `relh` | 相对湿度 | % |
| `drct` | 风向 | 度 |
| `sknt` / `gust` | 持续风 / 阵风 | 节 |
| `vsby` | 能见度 | statute mile |
| `skyc1..4` | 各云层覆盖类型 | CLR/FEW/SCT/BKN/OVC/VV 等 |
| `skyl1..4` | 各云层底高 | 英尺 |
| `wxcodes` | 当前天气现象代码 | METAR code |
| `metar` | 原始航空气象文本 | — |

## 标准化字段

| 字段 | 定义 |
|---|---|
| `valid_utc` | timezone-aware UTC |
| `temperature_c` / `dew_point_c` | 摄氏度 |
| `wind_speed_mps` / `wind_gust_mps` | 米/秒，同时保留原始节 |
| `visibility_km` | 公里，同时保留原始英里 |
| `elevation_m` | 直接复制 IEM `elevation` |
| `ceiling_ft` | 仅在 BKN、OVC、VV 层中取最低云底；FEW/SCT 不构成 ceiling |
| `is_five_minute_partial` | 原始文本含 `MADISHF` 的 5 分钟部分观测 |
| `is_complete_metar` | 非 `MADISHF` 的完整 METAR/SPECI 报告 |
| `report_type` | `FIVE_MINUTE`、`METAR_OR_SPECI`，或文本明确时的 `SPECI` |
| `is_duplicate_report` | 同站同 UTC 时刻原先存在多个报告；去重后仍保留该标记 |
| `usable_for_exposure` | 完整报告，且能见度、持续风和至少一层天空状况可用 |
| `airport_code` | 经显式站点映射得到的 BTS IATA 机场代码 |

IEM 导出不能总是可靠区分常规 METAR 与 SPECI，因此不根据分钟数猜测类型。`METAR_OR_SPECI` 是有意保守的标签。

## 候选天气状态

- `low_visibility`：`vsby < 3` statute miles；
- `low_ceiling`：`ceiling_ft < 1,000` ft；
- `strong_wind`：`sknt >= 20` 或 `gust >= 30` kt；
- `precipitation`：天气代码含 RA/SN/DZ/SG/PL/GR/GS；
- `thunderstorm`：天气代码含 TS；
- `fog`：天气代码含 FG 或 BR；
- `adverse_weather`：上述任一条件成立。

`gust`、`present_weather` 或 `ceiling_ft` 为空通常有明确语义：没有报告阵风、没有显式天气现象、或没有 BKN/OVC/VV ceiling。不能简单将其写成数据损坏。

## 站点映射

优先使用与机场相同的 IATA 站点代码；若 IEM 使用地区性 ICAO 前缀，则使用 `airportsdata` 的官方 ICAO，例如 HNL→PHNL、SJU→TJSJ。映射保存站点经纬度、机场经纬度来源、距离和方法。

V2-P0 未使用邻站替代。PBI 因 IEM 无 PBI/KPBI 同机场响应而保持 `unmapped`。

## 时间连接

主连接固定为 backward as-of：只允许事件时刻之前的最近观测，禁止使用未来天气。完整报告口径计算 30/60/90 分钟三档；V2-A 默认 90 分钟，并展示 60/90 分钟敏感性。

逐机场小时覆盖按该机场首末计划起飞 UTC 覆盖的小时窗口计算，并分别报告任意观测、完整 METAR/SPECI 和 `usable_for_exposure` 三种口径。
