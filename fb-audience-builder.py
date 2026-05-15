"""
Facebook Audience Builder
==========================
Tao tu dong 3 tang tep doi tuong theo SOP Quan Jean Nu:

  TOF — Cold: Nu 22-40, thoi trang, mua sam online
  MOF — Lookalike 1-3% tu tep khach hang + tuong tac
  BOF — Retarget: nguoi da tuong tac/xem video chua mua

Chay STEP 1 truoc (xem tep hien co), sau moi tao.
"""
import os, sys, io, json, time
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.customaudience import CustomAudience

ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")

# ── PAGE ID (lay tu audience engagement) ────────────────
# Anh can dien PAGE ID cua fanpage ban quan jean
# Tim tai: facebook.com/your-page -> About -> Page ID
PAGE_ID = os.environ.get("FB_PAGE_ID", "")   # VD: "123456789012345"


def sep(t="", w=66):
    if t: print(f"\n{'='*((w-len(t)-2)//2)} {t} {'='*((w-len(t)-2)//2)}")
    else: print("=" * w)


def step0_check_existing():
    """Xem tat ca tep doi tuong hien co trong tai khoan."""
    sep("TEP DOI TUONG HIEN CO")
    account = AdAccount(AD_ACCOUNT_ID)

    audiences = list(account.get_custom_audiences(fields=[
        CustomAudience.Field.id,
        CustomAudience.Field.name,
        CustomAudience.Field.subtype,
        CustomAudience.Field.approximate_count_lower_bound,
        CustomAudience.Field.approximate_count_upper_bound,
        CustomAudience.Field.description,
        CustomAudience.Field.data_source,
    ]))

    if not audiences:
        print("\n  Chua co tep nao trong tai khoan.")
        return []

    from tabulate import tabulate
    rows = []
    for a in audiences:
        lo  = a.get("approximate_count_lower_bound", 0) or 0
        hi  = a.get("approximate_count_upper_bound", 0) or 0
        cnt = f"{lo:,} - {hi:,}" if lo > 0 else "< 1,000"
        rows.append({
            "ID":      a.get("id"),
            "Ten":     (a.get("name") or "")[:40],
            "Loai":    a.get("subtype", ""),
            "So luong": cnt,
        })

    print(tabulate(rows, headers="keys", tablefmt="rounded_outline"))
    print(f"\n  Tong: {len(audiences)} tep")
    return audiences


def step1_create_engagement_audiences():
    """
    Tao tep BOF va MOF tu ENGAGEMENT (tuong tac trang, xem video).
    Khong can upload data khach hang — lay truc tiep tu Facebook.
    """
    sep("TAO TEP ENGAGEMENT (KHONG CAN DATA)")

    if not PAGE_ID:
        print("\n  [!] Can set FB_PAGE_ID truoc khi tao tep engagement.")
        print("  Tim Page ID: facebook.com/your-page -> About -> Page ID")
        print("  Set: $env:FB_PAGE_ID = '123456789'")
        return []

    account = AdAccount(AD_ACCOUNT_ID)
    created = []

    audiences_to_create = [
        # ── BOF: Tuong tac 14 ngay ────────────────────────────
        {
            "name":        "BOF_JeanNu_TuongTac_14d",
            "description": "Nguoi tuong tac voi Page trong 14 ngay qua",
            "subtype":     "ENGAGEMENT",
            "rule": json.dumps({
                "inclusions": {
                    "operator": "or",
                    "rules": [{
                        "event_sources": [{"id": PAGE_ID, "type": "page"}],
                        "retention_seconds": 14 * 86400,
                        "filter": {
                            "operator": "and",
                            "filters": [{
                                "field": "event",
                                "operator": "eq",
                                "value": "PageEngagedUsers"
                            }]
                        }
                    }]
                }
            }),
            "tang": "BOF",
        },
        # ── BOF: Tuong tac 30 ngay ────────────────────────────
        {
            "name":        "BOF_JeanNu_TuongTac_30d",
            "description": "Nguoi tuong tac voi Page trong 30 ngay qua",
            "subtype":     "ENGAGEMENT",
            "rule": json.dumps({
                "inclusions": {
                    "operator": "or",
                    "rules": [{
                        "event_sources": [{"id": PAGE_ID, "type": "page"}],
                        "retention_seconds": 30 * 86400,
                        "filter": {
                            "operator": "and",
                            "filters": [{
                                "field": "event",
                                "operator": "eq",
                                "value": "PageEngagedUsers"
                            }]
                        }
                    }]
                }
            }),
            "tang": "BOF",
        },
        # ── MOF: Tuong tac 60 ngay (seed Lookalike) ──────────
        {
            "name":        "MOF_JeanNu_TuongTac_60d",
            "description": "Nguoi tuong tac voi Page trong 60 ngay — seed Lookalike",
            "subtype":     "ENGAGEMENT",
            "rule": json.dumps({
                "inclusions": {
                    "operator": "or",
                    "rules": [{
                        "event_sources": [{"id": PAGE_ID, "type": "page"}],
                        "retention_seconds": 60 * 86400,
                        "filter": {
                            "operator": "and",
                            "filters": [{
                                "field": "event",
                                "operator": "eq",
                                "value": "PageEngagedUsers"
                            }]
                        }
                    }]
                }
            }),
            "tang": "MOF (Seed)",
        },
        # ── BOF: Nhan tin (Messenger) 14 ngay ────────────────
        {
            "name":        "BOF_JeanNu_NhanTin_14d",
            "description": "Nguoi da nhan tin voi Page trong 14 ngay qua",
            "subtype":     "ENGAGEMENT",
            "rule": json.dumps({
                "inclusions": {
                    "operator": "or",
                    "rules": [{
                        "event_sources": [{"id": PAGE_ID, "type": "page"}],
                        "retention_seconds": 14 * 86400,
                        "filter": {
                            "operator": "and",
                            "filters": [{
                                "field": "event",
                                "operator": "eq",
                                "value": "MessagingConversationStarted7d"
                            }]
                        }
                    }]
                }
            }),
            "tang": "BOF (Inbox)",
        },
    ]

    for aud in audiences_to_create:
        try:
            # Note: subtype NOT used for engagement audiences (deprecated since 2018)
            params = {
                "name":    aud["name"],
                "rule":    aud["rule"],
                "prefill": 1,
            }
            new_aud = account.create_custom_audience(params=params)
            aud_id = new_aud.get("id")
            created.append({"id": aud_id, "name": aud["name"], "tang": aud["tang"]})
            print(f"  [OK] [{aud['tang']}] {aud['name']} (ID: {aud_id})")
            time.sleep(0.5)
        except Exception as e:
            print(f"  [ERR] {aud['name']}: {e}")

    return created


def step2_create_lookalike(seed_audience_id, seed_name):
    """
    Tao Lookalike 1%, 2%, 3% tu tep seed.
    seed_audience_id: ID cua tep goc (engagement 60d hoac danh sach khach)
    """
    sep(f"TAO LOOKALIKE TU: {seed_name[:40]}")

    account = AdAccount(AD_ACCOUNT_ID)
    created = []

    for pct in [1, 2, 3]:
        try:
            params = {
                "name":             f"MOF_JeanNu_LLA{pct}pct",
                "subtype":          "LOOKALIKE",
                "origin_audience_id": seed_audience_id,
                "lookalike_spec": json.dumps({
                    "ratio": pct / 100,   # 0.01, 0.02, 0.03
                    "country": "VN",
                    "type": "similarity",
                }),
                "description": f"Lookalike {pct}% Viet Nam tu {seed_name[:30]}",
            }
            new_aud = account.create_custom_audience(params=params)
            aud_id = new_aud.get("id")
            created.append({"id": aud_id, "name": f"MOF_JeanNu_LLA{pct}pct"})
            print(f"  [OK] [MOF] Lookalike {pct}% VN (ID: {aud_id})")
            time.sleep(0.5)
        except Exception as e:
            print(f"  [ERR] Lookalike {pct}%: {e}")

    return created


def step3_upload_customer_list(customer_data: list):
    """
    Upload danh sach khach hang (so dien thoai/email).
    customer_data = [{"phone": "0901234567"}, {"phone": "0987654321"}, ...]
    """
    sep("UPLOAD DANH SACH KHACH HANG")
    print("  [!] Tinh nang nay yeu cau:")
    print("      1. File CSV so dien thoai / email khach da mua")
    print("      2. Hash SHA-256 truoc khi upload (bao mat)")
    print("      3. Tep se duoc dung lam seed cho Lookalike chinh xac nhat")
    print()
    print("  Xem huong dan chi tiet tai:")
    print("  https://developers.facebook.com/docs/marketing-api/audiences/guides/custom-audiences")
    print()
    print("  Anh co the chay: python fb-audience-builder.py --upload-csv path/to/customers.csv")


def print_summary(all_created):
    sep("TON TAT TEP DA TAO")
    if not all_created:
        print("  Khong co tep moi nao duoc tao.")
        return

    print(f"\n  Da tao {len(all_created)} tep doi tuong:\n")
    for a in all_created:
        print(f"    [{a.get('tang', 'N/A')}] {a['name']} (ID: {a['id']})")

    print()
    print("  BUOC TIEP THEO:")
    print("  1. Vao Ads Manager -> Audiences de xem tep vua tao")
    print("  2. Cho 24-48h de Facebook dien so luong nguoi vao tep")
    print("  3. Dung cac tep nay khi tao Ad Set:")
    print("     - BOF_*  -> Ad Set cho campaign retarget")
    print("     - MOF_LLA* -> Ad Set cho campaign lookalike")
    print("  4. Khi co data khach hang: chay lai voi --upload-csv")
    sep()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Audience Builder")
    parser.add_argument("--check",   action="store_true", help="Chi xem tep hien co")
    parser.add_argument("--create",  action="store_true", help="Tao tep engagement moi")
    parser.add_argument("--lookalike", metavar="AUDIENCE_ID", help="Tao lookalike tu ID tep seed")
    parser.add_argument("--seed-name", metavar="NAME", default="Tep goc", help="Ten tep seed")
    args = parser.parse_args()

    FacebookAdsApi.init(APP_ID, "", ACCESS_TOKEN)
    print(f"\n[OK] API connected | Account: {AD_ACCOUNT_ID}")
    print(f"[OK] Page ID: {PAGE_ID or '[CHUA SET]'}\n")

    all_created = []

    # Luon xem tep hien co truoc
    existing = step0_check_existing()

    if args.check:
        return  # Chi check, khong tao

    if args.create or (not args.check and not args.lookalike):
        # Tao tep engagement (default action)
        created = step1_create_engagement_audiences()
        all_created.extend(created)

        # Tu dong tao lookalike tu tep MOF_60d vua tao
        mof_seed = next((a for a in created if "60d" in a["name"]), None)
        if mof_seed:
            lla = step2_create_lookalike(mof_seed["id"], mof_seed["name"])
            all_created.extend([{**a, "tang": "MOF"} for a in lla])

    if args.lookalike:
        lla = step2_create_lookalike(args.lookalike, args.seed_name)
        all_created.extend([{**a, "tang": "MOF"} for a in lla])

    print_summary(all_created)

    # Luu ket qua
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"fb_audiences_{ts}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump({
            "created_at": datetime.now().isoformat(),
            "account": AD_ACCOUNT_ID,
            "page_id": PAGE_ID,
            "existing": len(existing),
            "new_audiences": all_created,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  [*] Saved: {fname}")


if __name__ == "__main__":
    main()
