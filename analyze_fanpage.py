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

def get_recent_posts(page_id, page_token):
    # Lấy bài viết trong 3 ngày qua để xem bài nào hiệu quả
    url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    params = {
        'fields': 'message,created_time,permalink_url,likes.summary(true),comments.summary(true),shares',
        'access_token': page_token,
        'limit': 5
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json().get('data', [])
    else:
        print(r.text)
        return []

if __name__ == "__main__":
    p_id, p_token, p_name = get_page_token("Quần Jean Nữ")
    if p_id:
        posts = get_recent_posts(p_id, p_token)
        print("--- TOP 5 BÀI VIẾT GẦN NHẤT ---")
        for post in posts:
            msg = post.get('message', '')[:50].replace('\n', ' ')
            likes = post.get('likes', {}).get('summary', {}).get('total_count', 0)
            comments = post.get('comments', {}).get('summary', {}).get('total_count', 0)
            shares = post.get('shares', {}).get('count', 0)
            time = post.get('created_time', '')
            print(f"[{time}] {msg}... | Likes: {likes}, Cmt: {comments}, Share: {shares}")
