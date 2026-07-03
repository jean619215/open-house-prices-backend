---
name: project-moi-download-pattern
description: MOI 實價登錄 bulk download URL pattern and zip extraction approach used in TASK-002
metadata:
  type: project
---

The MOI bulk download endpoint returns a ZIP file, not a direct CSV:

```
https://plvr.land.moi.gov.tw/DownloadOpenData?type=zip&fileName={city_code}_lvr_land_a.zip
```

City codes: A = 台北市, F = 新北市 (see `etl/constants.py` TARGET_CITIES).

Inside the zip, the 不動產買賣 file is named `{city_code_lower}_lvr_land_a.CSV` (uppercase `.CSV` extension). Extraction uses case-insensitive suffix matching.

CSV encoding: UTF-8 with BOM (`utf-8-sig`). Use `csv.DictReader` on `io.StringIO`.

**Why:** The API returns zip, not raw CSV — this is easy to miss and causes silent failures if you try to parse the zip bytes directly as CSV.

**How to apply:** Always decode zip → extract CSV member → decode with `utf-8-sig` before passing to parser.
