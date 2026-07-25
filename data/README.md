# Data layout

- `raw/`：BTS 官方原始 ZIP，只下载、不手工修改。
- `processed/`：P0 脚本生成的 Parquet、CSV 与 JSON。

大文件被 `.gitignore` 排除。报告会记录原始下载 URL、文件大小和 SHA-256，确保别人能验证拿到的是同一份数据。

