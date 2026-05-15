"""
Facebook Campaign Audit Tool
============================
Dùng Meta Marketing API de audit toan bo chien dich quang cao.
Yeu cau: Token co quyen ads_read + ads_management

Cài đặt: pip install facebook-business pandas tabulate
"""

import os
import json
import sys
import io

# Fix Windows terminal encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from datetime import datetime

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad
except ImportError:
    print("❌ Chưa cài SDK. Chạy: pip install facebook-business")
    sys.exit(1)

try:
    import pandas as pd
    from tabulate import tabulate
    HAS_DISPLAY = True
except ImportError:
    HAS_DISPLAY = False

# ============================================================
# CONFIGURATION — Cập nhật token mới vào đây
# ============================================================
ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "PASTE_TOKEN_MỚI_VÀO_ĐÂY")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "act_XXXXXXXXXX")  # Dạng: act_1234567890
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")
APP_SECRET    = os.environ.get("FB_APP_SECRET", "")

# Khoảng thời gian audit
DATE_PRESET = "last_30d"   # Có thể đổi: last_7d, last_14d, last_30d, last_90d, this_month

# ============================================================
# INIT API
# ============================================================
def init_api():
    try:
        FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
        print(f"✅ Kết nối API thành công — App ID: {APP_ID}")
    except Exception as e:
        print(f"❌ Lỗi kết nối API: {e}")
        sys.exit(1)


# ============================================================
# 1. KIỂM TRA TÀI KHOẢN QUẢNG CÁO
# ============================================================
def audit_account(account_id: str) -> dict:
    print(f"\n{'='*60}")
    print(f"🔍 AUDIT AD ACCOUNT: {account_id}")
    print(f"{'='*60}")

    account = AdAccount(account_id)
    fields = [
        AdAccount.Field.name,
        AdAccount.Field.account_status,
        AdAccount.Field.currency,
        AdAccount.Field.spend_cap,
        AdAccount.Field.amount_spent,
        AdAccount.Field.balance,
        AdAccount.Field.timezone_name,
        AdAccount.Field.business,
    ]
    data = account.api_get(fields=fields)
    
    STATUS_MAP = {1: "✅ ACTIVE", 2: "❌ DISABLED", 3: "⚠️ UNSETTLED",
                  7: "🔴 PENDING_REVIEW", 9: "🔒 IN_GRACE_PERIOD", 101: "🚫 CLOSED"}
    status = STATUS_MAP.get(data.get("account_status"), "❓ UNKNOWN")
    
    print(f"  Tên:          {data.get('name')}")
    print(f"  Trạng thái:   {status}")
    print(f"  Tiền tệ:      {data.get('currency')}")
    print(f"  Đã tiêu:      {float(data.get('amount_spent', 0))/100:.2f} {data.get('currency')}")
    print(f"  Múi giờ:      {data.get('timezone_name')}")
    return data


# ============================================================
# 2. AUDIT CAMPAIGNS
# ============================================================
def audit_campaigns(account_id: str) -> list:
    print(f"\n{'='*60}")
    print(f"📊 CAMPAIGNS — {DATE_PRESET}")
    print(f"{'='*60}")

    account = AdAccount(account_id)
    fields = [
        Campaign.Field.name,
        Campaign.Field.status,
        Campaign.Field.objective,
        Campaign.Field.effective_status,
        Campaign.Field.budget_remaining,
        Campaign.Field.daily_budget,
        Campaign.Field.lifetime_budget,
        Campaign.Field.start_time,
        Campaign.Field.stop_time,
    ]
    campaigns = account.get_campaigns(fields=fields)

    rows = []
    for c in campaigns:
        rows.append({
            "ID":       c.get("id"),
            "Name":     c.get("name", "")[:40],
            "Status":   c.get("effective_status"),
            "Objective":c.get("objective"),
            "Budget/d": _fmt_budget_raw(c.get("daily_budget")),
            "Remaining":_fmt_budget_raw(c.get("budget_remaining")),
        })

    _print_table(rows, "Campaigns")
    print(f"\n  [*] Total: {len(rows)} campaigns | Active: {sum(1 for r in rows if r['Status']=='ACTIVE')}")
    return rows


# ============================================================
# 3. AUDIT INSIGHTS (PERFORMANCE)
# ============================================================
def audit_insights(account_id: str) -> list:
    print(f"\n{'='*60}")
    print(f"📈 PERFORMANCE INSIGHTS — {DATE_PRESET}")
    print(f"{'='*60}")

    account = AdAccount(account_id)
    fields = [
        "campaign_name",
        "spend",
        "impressions",
        "reach",
        "clicks",
        "ctr",
        "cpc",
        "cpm",
        "cpp",
        "frequency",
        "actions",           # conversions, leads, messages...
        "cost_per_action_type",
        "purchase_roas",
    ]
    params = {
        "date_preset": DATE_PRESET,
        "level": "campaign",
        "limit": 50,
    }
    insights = account.get_insights(fields=fields, params=params)

    rows = []
    flags = []  # Cờ cảnh báo

    for insight in insights:
        spend  = float(insight.get("spend", 0))
        impr   = int(insight.get("impressions", 0))
        clicks = int(insight.get("clicks", 0))
        ctr    = float(insight.get("ctr", 0))
        cpc    = float(insight.get("cpc", 0))
        freq   = float(insight.get("frequency", 0))
        cpm    = float(insight.get("cpm", 0))
        name   = insight.get("campaign_name", "")[:35]

        # Phân tích leads/messages/purchases
        actions = insight.get("actions", [])
        leads = _get_action_value(actions, "lead")
        msgs  = _get_action_value(actions, "onsite_conversion.messaging_first_reply")
        buys  = _get_action_value(actions, "purchase")

        # ROAS
        roas_data = insight.get("purchase_roas", [])
        roas = float(roas_data[0]["value"]) if roas_data else 0

        row = {
            "Campaign":   name,
            "Spend(VND)": int(spend),
            "Impressions":impr,
            "Clicks":     clicks,
            "CTR%":       round(ctr, 2),
            "CPC":        int(cpc),
            "Frequency":  round(freq, 2),
            "CPM":        int(cpm),
            "Leads":      leads,
            "Messages":   msgs,
            "Purchases":  buys,
            "ROAS":       round(roas, 2) if roas else 0,
        }
        rows.append(row)

        # ⚠️ FLAGS — Cảnh báo
        w = []
        if freq > 3.5:
            w.append(f"[FATIGUE] Freq={freq:.1f} > 3.5")
        if ctr < 0.5 and spend > 100000:
            w.append(f"[LOW-CTR] CTR={ctr:.2f}%")
        if spend > 500000 and leads == 0 and buys == 0:
            w.append(f"[NO-RESULT] Spend cao, 0 conversion")
        if cpm > 150000:
            w.append(f"[HIGH-CPM] CPM={int(cpm)}")
        if w:
            flags.append({"Campaign": name, "Cảnh báo": " | ".join(w)})

    _print_table(rows, "Insights")

    if flags:
        print(f"\n{'='*60}")
        print("⚠️  CẢNH BÁO — CẦN XEM LẠI")
        print(f"{'='*60}")
        _print_table(flags, "Flags")

    return rows


# ============================================================
# 4. AUDIT AD SETS
# ============================================================
def audit_adsets(account_id: str) -> list:
    print(f"\n{'='*60}")
    print(f"🎯 AD SETS — Kiểm tra cấu trúc")
    print(f"{'='*60}")

    account = AdAccount(account_id)
    fields = [
        AdSet.Field.name,
        AdSet.Field.status,
        AdSet.Field.effective_status,
        AdSet.Field.daily_budget,
        AdSet.Field.billing_event,
        AdSet.Field.optimization_goal,
        AdSet.Field.targeting,
        AdSet.Field.campaign_id,
    ]
    adsets = account.get_ad_sets(fields=fields)

    rows = []
    for ads in adsets:
        targeting = ads.get("targeting", {})
        geo = targeting.get("geo_locations", {}).get("countries", ["N/A"])
        age_min = targeting.get("age_min", "N/A")
        age_max = targeting.get("age_max", "N/A")

        rows.append({
            "Ad Set Name":  ads.get("name", "")[:35],
            "Status":       ads.get("effective_status"),
            "Budget/d":     _fmt_budget_raw(ads.get("daily_budget")),
            "Billing":      ads.get("billing_event"),
            "Goal":         ads.get("optimization_goal"),
            "Geo":          ",".join(geo),
            "Age":          f"{age_min}-{age_max}",
        })

    _print_table(rows, "Ad Sets")
    print(f"\n  📌 Tổng: {len(rows)} ad sets")
    return rows


# ============================================================
# 5. EXPORT REPORT
# ============================================================
def export_report(account_id: str, insights: list, campaigns: list):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"fb_audit_{account_id.replace('act_','')}_{timestamp}.json"
    
    report = {
        "audit_date": datetime.now().isoformat(),
        "account_id": account_id,
        "date_preset": DATE_PRESET,
        "campaigns_count": len(campaigns),
        "insights": insights,
        "campaigns": campaigns,
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Report đã lưu: {filename}")


# ============================================================
# HELPERS
# ============================================================
def _fmt_budget(val):
    if val is None: return "-"
    return f"{int(val)/100:,.0f}"

def _fmt_budget_raw(val):
    """Return plain int (no commas) for tabulate compatibility."""
    if val is None: return 0
    return int(int(val)/100)

def _get_action_value(actions: list, action_type: str) -> int:
    for a in actions:
        if a.get("action_type") == action_type:
            return int(float(a.get("value", 0)))
    return 0

def _print_table(rows: list, title: str):
    if not rows:
        print(f"  (Không có dữ liệu {title})")
        return
    if HAS_DISPLAY:
        print(tabulate(rows, headers="keys", tablefmt="rounded_outline", maxcolwidths=40))
    else:
        for r in rows:
            print(r)


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n🚀 FACEBOOK CAMPAIGN AUDIT TOOL")
    print(f"   Account: {AD_ACCOUNT_ID}")
    print(f"   Period:  {DATE_PRESET}")
    print(f"   Time:    {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if "PASTE_TOKEN" in ACCESS_TOKEN:
        print("\n❌ CHƯA CÀI TOKEN! Mở file và paste token mới vào ACCESS_TOKEN")
        print("   Hoặc set env: set FB_ACCESS_TOKEN=your_token")
        sys.exit(1)

    if "XXXXXXXXXX" in AD_ACCOUNT_ID:
        print("\n❌ CHƯA CÀI AD ACCOUNT ID!")
        print("   Tìm trong Business Manager > Ad Accounts > ID có dạng: act_123456789")
        sys.exit(1)

    init_api()
    audit_account(AD_ACCOUNT_ID)
    campaigns = audit_campaigns(AD_ACCOUNT_ID)
    insights  = audit_insights(AD_ACCOUNT_ID)
    audit_adsets(AD_ACCOUNT_ID)
    export_report(AD_ACCOUNT_ID, insights, campaigns)

    print(f"\n{'='*60}")
    print("✅ AUDIT HOÀN THÀNH")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
