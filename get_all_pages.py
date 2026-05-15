import requests
import json
token = 'EAAWretZAkV04BRQp9Gtoti6ZCHx3nGiB8eN2XKN9oxmpimFNSCvzEKM5p8WP9YZAIQKaRkcxZCG3PyKod9Xh6VhO9EuTRtrnMIcCti9eGLJrDnXC2aSVIXXGpwCaKViL1b0WTIQ3gqcNSCXCsx3uql6VfOVDqVPMFCj3ccSrbPsIXWfYZCWgR6gHukKkA8Abks0ezch9r0k0B7fUrNPWyY9fARLCBRiZB7PUtzKtiQ5iUUIxZAF3y5h5YaH8c8DoYlVsUZC5f6lI0ULnHW41hla1dAZDZD'
url = f'https://graph.facebook.com/v19.0/me/accounts?access_token={token}&limit=100'
pages = []
while url:
    r = requests.get(url).json()
    if 'data' in r:
        pages.extend(r['data'])
    url = r.get('paging', {}).get('next')

print(json.dumps([p['name'] for p in pages], ensure_ascii=False))
