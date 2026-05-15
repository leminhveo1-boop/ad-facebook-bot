import os, requests, json
from datetime import datetime, timedelta

FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "EAAWretZAkV04BRQp9Gtoti6ZCHx3nGiB8eN2XKN9oxmpimFNSCvzEKM5p8WP9YZAIQKaRkcxZCG3PyKod9Xh6VhO9EuTRtrnMIcCti9eGLJrDnXC2aSVIXXGpwCaKViL1b0WTIQ3gqcNSCXCsx3uql6VfOVDqVPMFCj3ccSrbPsIXWfYZCWgR6gHukKkA8Abks0ezch9r0k0B7fUrNPWyY9fARLCBRiZB7PUtzKtiQ5iUUIxZAF3y5h5YaH8c8DoYlVsUZC5f6lI0ULnHW41hla1dAZDZD")

def get_page_token(page_name_contains):
    url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={FB_ACCESS_TOKEN}&limit=100"
    while url:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json().get('data', [])
            for page in data:
                if page_name_contains.lower() in page.get('name', '').lower():
                    return page.get('id'), page.get('access_token'), page.get('name')
            url = r.json().get('paging', {}).get('next')
        else:
            break
    return None, None, None

def get_daily_metrics(page_id, page_token):
    metrics = "page_impressions_unique,page_impressions_organic_unique_v2,page_impressions_paid_unique,page_post_engagements"
    # Yesterday 
    start_date = datetime.now() - timedelta(days=1)
    since = start_date.strftime('%Y-%m-%d')
    until = datetime.now().strftime('%Y-%m-%d')
    
    url = f"https://graph.facebook.com/v19.0/{page_id}/insights"
    params = {
        'metric': metrics,
        'period': 'day',
        'since': since,
        'until': until,
        'access_token': page_token
    }
    r = requests.get(url, params=params)
    data = r.json().get('data', [])
    
    results = {}
    for item in data:
        name = item['name']
        values = item.get('values', [])
        if values:
            results[name] = values[-1].get('value', 0)
    return results

def count_posts_yesterday(page_id, page_token):
    start_date = datetime.now() - timedelta(days=1)
    # Using unix timestamps for precise yesterday start (00:00) and end (23:59)
    # Actually just since and until strings usually work
    since = start_date.strftime('%Y-%m-%dT00:00:00')
    until = start_date.strftime('%Y-%m-%dT23:59:59')
    url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    params = {
        'since': since,
        'until': until,
        'access_token': page_token,
        'limit': 100
    }
    r = requests.get(url, params=params)
    data = r.json().get('data', [])
    return len(data)

if __name__ == "__main__":
    p_id, p_token, p_name = get_page_token("Quần Jean Nữ")
    if p_id:
        metrics = get_daily_metrics(p_id, p_token)
        posts_count = count_posts_yesterday(p_id, p_token)
        
        print(json.dumps({
            "posts": posts_count,
            "metrics": metrics
        }, indent=2))
