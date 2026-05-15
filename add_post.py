from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.campaign import Campaign
import os

ACCESS_TOKEN = os.environ.get('FB_ACCESS_TOKEN')
AD_ACCOUNT_ID = os.environ.get('FB_AD_ACCOUNT_ID')
APP_ID = os.environ.get('FB_APP_ID')

FacebookAdsApi.init(APP_ID, '', ACCESS_TOKEN)
account = AdAccount(AD_ACCOUNT_ID)

page_id = '337996149742830'
post_id = '1485789129912029'
object_story_id = f"{page_id}_{post_id}"

print(f"Creating AdCreative for {object_story_id}...")
creative = AdCreative(parent_id=AD_ACCOUNT_ID)
creative[AdCreative.Field.name] = f"Creative_Post_{post_id}"
creative[AdCreative.Field.object_story_id] = object_story_id
try:
    creative.remote_create()
    creative_id = creative[AdCreative.Field.id]
    print(f"Created AdCreative with ID: {creative_id}")
except Exception as e:
    print(f"Failed to create AdCreative: {e}")
    exit(1)

campaign_ids = ['120244866030010224', '120244866023250224']

for camp_id in campaign_ids:
    camp = Campaign(camp_id)
    camp.api_get(fields=['name'])
    print(f"\nProcessing Campaign: {camp['name']}")
    adsets = camp.get_ad_sets(fields=['id', 'name'])
    for adset in adsets:
        print(f"  Adding to AdSet: {adset['name']} ({adset['id']})")
        ad = Ad(parent_id=AD_ACCOUNT_ID)
        ad[Ad.Field.name] = f"Ad - Post {post_id}"
        ad[Ad.Field.adset_id] = adset['id']
        ad[Ad.Field.creative] = {'creative_id': creative_id}
        ad[Ad.Field.status] = 'ACTIVE'
        try:
            ad.remote_create()
            print(f"    -> Success: Ad {ad['id']} created and ACTIVE.")
        except Exception as e:
            print(f"    -> Error creating ad: {e}")
