from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
import os

ACCESS_TOKEN = os.environ.get('FB_ACCESS_TOKEN')
AD_ACCOUNT_ID = os.environ.get('FB_AD_ACCOUNT_ID')
APP_ID = os.environ.get('FB_APP_ID')

FacebookAdsApi.init(APP_ID, '', ACCESS_TOKEN)
acc = AdAccount(AD_ACCOUNT_ID)

camps = acc.get_campaigns(
    fields=['id', 'name', 'effective_status', 'daily_budget', 'lifetime_budget'], 
    params={'filtering': [{'field': 'effective_status', 'operator': 'IN', 'value': ['ACTIVE']}]}
)

print('--- DANH SACH NGAN SACH ---')
for c in camps:
    c_budget = c.get('daily_budget')
    if c_budget:
        print(f'[CBO] Campaign: {c.get("name")} - Ngan sach: {int(c_budget)/1000:,.0f}k/ngay')
    else:
        print(f'[ABO] Campaign: {c.get("name")}')
        adsets = Campaign(c['id']).get_ad_sets(
            fields=['name', 'effective_status', 'daily_budget', 'lifetime_budget'], 
            params={'filtering': [{'field': 'effective_status', 'operator': 'IN', 'value': ['ACTIVE']}]}
        )
        for a in adsets:
            a_budget = a.get('daily_budget')
            a_life = a.get('lifetime_budget')
            if a_budget:
                print(f'  -> AdSet: {a.get("name")} - Ngan sach: {int(a_budget)/1000:,.0f}k/ngay')
            elif a_life:
                print(f'  -> AdSet: {a.get("name")} - Ngan sach Tron doi: {int(a_life)/1000:,.0f}k')
            else:
                print(f'  -> AdSet: {a.get("name")} - Khong xac dinh')
