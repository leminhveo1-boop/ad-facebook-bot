import os, sys, io
import json
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign

ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")

def main():
    print("="*60)
    print(" DANH DEP CAMPAIGN RONG (KHONG CO AD SET)")
    print("="*60)
    
    FacebookAdsApi.init(APP_ID, "", ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)
    
    # Lay tat ca campaigns
    print("Dang lay danh sach campaign...")
    campaigns = account.get_campaigns(fields=[
        Campaign.Field.id,
        Campaign.Field.name,
        Campaign.Field.status,
    ], params={"limit": 100})
    
    deleted_count = 0
    kept_count = 0
    
    for camp in campaigns:
        name = camp.get("name", "")
        # Chi xet nhung campaign moi tao hom nay do tool lam
        if "BOF_JeanNu_MSG_RTG" in name or "MOF_JeanNu_MSG_LLA" in name:
            # Dem so luong ad sets trong campaign
            adsets = camp.get_ad_sets(fields=["id"])
            adset_count = len(list(adsets))
            
            if adset_count == 0:
                print(f" [XOA] Campaign rỗng: {name} (ID: {camp['id']})")
                camp.api_delete()
                deleted_count += 1
            else:
                print(f" [GIU] Campaign tốt : {name} (ID: {camp['id']}) — Co {adset_count} adsets")
                kept_count += 1
                
    print("\n="*60)
    print(f" DA XOA {deleted_count} campaign rỗng.")
    print(f" DA GIU {kept_count} campaign hoan chinh.")
    print("="*60)

if __name__ == "__main__":
    main()
