import os
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

FacebookAdsApi.init('1595918954813262', '', os.environ.get('FB_ACCESS_TOKEN'))
acc = AdAccount(os.environ.get('FB_AD_ACCOUNT_ID'))
insights = acc.get_insights(fields=['actions'], params={'date_preset': 'today'})

if insights and 'actions' in insights[0]:
    for a in insights[0]['actions']:
        print(f"{a.get('action_type')}: {a.get('value')}")
