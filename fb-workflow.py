"""
Facebook Ads Auto-Workflow
==========================
Chay toan bo pipeline tu dong moi 3 ngay:
  1. Audit toan bo tai khoan
  2. Tim top ads dang hieu qua nhat
  3. Toi uu: pause ads kem, scale up budget winners
  4. Gui bao cao tom tat ra file

Log tat ca ket qua vao: logs/fb_workflow_YYYYMMDD.txt
"""
import os, sys, io, json, time, subprocess, traceback
from datetime import datetime
from pathlib import Path

# ── SETUP STDOUT ─────────────────────────────────────────
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── PATHS ─────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
LOG_DIR     = SCRIPT_DIR / "logs"
REPORT_DIR  = SCRIPT_DIR / "reports"
LOG_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# ── CONFIG TU BIEN MOI TRUONG ─────────────────────────────
ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")

# ── NGUONG TOI UU — THEO SOP QUAN JEAN NU ────────────
# Gia SP: 500k-700k | BE-ROAS: 2.5x | Nguong co loi: >= 5.0x
# Nguon: SOP_Quang_Cao_Quan_Jean_Nu.md (data TK02 thuc te)

PAUSE_AD_MIN_SPEND       = 100_000  # VND - Can >= 100k de co du data quyet dinh
PAUSE_ROAS_BELOW         = 3.0      # ROAS < 3x = lo (BE=2.5x, nguong an toan=3x) -> PAUSE
SCALE_ROAS_GOOD          = 5.0      # ROAS >= 5x (DAT) -> Scale +20%
SCALE_ROAS_EXCELLENT     = 7.0      # ROAS >= 7x (XUAT SAC) -> Scale +20%
SCALE_BUDGET_PCT         = 20       # KHONG bao gio tang > 20%/lan (reset Learning Phase)
SCALE_MIN_SCORE          = 65       # Score toi thieu de scale (fallback khi chua co pixel)
FREQ_WARNING             = 2.5      # Frequency > 2.5 -> flag, KHONG scale
FREQ_CRITICAL            = 3.5      # Frequency > 3.5 -> canh bao bao hoa
CPC_WARNING              = 4_000    # CPC > 4k -> flag
CPM_WARNING              = 130_000  # CPM > 130k -> flag
# ──────────────────────────────────────────────────────────


def log_print(msg, log_file):
    """In ra console va ghi vao log file."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_file.write(line + "\n")
    log_file.flush()


def sep(title="", w=66):
    line = "=" * w if not title else f"{'='*((w-len(title)-2)//2)} {title} {'='*((w-len(title)-2)//2)}"
    print(line)
    return line


def check_env():
    missing = []
    if not ACCESS_TOKEN:  missing.append("FB_ACCESS_TOKEN")
    if not AD_ACCOUNT_ID: missing.append("FB_AD_ACCOUNT_ID")
    if missing:
        print(f"\n[ERROR] Thieu bien moi truong: {', '.join(missing)}")
        print("  Set truoc khi chay:")
        for m in missing:
            print(f"    $env:{m} = 'your_value'")
        sys.exit(1)


# ── STEP 1: AUDIT ─────────────────────────────────────────
def step_audit(log_file):
    log_print("[STEP 1/3] Dang audit tai khoan...", log_file)

    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet

    FacebookAdsApi.init(APP_ID, "", ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)

    # Account info
    acc_data = account.api_get(fields=["name", "account_status", "currency", "amount_spent", "timezone_name"])
    STATUS_MAP = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 9: "IN_GRACE_PERIOD", 101: "CLOSED"}

    result = {
        "account": {
            "name":     acc_data.get("name"),
            "status":   STATUS_MAP.get(acc_data.get("account_status"), "UNKNOWN"),
            "currency": acc_data.get("currency"),
            "spent_30d": 0,
        },
        "campaigns": [],
        "top_ads": [],
        "flags": [],
    }

    # Campaign insights
    fields = ["campaign_id","campaign_name","spend","impressions","clicks",
              "ctr","cpm","frequency","actions","purchase_roas"]
    params = {"date_preset": "last_30d", "level": "campaign", "limit": 50}
    insights = list(account.get_insights(fields=fields, params=params))

    total_spend = 0
    for ins in insights:
        spend   = float(ins.get("spend", 0))
        total_spend += spend
        actions = ins.get("actions", [])
        buys    = _aval(actions, "purchase")                               # PRIMARY KPI
        msgs    = _aval(actions, "onsite_conversion.messaging_first_reply") # phu
        leads   = _aval(actions, "lead")                                   # phu
        ctr     = float(ins.get("ctr", 0))
        cpm     = float(ins.get("cpm", 0))
        freq    = float(ins.get("frequency", 0))
        roas_d  = ins.get("purchase_roas", [])
        roas    = float(roas_d[0]["value"]) if roas_d else 0               # PRIMARY KPI
        cpp     = int(spend / buys) if buys > 0 else 999999               # Cost per purchase
        sc      = _score_campaign(ctr, freq, cpm, spend, buys, roas)

        result["campaigns"].append({
            "id": ins.get("campaign_id"),
            "name": ins.get("campaign_name"),
            "spend": spend,
            "purchases": buys, "msgs": msgs, "leads": leads,
            "ctr": ctr, "cpm": cpm, "freq": freq,
            "roas": roas, "cost_per_purchase": cpp, "score": sc,
        })

        # Flags dua tren ROAS va Purchase (theo SOP thuc te)
        if freq > FREQ_CRITICAL:
            result["flags"].append(f"[FATIGUE] {ins.get('campaign_name')[:30]} - Freq={freq:.1f} > 3.5 -> doi creative ngay")
        elif freq > FREQ_WARNING:
            result["flags"].append(f"[FREQ-WARN] {ins.get('campaign_name')[:30]} - Freq={freq:.1f} -> mo rong tep")
        if spend > 500_000 and roas < 1.0 and buys == 0:
            result["flags"].append(f"[LOW-ROAS] {ins.get('campaign_name')[:30]} - Spend={spend:,.0f}d, ROAS={roas:.2f}x")
        if roas >= SCALE_ROAS_EXCELLENT:
            result["flags"].append(f"[SCALE-NOW] {ins.get('campaign_name')[:30]} - ROAS={roas:.2f}x -> +{SCALE_BUDGET_PCT}%")

    result["account"]["spent_30d"] = total_spend
    log_print(f"  >> {len(insights)} campaigns | Total spend 30d: {total_spend:,.0f}d", log_file)

    # Ad level insights
    ad_fields = ["ad_id","ad_name","campaign_name","spend","ctr","cpm",
                 "frequency","actions","purchase_roas"]
    ad_params = {"date_preset": "last_30d", "level": "ad", "limit": 200}
    ad_insights = list(account.get_insights(fields=ad_fields, params=ad_params))

    for r in ad_insights:
        spend   = float(r.get("spend", 0))
        if spend < 10000: continue
        actions = r.get("actions", [])
        buys    = _aval(actions, "purchase")                                # PRIMARY KPI
        msgs    = _aval(actions, "onsite_conversion.messaging_first_reply") # phu
        leads   = _aval(actions, "lead")                                    # phu
        ctr     = float(r.get("ctr", 0))
        cpm     = float(r.get("cpm", 0))
        freq    = float(r.get("frequency", 0))
        roas_d  = r.get("purchase_roas", [])
        roas    = float(roas_d[0]["value"]) if roas_d else 0
        sc      = _score_ad(spend, ctr, freq, buys, roas)
        cpp     = int(spend / buys) if buys > 0 else 999999
        result["top_ads"].append({
            "id": r.get("ad_id"), "name": r.get("ad_name"),
            "campaign": r.get("campaign_name"),
            "spend": spend, "purchases": buys, "msgs": msgs, "leads": leads,
            "ctr": ctr, "cpm": cpm, "freq": freq,
            "roas": roas, "cost_per_purchase": cpp, "score": sc,
        })

    result["top_ads"].sort(key=lambda x: x["score"], reverse=True)
    log_print(f"  >> {len(result['top_ads'])} ads co spend | Top ad: {result['top_ads'][0]['name'][:30] if result['top_ads'] else 'N/A'}", log_file)
    return result


# ── STEP 2: OPTIMIZE ──────────────────────────────────────
def step_optimize(audit_data, log_file):
    log_print("[STEP 2/3] Dang toi uu campaigns...", log_file)

    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad

    FacebookAdsApi.init(APP_ID, "", ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)

    actions_done = []
    actions_err  = []

    # --- Lay du lieu tu Meta ---
    campaigns = list(account.get_campaigns(fields=[
        Campaign.Field.id, Campaign.Field.name,
        Campaign.Field.effective_status, Campaign.Field.daily_budget,
    ]))
    adsets = list(account.get_ad_sets(fields=[
        AdSet.Field.id, AdSet.Field.name, AdSet.Field.campaign_id,
        AdSet.Field.effective_status, AdSet.Field.daily_budget,
    ]))
    ads = list(account.get_ads(fields=[
        Ad.Field.id, Ad.Field.name, Ad.Field.effective_status,
        Ad.Field.campaign_id,
    ]))

    camp_scores = {c["id"]: c for c in audit_data["campaigns"]}  # full object
    ad_data_map = {a["id"]: a for a in audit_data["top_ads"]}

    # 1. PAUSE ads: spend du lon MA ROAS thap va 0 purchase
    for ad in ads:
        ad_id = ad.get("id")
        if ad.get("effective_status") not in ("ACTIVE",):
            continue
        d     = ad_data_map.get(ad_id, {})
        spend = d.get("spend", 0)
        buys  = d.get("purchases", 0)
        roas  = d.get("roas", 0)
        if spend >= PAUSE_AD_MIN_SPEND and buys == 0 and roas < PAUSE_ROAS_BELOW:
            try:
                Ad(ad_id).api_update(params={"status": "PAUSED"})
                msg = f"PAUSED ad: {ad.get('name','')[:38]} | spend={spend:,.0f}d, purchases=0, ROAS={roas:.2f}x"
                actions_done.append(msg)
                log_print(f"  [OK] {msg}", log_file)
                time.sleep(0.3)
            except Exception as e:
                err = f"ERR pause ad {ad.get('name','')[:30]}: {e}"
                actions_err.append(err)
                log_print(f"  [ERR] {err}", log_file)

    # 2. SCALE UP campaigns — dua tren ROAS la KPI chinh
    for camp in campaigns:
        cid    = camp.get("id")
        status = camp.get("effective_status", "")
        if status != "ACTIVE": continue
        c_data = camp_scores.get(cid, {})
        roas   = c_data.get("roas", 0) if isinstance(c_data, dict) else 0
        sc     = c_data.get("score", 0) if isinstance(c_data, dict) else 0
        raw_b  = int(camp.get("daily_budget") or 0)
        if raw_b <= 0: continue

        pct = 0
        reason = ""
        # Theo SOP: chi scale khi ROAS >= 5x (DAT), khong scale khi CANH BAO (3-5x)
        if roas >= SCALE_ROAS_EXCELLENT:
            # ROAS >= 7x (XUAT SAC)
            pct = SCALE_BUDGET_PCT
            reason = f"ROAS={roas:.2f}x (XUAT SAC >= {SCALE_ROAS_EXCELLENT}x) -> +{pct}%"
        elif roas >= SCALE_ROAS_GOOD:
            # ROAS >= 5x (DAT)
            pct = SCALE_BUDGET_PCT
            reason = f"ROAS={roas:.2f}x (DAT >= {SCALE_ROAS_GOOD}x) -> +{pct}%"
        elif sc >= SCALE_MIN_SCORE and roas == 0:
            # Fallback: chua co purchase pixel, dung score
            pct = SCALE_BUDGET_PCT
            reason = f"Score={sc}/100 (chua co pixel, ROAS=0)"
        # ROAS 3-5x (CANH BAO): KHONG scale, giu nguyen
        # ROAS < 3x: PAUSE (xu ly o buoc 1)

        if pct > 0:
            new_b = int(raw_b * (1 + pct / 100))
            try:
                Campaign(cid).api_update(params={"daily_budget": str(new_b)})
                msg = f"SCALED +{pct}% campaign: {camp.get('name','')[:32]} | {raw_b:,} -> {new_b:,} VND | {reason}"
                actions_done.append(msg)
                log_print(f"  [OK] {msg}", log_file)
                time.sleep(0.3)
            except Exception as e:
                err = f"ERR scale campaign {camp.get('name','')[:30]}: {e}"
                actions_err.append(err)
                log_print(f"  [ERR] {err}", log_file)

    # 3. SCALE UP adsets neu campaign khong co budget
    camp_has_budget = {c.get("id") for c in campaigns if int(c.get("daily_budget") or 0) > 0}
    for ads_obj in adsets:
        camp_id = ads_obj.get("campaign_id")
        if camp_id in camp_has_budget: continue
        if ads_obj.get("effective_status") != "ACTIVE": continue
        c_data = camp_scores.get(camp_id, {})
        roas   = c_data.get("roas", 0) if isinstance(c_data, dict) else 0
        sc     = c_data.get("score", 0) if isinstance(c_data, dict) else 0
        raw_b  = int(ads_obj.get("daily_budget") or 0)
        if raw_b <= 0: continue

        pct = 0
        reason = ""
        if roas >= SCALE_ROAS_EXCELLENT:
            pct = SCALE_BUDGET_PCT
            reason = f"ROAS={roas:.2f}x XUAT SAC"
        elif roas >= SCALE_ROAS_GOOD:
            pct = SCALE_BUDGET_PCT
            reason = f"ROAS={roas:.2f}x DAT"
        elif sc >= SCALE_MIN_SCORE and roas == 0:
            pct = SCALE_BUDGET_PCT
            reason = f"Score={sc}/100"

        if pct > 0:
            new_b = int(raw_b * (1 + pct / 100))
            try:
                AdSet(ads_obj.get("id")).api_update(params={"daily_budget": str(new_b)})
                msg = f"SCALED +{pct}% adset: {ads_obj.get('name','')[:32]} | {raw_b:,} -> {new_b:,} VND | {reason}"
                actions_done.append(msg)
                log_print(f"  [OK] {msg}", log_file)
                time.sleep(0.3)
            except Exception as e:
                err = f"ERR scale adset {ads_obj.get('name','')[:30]}: {e}"
                actions_err.append(err)
                log_print(f"  [ERR] {err}", log_file)

    log_print(f"  >> Toi uu xong: {len(actions_done)} thanh cong | {len(actions_err)} loi", log_file)
    return actions_done, actions_err


# ── STEP 3: REPORT ────────────────────────────────────────
def step_report(audit_data, actions_done, actions_err, log_file):
    log_print("[STEP 3/3] Tao bao cao...", log_file)

    ts       = datetime.now().strftime("%Y%m%d_%H%M")
    report   = {
        "run_time":      datetime.now().isoformat(),
        "account":       audit_data["account"],
        "summary": {
            "total_campaigns": len(audit_data["campaigns"]),
            "total_ads_with_spend": len(audit_data["top_ads"]),
            "spend_30d": audit_data["account"]["spent_30d"],
            "flags": audit_data["flags"],
        },
        "top_3_ads":     audit_data["top_ads"][:3],
        "optimizations": actions_done,
        "errors":        actions_err,
    }

    fname = REPORT_DIR / f"fb_report_{ts}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # In summary
    sep("BAO CAO TOM TAT")
    acc  = audit_data["account"]
    print(f"\n  Tai khoan : {acc['name']} ({acc['status']})")
    print(f"  Spend 30d : {acc['spent_30d']:,.0f} VND")
    print(f"  Campaigns : {len(audit_data['campaigns'])}")

    if audit_data["top_ads"]:
        top = audit_data["top_ads"][0]
        cpp = top.get("cost_per_purchase", 999999)
        print(f"\n  [TOP AD] {top['name'][:40]}")
        print(f"    Campaign    : {top['campaign'][:35]}")
        print(f"    Score       : {top['score']}/100")
        print(f"    ROAS        : {top['roas']:.2f}x  |  Purchases: {top['purchases']}")
        print(f"    CTR         : {top['ctr']:.2f}%   |  CPM: {top['cpm']:,.0f}d")
        print(f"    Cost/Purchase: {'N/A' if cpp >= 999999 else f'{cpp:,}d'}")

    if audit_data["flags"]:
        print(f"\n  [CANH BAO - {len(audit_data['flags'])} van de]")
        for f in audit_data["flags"]:
            print(f"    {f}")

    print(f"\n  Toi uu thuc thi: {len(actions_done)} hanh dong")
    for a in actions_done:
        print(f"    [+] {a}")
    if actions_err:
        print(f"\n  Loi: {len(actions_err)}")
        for e in actions_err:
            print(f"    [-] {e}")

    print(f"\n  Report: {fname}")
    sep()
    log_print(f"  >> Report luu: {fname}", log_file)
    return str(fname)


# ── HELPERS ───────────────────────────────────────────────
def _aval(actions, t):
    for a in (actions or []):
        if a.get("action_type") == t:
            return int(float(a.get("value", 0)))
    return 0

def _score_ad(spend, ctr, freq, purchases, roas):
    """Score dua tren KPI thuc te SOP Quan Jean Nu."""
    score = 0
    # ROAS — KPI so 1 (0-40 pts) theo nguong SOP
    if roas >= 7.0:   score += 40   # XUAT SAC
    elif roas >= 5.0: score += 32   # DAT
    elif roas >= 3.0: score += 18   # CANH BAO
    elif roas >= 1.5: score += 8
    elif roas > 0:    score += 3
    # CPA/Purchase — KPI so 2 (0-30 pts)
    if purchases > 0 and spend > 0:
        cpa = spend / purchases
        if cpa <= 80_000:   score += 30  # XUAT SAC
        elif cpa <= 120_000:score += 22  # DAT
        elif cpa <= 180_000:score += 12  # CANH BAO
        else:               score += 4   # TAT
    # Frequency (0-15 pts)
    if freq <= 1.8:   score += 15   # XUAT SAC
    elif freq <= 2.5: score += 10   # DAT
    elif freq <= 3.5: score += 5    # CANH BAO
    # CTR (0-15 pts)
    if ctr >= 5.0:  score += 15   # XUAT SAC
    elif ctr >= 3.0:score += 10   # DAT
    elif ctr >= 2.0:score += 5    # CANH BAO
    return min(score, 100)

def _score_campaign(ctr, freq, cpm, spend, purchases, roas):
    """Score dua tren KPI thuc te SOP Quan Jean Nu."""
    score = 0
    # ROAS — KPI so 1 (0-40 pts)
    if roas >= 7.0:   score += 40
    elif roas >= 5.0: score += 32
    elif roas >= 3.0: score += 18
    elif roas >= 1.5: score += 8
    elif roas > 0:    score += 3
    # CPA/Purchase (0-25 pts)
    if purchases > 0 and spend > 0:
        cpa = spend / purchases
        if cpa <= 80_000:    score += 25
        elif cpa <= 120_000: score += 18
        elif cpa <= 180_000: score += 10
        else:                score += 3
    # Frequency (0-15 pts)
    if freq <= 1.8:   score += 15
    elif freq <= 2.5: score += 10
    elif freq <= 3.5: score += 5
    # CPM (0-10 pts)
    if cpm <= 80_000:   score += 10  # XUAT SAC
    elif cpm <= 100_000:score += 7   # DAT
    elif cpm <= 130_000:score += 4   # CANH BAO
    else:               score += 1   # TAT
    # CTR (0-10 pts)
    if ctr >= 5.0:  score += 10
    elif ctr >= 3.0:score += 7
    elif ctr >= 2.0:score += 4
    elif ctr >= 1.0:score += 2
    return min(score, 100)


# ── MAIN ─────────────────────────────────────────────────
def main():
    ts       = datetime.now().strftime("%Y%m%d_%H%M")
    log_path = LOG_DIR / f"fb_workflow_{ts}.txt"

    with open(log_path, "w", encoding="utf-8") as log_file:
        sep("FB ADS AUTO-WORKFLOW")
        log_print(f"Bat dau: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", log_file)
        log_print(f"Account: {AD_ACCOUNT_ID}", log_file)
        sep()

        check_env()

        try:
            # Step 1
            audit_data = step_audit(log_file)

            # Step 2
            actions_done, actions_err = step_optimize(audit_data, log_file)

            # Step 3
            report_path = step_report(audit_data, actions_done, actions_err, log_file)

            log_print(f"\n[DONE] Workflow hoan thanh luc {datetime.now().strftime('%H:%M:%S')}", log_file)
            log_print(f"[DONE] Log: {log_path}", log_file)
            log_print(f"[DONE] Report: {report_path}", log_file)

        except Exception as e:
            log_print(f"\n[FATAL ERROR] {e}", log_file)
            log_print(traceback.format_exc(), log_file)
            sys.exit(1)

if __name__ == "__main__":
    main()
