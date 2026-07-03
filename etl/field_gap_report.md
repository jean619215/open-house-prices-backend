# 欄位落差清單：實價登錄來源 CSV vs transactions 表

> 產出日期：2026-06-22（最後更新：2026-06-22）
> 負責人：Backend Engineer
> 對應 TASK：TASK-002

---

## 一、來源 CSV 有、但 `transactions` 表沒有對應欄位

以下欄位存在於 實價登錄不動產買賣 CSV（`*_lvr_land_a.CSV`），目前 `transactions` 表**沒有對應欄位**，資料在本期 ETL 中被丟棄：

| 來源 CSV 欄位名稱 | 說明 |
|------------------|------|
| 交易標的 | 房地(土地+建物) / 房地(土地+建物+車位) 等分類 |
| 土地移轉總面積平方公尺 | 土地面積（非建物面積），與 `area_sqm` 不同 |
| 都市土地使用分區 | 住 / 商 / 工 等分區別 |
| 非都市土地使用分區 | 農業區 / 山坡地保育區等 |
| 非都市土地使用編定 | 甲種建築用地 / 乙種等 |
| 交易筆棟數 | 如「土地1建物1車位0」 |
| 總樓層數 | 該棟總樓層數（整數字串） |
| 主要用途 | 住家用 / 商業用 / 工業用等 |
| 主要建材 | 鋼筋混凝土 / 加強磚造等 |
| 建物現況格局-房 | 房間數 |
| 建物現況格局-廳 | 廳數 |
| 建物現況格局-衛 | 衛浴數 |
| 建物現況格局-隔間 | 隔間有/無 |
| 有無管理組織 | 有 / 無 |
| 車位移轉總面積平方公尺 | 車位面積 |
| 備註 | 文字備註欄 |
| 編號 | 內政部流水編號（非穩定唯一 key） |

---

## 二、`transactions` 表有、但來源 CSV 無法直接對應的欄位

| `transactions` 表欄位 | 說明 | 來源狀況 |
|----------------------|------|---------|
| `location` (PostGIS POINT) | 經緯度座標 | 來源無；需透過 geocoding API 另行取得。本期一律 NULL。 |
| `mrt_distance` (NUMERIC) | 距最近捷運站距離（公尺） | 來源無；需另計算。本期一律 NULL。 |
| `id` (BigInteger PK) | 自增主鍵 | DB 自動產生，無需來源。 |
| `created_at` (TIMESTAMP) | 寫入時間 | DB server_default，無需來源。 |

---

## 三、型別 / 單位不一致處（需 ETL 轉換）

| 欄位 | 來源格式 | 表欄位型別 | 轉換方式 | 備註 |
|------|---------|-----------|---------|------|
| `transaction_date` | 民國年 7 碼字串，如 `1130515` (YYYMMDD) | PostgreSQL `DATE` | ROC 年 + 1911 → 西元 DATE；`0000000` / 空值 → NULL | AC-05, AC-14 |
| `area_sqm` | 平方公尺（浮點字串）| `NUMERIC(8,2)`（平方公尺） | 直接儲存來源值，不做坪換算；坪換算為前端責任（坪 = m² ÷ 3.305785） | 欄位名與單位一致，已解決：決定存平方公尺，欄位名維持 |
| `price_per_sqm` | 元/平方公尺（整數字串） | `NUMERIC(12,2)`（元/平方公尺） | 直接儲存來源值，不做坪換算；坪換算為前端責任（元/坪 = 元/m² × 3.305785） | 欄位名與單位一致，已解決：決定存平方公尺，欄位名維持 |
| `building_age` | 建築完成年月（民國 7 碼字串） | `SMALLINT`（整數年） | 西元匯入年 − (ROC 年 + 1911)；只取整數年、不計月份；負數 → NULL | AC-09 |
| `has_parking` | 車位類別（字串）+ 車位總價（字串） | `BOOLEAN / NULL` | 三態邏輯：有車位=TRUE、明確無=FALSE、無法判斷=NULL | AC-10, AC-18 |
| `floor` | 移轉層次，如「三層」「全」「地下一層」 | `VARCHAR(10)` | 保留原始字串，不轉數字 | AC-08 |
| `building_type` | 建物型態（字串），如「公寓(5樓含以下無電梯)」 | `TEXT`（無長度限制） | 直接對應，已解決：改 TEXT（migration 002）| 已修正截斷風險 |

---

## 四、潛在議題（供後續 TASK 討論）

1. **`area_sqm` / `price_per_sqm` 欄位命名誤導** — **已解決（2026-06-22，決策 1）**：
   需求方決定 DB 直接存平方公尺原始值，不做坪換算；坪換算為前端責任（坪 = m² ÷ 3.305785）。
   欄位名 `area_sqm` / `price_per_sqm` 現已名實相符，維持不改名。此議題結案。

2. **`building_type` VARCHAR(20) 可能截斷** — **已解決（2026-06-22，決策 2）**：
   需求方選擇改為 `TEXT`（無長度限制）。已在 `shared/models.py` 更新欄位型別，並新增
   Alembic migration `002_building_type_to_text`（`ALTER COLUMN building_type TYPE TEXT`）。
   此議題結案。

3. **`floor` VARCHAR(10) 邊界**：目前已評估實價登錄常見值（見 TASK-001 歷程），VARCHAR(10) 足夠，但仍應在 ETL 監控截斷警告。

4. **冪等鍵設計（效能優化，待後續 TASK）**：本期採用組合鍵 `(address, transaction_date, floor, area_sqm, price_total)` 逐列 SELECT 查重，效能較低。
   後續待辦：為去重鍵 `(address, transaction_date, floor, area_sqm, price_total)` 建 DB unique index，
   並改用 `INSERT ... ON CONFLICT DO NOTHING` 提升批次寫入效率。
   觸發時機：要做全台匯入、歷史回補、或排程自動跑時必須處理。

5. **來源無穩定 unique key**：內政部「編號」欄位並非跨期穩定 ID，不可作為去重鍵。本期設計已考量此點。
