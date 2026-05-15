import os, requests, json
from datetime import datetime, timedelta

# Lấy token từ biến môi trường hoặc dùng mặc định
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

def get_page_insights(page_id, page_token, days=1):
    metrics = "page_impressions_unique,page_post_engagements"
    
    start_date = datetime.now() - timedelta(days=days)
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
    if r.status_code != 200:
        return f"Error: {r.text}"
        
    data = r.json().get('data', [])
    
    results = {}
    for item in data:
        name = item['name'] # VD: page_impressions_unique
        values = item.get('values', [])
        if values:
            # Lấy value của ngày hôm qua (ngày gần nhất)
            results[name] = values[-1].get('value', 0)
            
    return results

if __name__ == "__main__":
    # Tìm page có tên "Quần Jean Nữ"
    p_id, p_token, p_name = get_page_token("Quần Jean Nữ")
    if p_id:
        print(f"--- Đang phân tích Page: {p_name} ---")
        insights = get_page_insights(p_id, p_token, days=1)
        
        reach = insights.get('page_impressions_unique', 0)
        engagements = insights.get('page_post_engagements', 0)
        
        print(f"Lượt Reach (Tiếp cận) hôm qua: {reach}")
        print(f"Lượt Tương tác hôm qua: {engagements}")
    else:
        print("Không tìm thấy Fanpage hợp lệ.")
