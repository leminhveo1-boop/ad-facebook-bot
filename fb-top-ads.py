"""
Top Ads Finder — Tim bai quang cao hieu qua nhat
=================================================
Pull tat ca ads dang ACTIVE, rank theo hieu qua thuc su.
"""
import os, sys, io, json
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from tabulate import tabulate

ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")
APP_SECRET    = os.environ.get("FB_APP_SECRET", "")
DATE_PRESET   = "last_30d"

def action_val(actions, t):
    for a in (actions or []):
        if a.get("action_type") == t:
            return int(float(a.get("value", 0)))
    return 0

def main():
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    print(f"\n[*] Pulling all ad-level insights | {DATE_PRESET}\n")

    account = AdAccount(AD_ACCOUNT_ID)

    # Pull insights at AD level for ALL active ads
    fields = [
        "ad_id", "ad_name",
        "campaign_name", "adset_name",
        "spend", "impressions", "reach",
        "clicks", "unique_clicks",
        "ctr", "unique_ctr",
        "cpc", "cpm", "frequency",
        "actions",
        "cost_per_action_type",
        "purchase_roas",
        "video_play_actions",
    ]
    params = {
        "date_preset": DATE_PRESET,
        "level": "ad",
        "filtering": [{"field": "ad.effective_status", "operator": "IN",
                        "value": ["ACTIVE", "PAUSED"]}],
        "limit": 100,
    }

    print("[*] Fetching data from Meta API...")
    raw = list(account.get_insights(fields=fields, params=params))
    print(f"[*] Got {len(raw)} ads with spend data\n")

    rows = []
    for r in raw:
        spend   = float(r.get("spend", 0))
        if spend < 10000:   # Bo qua ads chi tieu qua it
            continue

        impr    = int(r.get("impressions", 0) or 0)
        clicks  = int(r.get("clicks", 0) or 0)
        ctr     = float(r.get("ctr", 0))
        cpm     = float(r.get("cpm", 0))
        cpc     = float(r.get("cpc", 0))
        freq    = float(r.get("frequency", 0))
        actions = r.get("actions", [])

        msgs    = action_val(actions, "onsite_conversion.messaging_first_reply")
        leads   = action_val(actions, "lead")
        buys    = action_val(actions, "purchase")
        engages = action_val(actions, "post_engagement")

        result_total = msgs + leads + buys
        cost_per_result = int(spend / result_total) if result_total > 0 else 999999

        roas_d  = r.get("purchase_roas", [])
        roas    = float(roas_d[0]["value"]) if roas_d else 0

        # ── TINH DIEM HIEU QUA ──────────────────────────────
        score = 0

        # CTR score (0-35 pts)
        if ctr >= 6:    score += 35
        elif ctr >= 4:  score += 28
        elif ctr >= 2:  score += 18
        elif ctr >= 1:  score += 10
        elif ctr >= 0.5:score += 4

        # Cost per result score (0-40 pts)
        if result_total > 0:
            if cost_per_result < 10000:    score += 40
            elif cost_per_result < 20000:  score += 32
            elif cost_per_result < 40000:  score += 22
            elif cost_per_result < 80000:  score += 12
            else:                          score += 4
        # else 0 pts — no result = bad

        # Frequency score (0-15 pts) — thap = tot
        if freq <= 1.5:   score += 15
        elif freq <= 2.5: score += 10
        elif freq <= 3.5: score += 5

        # CPM score (0-10 pts) — thap = tot
        if cpm < 60000:     score += 10
        elif cpm < 90000:   score += 7
        elif cpm < 120000:  score += 4
        else:               score += 1

        # ── FLAGS ────────────────────────────────────────────
        flags = []
        if score >= 70:           flags.append("TOP-AD")
        if result_total == 0 and spend > 200000: flags.append("NO-RESULT")
        if freq > 3.5:            flags.append("FATIGUE")
        if ctr > 5:               flags.append("HOT-CTR")
        if cost_per_result < 15000 and result_total > 5: flags.append("CHEAP-WIN")
        flag_str = " | ".join(flags) if flags else "normal"

        rows.append({
            "score":          score,
            "Ad Name":        r.get("ad_name", "")[:32],
            "Campaign":       r.get("campaign_name", "")[:28],
            "Score":          score,
            "Spend":          int(spend),
            "CTR%":           round(ctr, 2),
            "CPM":            int(cpm),
            "Freq":           round(freq, 2),
            "Msgs":           msgs,
            "Leads":          leads,
            "Cost/Result":    cost_per_result if result_total > 0 else "N/A",
            "ROAS":           round(roas, 2) if roas else 0,
            "Flag":           flag_str,
        })

    # ── SORT & DISPLAY ───────────────────────────────────────
    rows.sort(key=lambda x: x["score"], reverse=True)

    # Xoa column score (dung cho sort, khong can hien)
    display_rows = [{k: v for k, v in r.items() if k != "score"} for r in rows]

    print("=" * 90)
    print(f"  TOP ADS RANKING — {DATE_PRESET}  |  {len(rows)} ads co spend")
    print("=" * 90)
    print(tabulate(display_rows, headers="keys", tablefmt="rounded_outline"))

    # ── TOP 3 WINNERS ────────────────────────────────────────
    winners = [r for r in rows if r["score"] >= 60]
    print(f"\n{'='*70}")
    print(f"  WINNERS ({len(winners)} ads dat hieu qua cao)")
    print(f"{'='*70}")
    for i, w in enumerate(winners[:5], 1):
        cost_r = w["Cost/Result"]
        cost_str = f"{int(cost_r):,}d" if isinstance(cost_r, (int, float)) else cost_r
        print(f"\n  #{i} [{w['Score']}/100] {w['Ad Name']}")
        print(f"      Campaign  : {w['Campaign']}")
        print(f"      Spend     : {w['Spend']:,}d  |  CTR: {w['CTR%']}%  |  Freq: {w['Freq']}")
        print(f"      Messages  : {w['Msgs']}  |  Leads: {w['Leads']}")
        print(f"      Cost/Result: {cost_str}  |  ROAS: {w['ROAS']}x")
        print(f"      Status    : {w['Flag']}")

    # ── LOSERS (can xem lai) ─────────────────────────────────
    losers = [r for r in rows if "NO-RESULT" in r["Flag"] or r["score"] < 30]
    if losers:
        print(f"\n{'='*70}")
        print(f"  CAN XEM LAI / DUNG ({len(losers)} ads)")
        print(f"{'='*70}")
        for w in losers:
            print(f"  [-] {w['Ad Name']} | Spend: {w['Spend']:,}d | CTR: {w['CTR%']}% | Flag: {w['Flag']}")

    # ── EXPORT ───────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"fb_top_ads_{ts}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[*] Saved: {fname}")
    print("=" * 90)

if __name__ == "__main__":
    main()
