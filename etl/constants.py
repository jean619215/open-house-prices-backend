"""Constants used across the ETL pipeline.

Note:
    DB stores area in square metres (m²) and unit price in TWD/m² — raw values
    from the MOI source.  Conversion to ping (坪) is the frontend's responsibility:
        坪 = 平方公尺 ÷ 3.305785

"""

# 支援的縣市清單（台北市=A, 新北市=F）
TARGET_CITIES: dict[str, str] = {
    "A": "台北市",
    "F": "新北市",
}

# 內政部實價登錄整批下載 API base URL（不動產買賣）
# ref: https://plvr.land.moi.gov.tw/DownloadOpenData
MOI_DOWNLOAD_BASE_URL: str = (
    "https://plvr.land.moi.gov.tw/DownloadOpenData?type=zip&fileName={city_code}_lvr_land_a.zip"
)

# 車位類別：這些值代表「無車位」
PARKING_TYPE_NONE_VALUES: frozenset[str] = frozenset({"無", ""})

# 交易年月日：代表日期不詳的特殊值
UNKNOWN_DATE_VALUE: str = "0000000"
