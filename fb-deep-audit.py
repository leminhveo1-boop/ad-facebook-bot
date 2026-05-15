"""
Facebook Deep Campaign Analysis
================================
Phan tich sau toan bo campaigns dang ACTIVE:
- Ad-level breakdown (tung quang cao)
- Daily trend (7 ngay)
- Creative performance
- Messages/Lead cost
"""

import os, json, sys, io
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad
except ImportError:
    print("pip install facebook-business"); sys.exit(1)

try:
    from tabulate import tabulate
    HAS_TAB = True
except ImportError:
    HAS_TAB = False

# ── CONFIG ──────────────────────────────────────────────
ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "PASTE_TOKEN")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "act_XXXXXXXX")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")
APP_SECRET    = os.environ.get("FB_APP_SECRET", "")
DATE_PRESET   = "last_30d"
# ────────────────────────────────────────────────────────

def init():
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    print(f"[OK] API connected | Account: {AD_ACCOUNT_ID}")

def sep(title="", char="=", w=70):
    if title:
        pad = (w - len(title) - 2) // 2
        print(f"\n{char*pad} {title} {char*pad}")
    else:
        print(char * w)

def tbl(rows, title=""):
    if not rows:
        print(f"  (no data: {title})")
        return
    if HAS_TAB:
        print(tabulate(rows, headers="keys", tablefmt="rounded_outline"))
    else:
        for r in rows: print(r)

def fmt(n, unit=""):
    if n is None: return "-"
    try:
        n = float(n)
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M{unit}"
        if n >= 1_000:     return f"{n/1_000:.1f}K{unit}"
        return f"{n:.0f}{unit}"
    except: return str(n)

def action_val(actions, t):
    for a in (actions or []):
        if a.get("action_type") == t:
            return int(float(a.get("value", 0)))
    return 0

# ── 1. LAY DANH SACH ACTIVE CAMPAIGNS ───────────────────
def get_active_campaigns():
    account = AdAccount(AD_ACCOUNT_ID)
    fields = [
        Campaign.Field.id,
        Campaign.Field.name,
        Campaign.Field.status,
        Campaign.Field.effective_status,
        Campaign.Field.objective,
        Campaign.Field.daily_budget,
        Campaign.Field.budget_remaining,
        Campaign.Field.created_time,
        Campaign.Field.start_time,
    ]
    params = {"effective_status": ["ACTIVE"]}
    campaigns = account.get_campaigns(fields=fields, params=params)
    return list(campaigns)

# ── 2. INSIGHTS THEO CAMPAIGN (30 ngay) ──────────────────
def get_campaign_insights(campaign_id):
    c = Campaign(campaign_id)
    fields = [
        "spend", "impressions", "reach", "clicks", "unique_clicks",
        "ctr", "unique_ctr", "cpc", "cpm", "cpp", "frequency",
        "actions", "cost_per_action_type", "purchase_roas",
        "video_play_actions", "video_thruplay_watched_actions",
    ]
    params = {"date_preset": DATE_PRESET, "level": "campaign"}
    try:
        data = c.get_insights(fields=fields, params=params)
        return data[0] if data else {}
    except Exception as e:
        print(f"  [!] Insights error: {e}")
        return {}

# ── 3. DAILY TREND (7 ngay) ──────────────────────────────
def get_daily_trend(campaign_id, campaign_name):
    c = Campaign(campaign_id)
    fields = ["spend", "impressions", "clicks", "ctr", "cpm", "frequency", "actions"]
    params = {
        "date_preset": "last_7d",
        "time_increment": 1,
        "level": "campaign",
    }
    try:
        data = c.get_insights(fields=fields, params=params)
    except Exception as e:
        print(f"  [!] Daily trend error: {e}")
        return

    sep(f"Daily Trend: {campaign_name[:40]}", "-")
    rows = []
    for d in data:
        actions = d.get("actions", [])
        msgs = action_val(actions, "onsite_conversion.messaging_first_reply")
        leads = action_val(actions, "lead")
        rows.append({
            "Date":       d.get("date_start"),
            "Spend":      fmt(float(d.get("spend", 0)), "d"),
            "Impr":       fmt(d.get("impressions")),
            "Clicks":     d.get("clicks", 0),
            "CTR%":       round(float(d.get("ctr", 0)), 2),
            "CPM":        fmt(d.get("cpm")),
            "Freq":       round(float(d.get("frequency", 0)), 2),
            "Messages":   msgs,
            "Leads":      leads,
        })
    tbl(rows, "daily")

# ── 4. AD SETS CUA CAMPAIGN ───────────────────────────────
def get_adsets_of_campaign(campaign_id):
    c = Campaign(campaign_id)
    fields = [
        AdSet.Field.id,
        AdSet.Field.name,
        AdSet.Field.effective_status,
        AdSet.Field.daily_budget,
        AdSet.Field.optimization_goal,
        AdSet.Field.billing_event,
        AdSet.Field.targeting,
        AdSet.Field.bid_strategy,
    ]
    try:
        return list(c.get_ad_sets(fields=fields))
    except Exception as e:
        print(f"  [!] AdSet error: {e}")
        return []

# ── 5. ADS (CREATIVE LEVEL) ───────────────────────────────
def get_ads_of_campaign(campaign_id):
    c = Campaign(campaign_id)
    fields = [
        Ad.Field.id,
        Ad.Field.name,
        Ad.Field.effective_status,
        Ad.Field.creative,
        Ad.Field.adset_id,
    ]
    try:
        ads = list(c.get_ads(fields=fields))
    except Exception as e:
        print(f"  [!] Ads error: {e}")
        return []

    # Get insights for each ad
    insight_fields = [
        "ad_id", "ad_name", "spend", "impressions", "clicks",
        "ctr", "cpm", "frequency", "actions", "purchase_roas",
    ]
    insight_params = {
        "date_preset": DATE_PRESET,
        "level": "ad",
    }
    account = AdAccount(AD_ACCOUNT_ID)
    try:
        raw = account.get_insights(
            fields=insight_fields,
            params={**insight_params, "filtering": [{"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}]},
        )
    except Exception as e:
        print(f"  [!] Ad insights error: {e}")
        raw = []

    # Map insights by ad_id
    ad_stats = {}
    for r in raw:
        ad_stats[r.get("ad_id")] = r

    rows = []
    for ad in ads:
        ad_id = ad.get("id")
        stats = ad_stats.get(ad_id, {})
        actions = stats.get("actions", [])
        msgs  = action_val(actions, "onsite_conversion.messaging_first_reply")
        leads = action_val(actions, "lead")
        spend = float(stats.get("spend", 0))
        cpm   = float(stats.get("cpm", 0))
        freq  = float(stats.get("frequency", 0))
        ctr   = float(stats.get("ctr", 0))
        impr  = int(stats.get("impressions", 0) or 0)

        cost_per_msg = int(spend / msgs) if msgs > 0 else 0

        rows.append({
            "Ad Name":       ad.get("name", "")[:35],
            "Status":        ad.get("effective_status", ""),
            "Spend":         int(spend),
            "Impr":          impr,
            "CTR%":          round(ctr, 2),
            "CPM":           int(cpm),
            "Freq":          round(freq, 2),
            "Messages":      msgs,
            "Leads":         leads,
            "Cost/Msg":      cost_per_msg if cost_per_msg else "-",
            "Flag":          _flag_ad(spend, ctr, freq, msgs, leads),
        })

    # Sort by Spend desc
    rows.sort(key=lambda x: x["Spend"], reverse=True)
    return rows

def _flag_ad(spend, ctr, freq, msgs, leads):
    flags = []
    if freq > 3.5:      flags.append("FATIGUE")
    if ctr < 0.5 and spend > 50000: flags.append("LOW-CTR")
    if spend > 300000 and msgs == 0 and leads == 0: flags.append("NO-RESULT")
    if ctr > 5:         flags.append("HOT")
    if msgs > 50:       flags.append("TOP")
    return ",".join(flags) if flags else "OK"

# ── 6. TONG HOP SCORE CAMPAIGN ────────────────────────────
def score_campaign(insight):
    """Tinh diem hieu qua 0-100"""
    score = 0
    ctr   = float(insight.get("ctr", 0))
    freq  = float(insight.get("frequency", 0))
    cpm   = float(insight.get("cpm", 0))
    spend = float(insight.get("spend", 0))
    actions = insight.get("actions", [])
    msgs  = action_val(actions, "onsite_conversion.messaging_first_reply")
    leads = action_val(actions, "lead")
    roas_data = insight.get("purchase_roas", [])
    roas = float(roas_data[0]["value"]) if roas_data else 0

    # CTR (0-30 pts)
    if ctr >= 5:    score += 30
    elif ctr >= 3:  score += 22
    elif ctr >= 1:  score += 12
    elif ctr >= 0.5:score += 5

    # Frequency (0-20 pts) - thap tot hon
    if freq <= 1.5:   score += 20
    elif freq <= 2.5: score += 15
    elif freq <= 3.5: score += 8
    else:             score += 0

    # CPM (0-20 pts) - thap tot hon
    if cpm < 50000:     score += 20
    elif cpm < 80000:   score += 15
    elif cpm < 120000:  score += 8
    else:               score += 2

    # Results (0-30 pts)
    if spend > 0:
        result_total = msgs + leads
        cost_per = spend / result_total if result_total > 0 else 999999
        if cost_per < 20000:    score += 30
        elif cost_per < 50000:  score += 20
        elif cost_per < 100000: score += 10
        elif result_total > 0:  score += 5

    return min(score, 100)

def score_label(s):
    if s >= 80: return "EXCELLENT"
    if s >= 60: return "GOOD"
    if s >= 40: return "AVERAGE"
    if s >= 20: return "POOR"
    return "CRITICAL"

# ── MAIN ─────────────────────────────────────────────────
def main():
    sep("FACEBOOK DEEP CAMPAIGN ANALYSIS")
    print(f"Account : {AD_ACCOUNT_ID}")
    print(f"Period  : {DATE_PRESET}")
    print(f"Time    : {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    init()

    # Lay danh sach active campaigns
    campaigns = get_active_campaigns()
    print(f"\n[*] Found {len(campaigns)} ACTIVE campaigns\n")

    summary_rows = []
    full_report = []

    for camp in campaigns:
        cid   = camp.get("id")
        cname = camp.get("name", "")
        obj   = camp.get("objective", "")

        sep(f"CAMPAIGN: {cname[:50]}", "=")
        print(f"  ID        : {cid}")
        print(f"  Objective : {obj}")
        print(f"  Budget/d  : {int(camp.get('daily_budget', 0) or 0)//100} VND")

        # --- Insights tong hop ---
        insight = get_campaign_insights(cid)
        spend   = float(insight.get("spend", 0))
        impr    = int(insight.get("impressions", 0) or 0)
        clicks  = int(insight.get("clicks", 0) or 0)
        ctr     = float(insight.get("ctr", 0))
        freq    = float(insight.get("frequency", 0))
        cpm     = float(insight.get("cpm", 0))
        cpc     = float(insight.get("cpc", 0))
        actions = insight.get("actions", [])
        msgs    = action_val(actions, "onsite_conversion.messaging_first_reply")
        leads   = action_val(actions, "lead")
        roas_d  = insight.get("purchase_roas", [])
        roas    = float(roas_d[0]["value"]) if roas_d else 0

        cost_per_msg  = int(spend / msgs)  if msgs > 0  else "N/A"
        cost_per_lead = int(spend / leads) if leads > 0 else "N/A"
        sc = score_campaign(insight)

        print(f"\n  --- 30-DAY SUMMARY ---")
        print(f"  Spend      : {fmt(spend, 'd VND')}")
        print(f"  Impressions: {fmt(impr)}")
        print(f"  Clicks     : {fmt(clicks)}")
        print(f"  CTR        : {ctr:.2f}%")
        print(f"  CPM        : {fmt(cpm, 'd')}")
        print(f"  CPC        : {fmt(cpc, 'd')}")
        print(f"  Frequency  : {freq:.2f}")
        print(f"  Messages   : {msgs}  | Cost/Msg  : {fmt(cost_per_msg, 'd')}")
        print(f"  Leads      : {leads} | Cost/Lead : {fmt(cost_per_lead, 'd')}")
        print(f"  ROAS       : {roas:.2f}x")
        print(f"  SCORE      : {sc}/100  [{score_label(sc)}]")

        # --- Ad sets ---
        adsets = get_adsets_of_campaign(cid)
        if adsets:
            sep("Ad Sets", "-")
            adset_rows = []
            for ads in adsets:
                t = ads.get("targeting", {})
                geo = t.get("geo_locations", {}).get("countries", ["VN"])
                adset_rows.append({
                    "Name":    ads.get("name", "")[:30],
                    "Status":  ads.get("effective_status", ""),
                    "Budget":  int(int(ads.get("daily_budget", 0) or 0) / 100),
                    "Goal":    ads.get("optimization_goal", ""),
                    "Geo":     ",".join(geo),
                    "Age":     f"{t.get('age_min','?')}-{t.get('age_max','?')}",
                })
            tbl(adset_rows, "adsets")

        # --- Ad level ---
        sep("Ads (Creative Level)", "-")
        ad_rows = get_ads_of_campaign(cid)
        if ad_rows:
            tbl(ad_rows, "ads")
        else:
            print("  (No ad data)")

        # --- Daily trend ---
        get_daily_trend(cid, cname)

        # --- Summary row ---
        summary_rows.append({
            "Campaign":    cname[:35],
            "Score":       f"{sc}/100 [{score_label(sc)}]",
            "Spend":       int(spend),
            "CTR%":        round(ctr, 2),
            "Freq":        round(freq, 2),
            "CPM":         int(cpm),
            "Messages":    msgs,
            "Leads":       leads,
            "Cost/Msg":    cost_per_msg,
            "ROAS":        round(roas, 2),
        })

        full_report.append({
            "campaign_id": cid,
            "campaign_name": cname,
            "score": sc,
            "score_label": score_label(sc),
            "metrics": {
                "spend": spend, "impressions": impr, "clicks": clicks,
                "ctr": ctr, "cpm": cpm, "cpc": cpc, "frequency": freq,
                "messages": msgs, "leads": leads, "roas": roas,
                "cost_per_message": cost_per_msg,
                "cost_per_lead": cost_per_lead,
            }
        })

    # ── BANG TONG KET ──────────────────────────────────────
    sep("TONG KET — RANKING CAMPAIGNS", "=")
    summary_rows.sort(key=lambda x: int(x["Score"].split("/")[0]), reverse=True)
    tbl(summary_rows, "summary")

    # ── KHUYEN NGHI ────────────────────────────────────────
    sep("KHUYEN NGHI HANH DONG", "=")
    for r in summary_rows:
        sc_val = int(r["Score"].split("/")[0])
        name   = r["Campaign"]
        freq   = r["Freq"]
        ctr    = r["CTR%"]
        msgs   = r["Messages"]
        spend  = r["Spend"]

        print(f"\n[{r['Score']}] {name}")
        if sc_val >= 70:
            print("  => SCALE UP: Tang budget 20-30%, mo rong audience tuong tu")
        elif sc_val >= 50:
            if freq > 3.0:
                print("  => REFRESH CREATIVE: Audience met, doi creative moi")
            elif ctr < 1.0:
                print("  => TEST CREATIVE: CTR yeu, A/B test hook khac")
            else:
                print("  => GIU NGUYEN: Dang on, theo doi them 3-5 ngay")
        elif sc_val >= 30:
            if msgs == 0:
                print("  => XEM LAI OBJECTIVE: Khong co ket qua, cân stop va rebuild")
            else:
                print("  => OPTIMIZE: Giam budget, thu nghiem audience moi")
        else:
            print("  => STOP: Hieu qua kem, nen dung lai va phan tich nguyen nhan")

    # ── EXPORT ─────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"fb_deep_audit_{ts}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)
    print(f"\n[*] Full report saved: {fname}")
    sep("ANALYSIS COMPLETE")

if __name__ == "__main__":
    main()
