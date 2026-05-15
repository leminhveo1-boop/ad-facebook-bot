import os, sys, io, json, time
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad

ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")
PAGE_ID       = os.environ.get("FB_PAGE_ID", "337996149742830")

TODAY = datetime.now().strftime("%d.%m")

# 3 Post IDs moi cua anh
REEL_IDS = [
    "1498733928617549",
    "1499612711863004",
    "1477923827365226"
]

BASE_TARGETING = {
    "geo_locations": {"countries": ["VN"]},
    "age_min": 22,
    "age_max": 40,
    "genders": [2],
    "targeting_automation": {
        "advantage_audience": 0  # Tat Advantage+ de ep chat do tuoi 22-40
    }
}

def sep(t="", w=68):
    if t: print(f"\n{'='*((w-len(t)-2)//2)} {t} {'='*((w-len(t)-2)//2)}")
    else: print("=" * w)

def create_campaign(account):
    params = {
        "name": f"TOF_Test_3_Mau_JeanNu_{TODAY}",
        "objective": "OUTCOME_SALES",
        "status": "PAUSED",
        "special_ad_categories": [],
        "is_adset_budget_sharing_enabled": False, # Chay ABO (ngan sach nhom)
    }
    camp = account.create_campaign(params=params)
    return camp.get("id")

def create_adset(account, campaign_id, idx, reel_id):
    params = {
        "name": f"Test_Mau_{idx+1}_Reel_{reel_id}",
        "campaign_id": campaign_id,
        "status": "PAUSED",
        "daily_budget": "100000",
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "MESSAGING_PURCHASE_CONVERSION",
        "destination_type": "MESSENGER",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "targeting": json.dumps(BASE_TARGETING),
        "promoted_object": json.dumps({"page_id": PAGE_ID}),
    }
    adset = account.create_ad_set(params=params)
    return adset.get("id")

def create_adcreative(account, reel_id):
    # Gắn post có sẵn trên page vao quang cao
    params = {
        "name": f"Creative_Reel_{reel_id}",
        "object_story_id": f"{PAGE_ID}_{reel_id}",
    }
    creative = account.create_ad_creative(params=params)
    return creative.get("id")

def create_ad(account, adset_id, creative_id, idx):
    params = {
        "name": f"Ad_Mau_{idx+1}",
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    }
    ad = account.create_ad(params=params)
    return ad.get("id")

def main():
    FacebookAdsApi.init(APP_ID, "", ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)

    sep("BAT DAU SET UP CAMPAIGN TEST 4 MAU JEAN")
    print(f" Account: {AD_ACCOUNT_ID}")
    print(f" Page ID: {PAGE_ID}\n")

    try:
        # 1. Tao Campaign
        camp_id = create_campaign(account)
        print(f" [OK] Đã tạo Campaign TOF Test (ID: {camp_id})")

        # 2. Tao AdSets va Ads
        for idx, reel_id in enumerate(REEL_IDS):
            print(f"\n >> Đang xử lý Mẫu {idx+1} (Reel: {reel_id})...")
            
            # Tao Ad Set
            adset_id = create_adset(account, camp_id, idx, reel_id)
            print(f"    [OK] Tạo Ad Set thành công (Ngân sách: 100k/ngày)")
            time.sleep(1)

            # Tao Creative tu ID bai viet
            try:
                creative_id = create_adcreative(account, reel_id)
                print(f"    [OK] Đã gắn video Reel thành Creative")
                
                # Tao Ad
                ad_id = create_ad(account, adset_id, creative_id, idx)
                print(f"    [OK] Tạo Quảng Cáo hoàn tất (Ad ID: {ad_id})")
            except Exception as e:
                print(f"    [ERR] Lỗi khi tạo Creative/Ad (Reel ID có thể sai hoặc bài viết ko hỗ trợ chạy tin nhắn): {e}")

    except Exception as e:
         print(f"\n[ERR] Lỗi hệ thống: {e}")

    sep("HOAN TAT")

if __name__ == "__main__":
    main()
