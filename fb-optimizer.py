"""
Facebook Campaign Optimizer
============================
Tu dong toi uu dua tren ket qua audit:
  - PAUSE ads khong hieu qua (0 ket qua, chi phi cao)
  - SCALE UP budget cho campaigns/adsets dang win
  - PAUSE campaigns kem hieu qua

Chay DRY RUN truoc (xem ke hoach), sau moi thuc thi.
"""
import os, sys, io, json, time
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")
APP_SECRET    = os.environ.get("FB_APP_SECRET", "")
DATE_PRESET   = "last_30d"

# ── NGUONG QUYET DINH ────────────────────────────────────
# Note: Meta API tra ve budget theo don vi VND (khong nhan them)
# Nguong spend de quyet dinh (don vi: VND thuc)
PAUSE_AD_MIN_SPEND         = 30_000     # VND - Can toi thieu de co du data
PAUSE_AD_IF_RESULT_BELOW   = 1          # Ket qua < 1 -> PAUSE
SCALE_CAMPAIGN_THRESHOLD   = 60         # Score >= nay -> scale up budget
SCALE_BUDGET_PCT           = 30         # Tang bao nhieu % (30 = +30%)
# ────────────────────────────────────────────────────────

def sep(t="", w=68):
    if t: print(f"\n{'='*((w-len(t)-2)//2)} {t} {'='*((w-len(t)-2)//2)}")
    else: print("=" * w)

def action_val(actions, t):
    for a in (actions or []):
        if a.get("action_type") == t:
            return int(float(a.get("value", 0)))
    return 0

def score_ad(spend, ctr, freq, msgs, leads):
    buys = 0
    score = 0
    # CTR
    if ctr >= 6:    score += 35
    elif ctr >= 4:  score += 28
    elif ctr >= 2:  score += 18
    elif ctr >= 1:  score += 10
    elif ctr >= 0.5:score += 4
    # Results
    result = msgs + leads + buys
    if result > 0 and spend > 0:
        cpp = spend / result
        if cpp < 10000:    score += 40
        elif cpp < 20000:  score += 32
        elif cpp < 40000:  score += 22
        elif cpp < 80000:  score += 12
        else:              score += 4
    # Freq
    if freq <= 1.5:   score += 15
    elif freq <= 2.5: score += 10
    elif freq <= 3.5: score += 5
    return score

def score_campaign(ctr, freq, cpm, spend, msgs, leads):
    score = 0
    if ctr >= 5:    score += 30
    elif ctr >= 3:  score += 22
    elif ctr >= 1:  score += 12
    elif ctr >= 0.5:score += 5
    if freq <= 1.5:   score += 20
    elif freq <= 2.5: score += 15
    elif freq <= 3.5: score += 8
    if cpm < 50000:     score += 20
    elif cpm < 80000:   score += 15
    elif cpm < 120000:  score += 8
    else:               score += 2
    result = msgs + leads
    if spend > 0 and result > 0:
        cpp = spend / result
        if cpp < 20000:    score += 30
        elif cpp < 50000:  score += 20
        elif cpp < 100000: score += 10
        else:              score += 5
    return min(score, 100)

# ── FETCH DATA ────────────────────────────────────────────
def fetch_all_data():
    account = AdAccount(AD_ACCOUNT_ID)

    # Ad level insights
    ad_fields = [
        "ad_id", "ad_name", "campaign_id", "campaign_name",
        "adset_id", "adset_name",
        "spend", "impressions", "clicks", "ctr", "cpm", "frequency",
        "actions", "purchase_roas",
    ]
    ad_params = {
        "date_preset": DATE_PRESET,
        "level": "ad",
        "limit": 200,
    }
    ad_insights = {r.get("ad_id"): r for r in account.get_insights(fields=ad_fields, params=ad_params)}

    # Campaign level insights
    camp_fields = [
        "campaign_id", "campaign_name",
        "spend", "impressions", "clicks", "ctr", "cpm", "frequency",
        "actions", "purchase_roas",
    ]
    camp_params = {
        "date_preset": DATE_PRESET,
        "level": "campaign",
        "limit": 50,
    }
    camp_insights = {r.get("campaign_id"): r for r in account.get_insights(fields=camp_fields, params=camp_params)}

    # Active campaigns
    campaigns = list(account.get_campaigns(fields=[
        Campaign.Field.id, Campaign.Field.name,
        Campaign.Field.effective_status, Campaign.Field.daily_budget,
        Campaign.Field.budget_remaining,
    ]))

    # All ad sets
    adsets = list(account.get_ad_sets(fields=[
        AdSet.Field.id, AdSet.Field.name, AdSet.Field.campaign_id,
        AdSet.Field.effective_status, AdSet.Field.daily_budget,
    ]))

    # All ads
    ads = list(account.get_ads(fields=[
        Ad.Field.id, Ad.Field.name, Ad.Field.campaign_id,
        Ad.Field.adset_id, Ad.Field.effective_status,
    ]))

    return campaigns, adsets, ads, ad_insights, camp_insights

# ── XAY DUNG KE HOACH TOI UU ─────────────────────────────
def build_plan(campaigns, adsets, ads, ad_insights, camp_insights):
    actions_plan = []

    # ── 1. PAUSE ADS KHONG HIEU QUA ──────────────────────
    print("\n[*] Analyzing ads...")
    for ad in ads:
        ad_id     = ad.get("id")
        ad_name   = ad.get("name", "")
        ad_status = ad.get("effective_status", "")
        if ad_status in ("PAUSED", "ADSET_PAUSED", "CAMPAIGN_PAUSED", "DELETED"):
            continue  # Bo qua ads da dung

        data  = ad_insights.get(ad_id, {})
        spend = float(data.get("spend", 0))
        if spend < PAUSE_AD_MIN_SPEND:
            continue  # Chua du data

        actions   = data.get("actions", [])
        msgs      = action_val(actions, "onsite_conversion.messaging_first_reply")
        leads     = action_val(actions, "lead")
        buys      = action_val(actions, "purchase")
        result    = msgs + leads + buys
        ctr       = float(data.get("ctr", 0))
        freq      = float(data.get("frequency", 0))
        sc        = score_ad(spend, ctr, freq, msgs, leads)

        if result < PAUSE_AD_IF_RESULT_BELOW:
            actions_plan.append({
                "type":   "PAUSE_AD",
                "id":     ad_id,
                "name":   ad_name[:50],
                "reason": f"Spend {spend:,.0f}d | 0 ket qua | CTR {ctr:.2f}% | Score {sc}/100",
                "score":  sc,
            })

    # ── 2. SCALE UP CAMPAIGNS DANG WIN ───────────────────
    print("[*] Analyzing campaigns...")
    for camp in campaigns:
        cid    = camp.get("id")
        cname  = camp.get("name", "")
        status = camp.get("effective_status", "")
        if status != "ACTIVE":
            continue

        data   = camp_insights.get(cid, {})
        spend  = float(data.get("spend", 0))
        if spend < 500_000:
            continue

        actions= data.get("actions", [])
        msgs   = action_val(actions, "onsite_conversion.messaging_first_reply")
        leads  = action_val(actions, "lead")
        ctr    = float(data.get("ctr", 0))
        cpm    = float(data.get("cpm", 0))
        freq   = float(data.get("frequency", 0))
        sc     = score_campaign(ctr, freq, cpm, spend, msgs, leads)
        roas_d = data.get("purchase_roas", [])
        roas   = float(roas_d[0]["value"]) if roas_d else 0

        # Campaign budget raw (Meta VND: raw = actual VND)
        raw_budget = int(camp.get("daily_budget") or 0)

        if sc >= SCALE_CAMPAIGN_THRESHOLD and raw_budget > 0:
            new_budget = int(raw_budget * (1 + SCALE_BUDGET_PCT / 100))
            actions_plan.append({
                "type":       "SCALE_CAMPAIGN",
                "id":         cid,
                "name":       cname[:50],
                "reason":     f"Score {sc}/100 | CTR {ctr:.2f}% | {msgs} msgs | ROAS {roas:.2f}x",
                "old_budget": raw_budget,
                "new_budget": new_budget,
                "score":      sc,
            })
        elif sc < 30 and spend > 1_000_000:
            actions_plan.append({
                "type":   "PAUSE_CAMPAIGN",
                "id":     cid,
                "name":   cname[:50],
                "reason": f"Score {sc}/100 | Spend {spend:,.0f}d | Chi {msgs} msgs",
                "score":  sc,
            })

    # ── 3. SCALE AD SETS CUA WINNER (neu campaign khong co budget) ──
    print("[*] Analyzing ad sets...")
    # Map campaign id -> score
    camp_scores = {}
    for camp in campaigns:
        cid   = camp.get("id")
        data  = camp_insights.get(cid, {})
        spend = float(data.get("spend", 0))
        if spend < 500000:
            continue
        actions = data.get("actions", [])
        msgs    = action_val(actions, "onsite_conversion.messaging_first_reply")
        leads   = action_val(actions, "lead")
        ctr     = float(data.get("ctr", 0))
        cpm     = float(data.get("cpm", 0))
        freq    = float(data.get("frequency", 0))
        camp_scores[cid] = score_campaign(ctr, freq, cpm, spend, msgs, leads)

    for ads_obj in adsets:
        ads_id     = ads_obj.get("id")
        ads_name   = ads_obj.get("name", "")
        ads_status = ads_obj.get("effective_status", "")
        camp_id    = ads_obj.get("campaign_id")
        raw_budget = int(ads_obj.get("daily_budget") or 0)

        if ads_status != "ACTIVE" or raw_budget <= 0:
            continue

        sc = camp_scores.get(camp_id, 0)
        camp_has_budget = any(
            c.get("id") == camp_id and int(c.get("daily_budget") or 0) > 0
            for c in campaigns
        )
        if camp_has_budget:
            continue

        if sc >= SCALE_CAMPAIGN_THRESHOLD:
            new_budget = int(raw_budget * (1 + SCALE_BUDGET_PCT / 100))
            actions_plan.append({
                "type":       "SCALE_ADSET",
                "id":         ads_id,
                "name":       ads_name[:50],
                "camp_name":  next((c.get("name","") for c in campaigns if c.get("id")==camp_id), ""),
                "reason":     f"Parent campaign score {sc}/100",
                "old_budget": raw_budget,
                "new_budget": new_budget,
                "score":      sc,
            })

    return actions_plan

# ── IN KE HOACH ───────────────────────────────────────────
def print_plan(plan):
    sep("KE HOACH TOI UU — DRY RUN")
    if not plan:
        print("\n  Khong co thay doi nao duoc de xuat.")
        print("  Tat ca campaigns dang o trang thai on dinh.")
        return

    pauses   = [a for a in plan if a["type"] in ("PAUSE_AD", "PAUSE_CAMPAIGN")]
    scales   = [a for a in plan if a["type"] in ("SCALE_CAMPAIGN", "SCALE_ADSET")]

    if pauses:
        print(f"\n  [PAUSE — {len(pauses)} doi tuong] Dung cac quang cao kem hieu qua:")
        for i, a in enumerate(pauses, 1):
            t = "Ad" if a["type"] == "PAUSE_AD" else "Campaign"
            print(f"\n    {i}. [{t}] {a['name']}")
            print(f"       Ly do  : {a['reason']}")

    if scales:
        print(f"\n  [SCALE UP — {len(scales)} doi tuong] Tang budget cho winners:")
        for i, a in enumerate(scales, 1):
            t = "Campaign" if a["type"] == "SCALE_CAMPAIGN" else "Ad Set"
            old_b = a['old_budget']
            new_b = a['new_budget']
            diff  = new_b - old_b
            print(f"\n    {i}. [{t}] {a['name']}")
            if a["type"] == "SCALE_ADSET":
                print(f"       Campaign: {a.get('camp_name', '')}")
            print(f"       Ly do   : {a['reason']}")
            print(f"       Budget  : {old_b:,} -> {new_b:,} VND/ngay (+{diff:,})  (+{SCALE_BUDGET_PCT}%)")

    sep()
    print(f"\n  Tong: {len(pauses)} dung | {len(scales)} tang budget")
    print(f"  Du kien tiet kiem / ngay: xem xet {len(pauses)} quang cao lang phi")

# ── THUC THI ─────────────────────────────────────────────
def execute_plan(plan):
    log = []
    errors = []

    for action in plan:
        t = action["type"]
        try:
            if t == "PAUSE_AD":
                ad = Ad(action["id"])
                ad.api_update(params={"status": "PAUSED"})
                log.append(f"[OK] PAUSED Ad: {action['name']}")
                print(f"  [OK] Paused ad : {action['name'][:45]}")

            elif t == "PAUSE_CAMPAIGN":
                c = Campaign(action["id"])
                c.api_update(params={"status": "PAUSED"})
                log.append(f"[OK] PAUSED Campaign: {action['name']}")
                print(f"  [OK] Paused campaign: {action['name'][:45]}")

            elif t == "SCALE_CAMPAIGN":
                c = Campaign(action["id"])
                c.api_update(params={"daily_budget": str(action["new_budget"])})
                log.append(f"[OK] SCALED Campaign: {action['name']} -> {action['new_budget']//100:,} VND")
                print(f"  [OK] Scaled campaign: {action['name'][:35]} | Budget +{SCALE_BUDGET_PCT}%")

            elif t == "SCALE_ADSET":
                ads = AdSet(action["id"])
                ads.api_update(params={"daily_budget": str(action["new_budget"])})
                log.append(f"[OK] SCALED AdSet: {action['name']} -> {action['new_budget']//100:,} VND")
                print(f"  [OK] Scaled ad set : {action['name'][:35]} | Budget +{SCALE_BUDGET_PCT}%")

            time.sleep(0.3)  # rate limit

        except Exception as e:
            err = f"[ERR] {t} | {action['name']}: {e}"
            errors.append(err)
            print(f"  {err}")

    return log, errors

# ── MAIN ─────────────────────────────────────────────────
def main():
    dry_run = "--execute" not in sys.argv

    sep("FACEBOOK CAMPAIGN OPTIMIZER")
    print(f"  Account : {AD_ACCOUNT_ID}")
    print(f"  Period  : {DATE_PRESET}")
    print(f"  Mode    : {'*** DRY RUN (xem ke hoach) ***' if dry_run else '!!! THUC THI - DANG THAY DOI THAT !!!'}")
    print(f"  Time    : {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    print("\n[OK] API connected")

    print("\n[*] Fetching all campaign data...")
    campaigns, adsets, ads, ad_insights, camp_insights = fetch_all_data()
    print(f"[*] Found: {len(campaigns)} campaigns | {len(adsets)} adsets | {len(ads)} ads")

    # Xay dung ke hoach
    plan = build_plan(campaigns, adsets, ads, ad_insights, camp_insights)

    # In ke hoach
    print_plan(plan)

    if not plan:
        return

    if dry_run:
        print("\n" + "="*68)
        print("  DE THUC THI, CHAY LAI VOI THAM SO --execute:")
        print()
        print(f"  $env:FB_ACCESS_TOKEN = \"...\"; $env:FB_AD_ACCOUNT_ID = \"{AD_ACCOUNT_ID}\"")
        print(f"  python fb-optimizer.py --execute")
        print("="*68 + "\n")
    else:
        sep("DANG THUC THI CAC THAY DOI")
        log, errors = execute_plan(plan)

        # Luu log
        ts    = datetime.now().strftime("%Y%m%d_%H%M")
        fname = f"fb_optimize_log_{ts}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "account": AD_ACCOUNT_ID,
                "plan": plan,
                "executed": log,
                "errors": errors,
            }, f, ensure_ascii=False, indent=2)

        sep("KET QUA")
        print(f"\n  [*] Thanh cong : {len(log)} hanh dong")
        print(f"  [*] Loi        : {len(errors)} hanh dong")
        print(f"  [*] Log luu tai: {fname}")

        if errors:
            print("\n  Cac loi:")
            for e in errors:
                print(f"    {e}")

if __name__ == "__main__":
    main()
