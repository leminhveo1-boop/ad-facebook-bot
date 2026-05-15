"""
Facebook Campaign Creator — Theo SOP Quan Jean Nu
===================================================
Tu dong tao Campaign + Ad Set theo cau truc 3 tang pheu:

  BOF: retarget — inbox + tuong tac 14 ngay
  MOF: lookalike 1% tu khach da mua

Chay DRY RUN truoc de xem ke hoach, sau moi --execute.
"""
import os, sys, io, json, time
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet

ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")
PAGE_ID       = os.environ.get("FB_PAGE_ID", "337996149742830")

TODAY = datetime.now().strftime("%d.%m")

# ── CAU HINH CAMPAIGN THEO SOP ────────────────────────────
CAMPAIGNS_PLAN = [
    {
        # ── BOF: RETARGET (Day pheu) ──────────────────────
        "campaign": {
            "name":      f"BOF_JeanNu_MSG_RTG_{TODAY}",
            "objective": "OUTCOME_ENGAGEMENT",
            "status":    "PAUSED",   # Bat dau PAUSED, kiem tra roi bat tay
            "special_ad_categories": [],
        },
        "adsets": [
            {
                "name":           f"BOF_NhanTin14d_MSG_{TODAY}",
                "audience_id":    "120244863713580224",  # BOF_JeanNu_NhanTin_14d
                "audience_note":  "Inbox 14 ngay — nong nhat",
                "daily_budget":   150_000,   # VND
                "targeting_note": "BOF nong — nguoi da nhan tin trong 14 ngay",
                "expected_roas":  ">= 6x (BOF)",
            },
            {
                "name":           f"BOF_TuongTac14d_MSG_{TODAY}",
                "audience_id":    "120244863712940224",  # BOF_JeanNu_TuongTac_14d
                "audience_note":  "Tuong tac page 14 ngay",
                "daily_budget":   100_000,   # VND
                "targeting_note": "BOF tuong tac rong hon",
                "expected_roas":  ">= 5x (BOF)",
            },
        ],
    },
    {
        # ── MOF: LOOKALIKE (Giua pheu) ────────────────────
        "campaign": {
            "name":      f"MOF_JeanNu_MSG_LLA_{TODAY}",
            "objective": "OUTCOME_ENGAGEMENT",
            "status":    "PAUSED",
            "special_ad_categories": [],
        },
        "adsets": [
            {
                "name":           f"MOF_LLA1pct_InboxMua_{TODAY}",
                "audience_id":    "120244864602490224",  # LLA 1% tu Inbox+mua hang
                "audience_note":  "Lookalike 1% tu 4,700 khach da inbox mua",
                "daily_budget":   200_000,   # VND
                "targeting_note": "MOF chat luong cao nhat — seed tu khach that",
                "expected_roas":  ">= 5x (MOF)",
            },
            {
                "name":           f"MOF_LLA1pct_DS6500_{TODAY}",
                "audience_id":    "120244864116290224",  # LLA 1% tu aaa.txt 6500 KH
                "audience_note":  "Lookalike 1% tu danh sach 6,500 khach hang",
                "daily_budget":   150_000,   # VND
                "targeting_note": "MOF danh sach rong hon",
                "expected_roas":  ">= 4x (MOF test)",
            },
        ],
    },
]

# ── TARGETING CHUNG (Phu hop SOP: Nu 22-40, VN) ──────────
BASE_TARGETING = {
    "geo_locations": {
        "countries": ["VN"],
    },
    "age_min": 22,
    "age_max": 40,
    "genders": [2],   # 1=Nam, 2=Nu
    "targeting_automation": {
        "advantage_audience": 0  # Tat mo rong doi tuong de giu dung tep BOF/MOF
    }
}


def sep(t="", w=68):
    if t: print(f"\n{'='*((w-len(t)-2)//2)} {t} {'='*((w-len(t)-2)//2)}")
    else: print("=" * w)


def print_plan():
    """Hien thi ke hoach truoc khi thuc thi."""
    sep("KE HOACH TAO CAMPAIGN — DRY RUN")
    total_budget = 0

    for i, plan in enumerate(CAMPAIGNS_PLAN, 1):
        c = plan["campaign"]
        print(f"\n  [{i}] CAMPAIGN: {c['name']}")
        print(f"      Objective : {c['objective']}")
        print(f"      Status    : {c['status']} (phai bat thu cong sau khi kiem tra)")

        for j, ads in enumerate(plan["adsets"], 1):
            bud = ads["daily_budget"]
            total_budget += bud
            print(f"\n      [{i}.{j}] AD SET: {ads['name']}")
            print(f"            Audience   : {ads['audience_note']}")
            print(f"            ID tep     : {ads['audience_id']}")
            print(f"            Budget/ngay: {bud:,} VND")
            print(f"            Target     : Nu 22-40, VN, Mobile, Feed+Reels")
            print(f"            ROAS ky vong: {ads['expected_roas']}")

    sep()
    print(f"\n  Tong: {len(CAMPAIGNS_PLAN)} campaigns | "
          f"{sum(len(p['adsets']) for p in CAMPAIGNS_PLAN)} ad sets")
    print(f"  Tong budget/ngay: {total_budget:,} VND")
    print(f"  Tong budget/thang (est): {total_budget*30:,} VND")
    print()
    print("  LUU Y QUAN TRONG:")
    print("  - Tat ca campaign tao PAUSED — anh kiem tra roi bat tay")
    print("  - Ad Set chua co Ad (creative) — vao Ads Manager them creative")
    print("  - Cho 24-48h tep moi dien nguoi truoc khi bat campaign")
    sep()


def create_campaign(account, plan_c, dry_run):
    """Tao 1 campaign va tra ve ID."""
    if dry_run:
        return f"DRY_RUN_{plan_c['name']}"

    params = {
        "name":                           plan_c["name"],
        "objective":                      plan_c["objective"],
        "status":                         plan_c["status"],
        "special_ad_categories":          plan_c["special_ad_categories"],
        "is_adset_budget_sharing_enabled": False,  # ABO: budget theo Ad Set
    }
    camp = account.create_campaign(params=params)
    return camp.get("id")


def create_adset(account, campaign_id, ads_plan, dry_run):
    """Tao 1 ad set trong campaign."""
    if dry_run:
        return f"DRY_RUN_{ads_plan['name']}"

    # Targeting: custom audience + base demographic
    targeting = {
        **BASE_TARGETING,
        "custom_audiences": [{"id": ads_plan["audience_id"]}],
    }

    params = {
        "name":              ads_plan["name"],
        "campaign_id":       campaign_id,
        "status":            "PAUSED",
        "daily_budget":      str(ads_plan["daily_budget"]),
        "billing_event":     "IMPRESSIONS",
        "optimization_goal": "CONVERSATIONS",
        "destination_type":  "MESSENGER",
        "bid_strategy":      "LOWEST_COST_WITHOUT_CAP", # Fix loi yeu cau gia thau
        "targeting":         json.dumps(targeting),
        "promoted_object":   json.dumps({"page_id": PAGE_ID}),
    }
    adset = account.create_ad_set(params=params)
    return adset.get("id")


def execute_all(dry_run=True):
    FacebookAdsApi.init(APP_ID, "", ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)

    results = []
    errors  = []

    sep("DANG TAO CAMPAIGNS" if not dry_run else "DRY RUN — KHONG THAY DOI THAT")

    for plan in CAMPAIGNS_PLAN:
        plan_c = plan["campaign"]
        print(f"\n  >> Campaign: {plan_c['name']}")

        try:
            camp_id = create_campaign(account, plan_c, dry_run)
            if not dry_run:
                print(f"     [OK] Campaign created (ID: {camp_id})")
                time.sleep(0.5)

            for ads_plan in plan["adsets"]:
                print(f"     >> Ad Set: {ads_plan['name']}")
                try:
                    adset_id = create_adset(account, camp_id, ads_plan, dry_run)
                    msg = f"[OK] AdSet: {ads_plan['name']} | Budget: {ads_plan['daily_budget']:,}d"
                    print(f"        {msg}" if not dry_run else f"        [SIM] {msg}")
                    results.append({
                        "campaign":    plan_c["name"],
                        "campaign_id": camp_id,
                        "adset":       ads_plan["name"],
                        "adset_id":    adset_id,
                        "budget":      ads_plan["daily_budget"],
                        "audience":    ads_plan["audience_note"],
                    })
                    if not dry_run:
                        time.sleep(0.5)
                except Exception as e:
                    err = f"[ERR] AdSet {ads_plan['name']}: {e}"
                    errors.append(err)
                    print(f"        {err}")

        except Exception as e:
            err = f"[ERR] Campaign {plan_c['name']}: {e}"
            errors.append(err)
            print(f"     {err}")

    return results, errors


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Campaign Creator")
    parser.add_argument("--execute", action="store_true", help="Thuc thi that (mac dinh: dry run)")
    args = parser.parse_args()

    dry_run = not args.execute

    sep("FACEBOOK CAMPAIGN CREATOR — SOP QUAN JEAN NU")
    print(f"  Account: {AD_ACCOUNT_ID}")
    print(f"  Page ID: {PAGE_ID}")
    print(f"  Mode   : {'*** DRY RUN ***' if dry_run else '!!! THUC THI THAT !!!'}")
    print(f"  Ngay   : {TODAY}")

    # Luon show plan truoc
    print_plan()

    if dry_run:
        print("\n  De thuc thi that, chay lai voi --execute:")
        print(f"  python fb-campaign-creator.py --execute")
        return

    # Thuc thi
    results, errors = execute_all(dry_run=False)

    sep("KET QUA")
    print(f"\n  Thanh cong: {len(results)} ad sets")
    print(f"  Loi       : {len(errors)}")

    if results:
        print("\n  BUOC TIEP THEO (lam thu cong trong Ads Manager):")
        print("  1. Vao Ads Manager -> chon campaign vua tao")
        print("  2. Vao tung Ad Set -> them Ad (upload creative: anh/video)")
        print("  3. Kiem tra xem truoc -> BAT campaign khi ok")
        print("  4. Theo doi 3 ngay dau (khong can thiep truoc 3 ngay)")
        print()
        for r in results:
            print(f"    Campaign: {r['campaign']} (ID: {r['campaign_id']})")
            print(f"    Ad Set  : {r['adset']} (ID: {r['adset_id']})")
            print(f"    Budget  : {r['budget']:,}d/ngay | {r['audience']}")
            print()

    if errors:
        print(f"\n  Loi:")
        for e in errors:
            print(f"    {e}")

    # Luu ket qua
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"fb_campaigns_created_{ts}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump({
            "created_at": datetime.now().isoformat(),
            "account": AD_ACCOUNT_ID,
            "page_id": PAGE_ID,
            "mode": "execute" if not dry_run else "dry_run",
            "results": results,
            "errors": errors,
        }, f, ensure_ascii=False, indent=2)
    print(f"  Log: {fname}")
    sep()


if __name__ == "__main__":
    main()
