import os, sys, requests, json, io, argparse
from datetime import datetime, timedelta

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
APP_ID        = os.environ.get("FB_APP_ID", "1595918954813262")

# ===== CAU HINH TELEGRAM =====
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8761610260:AAErFpY0B4LZSdLEPQqI-HCU3QflDxcW8SM")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "1966471122")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    return response.ok, response.text

def get_page_token(access_token, page_name_contains):
    url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}&limit=100"
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

def get_page_insights(page_id, page_token, target_date=None):
    metrics = "page_impressions_unique,page_post_engagements"
    if target_date == "yesterday":
        start_date = datetime.now() - timedelta(days=1)
        since = start_date.strftime('%Y-%m-%d')
        until = datetime.now().strftime('%Y-%m-%d')
    elif target_date and target_date != "today":
        # custom date YYYY-MM-DD
        dt = datetime.strptime(target_date, '%Y-%m-%d')
        since = dt.strftime('%Y-%m-%d')
        until = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    else: # today
        since = datetime.now().strftime('%Y-%m-%d')
        until = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
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
        return {}
    data = r.json().get('data', [])
    results = {}
    for item in data:
        name = item['name']
        values = item.get('values', [])
        if values:
            results[name] = values[-1].get('value', 0)
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Date in YYYY-MM-DD format or 'yesterday'", default="today")
    args = parser.parse_args()
    
    print("="*60)
    print(f" DANG TAO BAO CAO FB ADS & GUI TELEGRAM ({args.date})")
    print("="*60)
    
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("[Loi] Chua cau hinh TELEGRAM_BOT_TOKEN.")
        return
        
    FacebookAdsApi.init(APP_ID, "", ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)
    
    if args.date == "yesterday":
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        params = {'time_range': {'since': target_date, 'until': target_date}}
        display_date = target_date
    elif args.date != "today":
        params = {'time_range': {'since': args.date, 'until': args.date}}
        display_date = args.date
    else:
        params = {'date_preset': 'today'}
        display_date = datetime.now().strftime('%d/%m/%Y')
    
    fields = ['spend', 'actions', 'action_values']
    
    try:
        insights = account.get_insights(fields=fields, params=params)
    except Exception as e:
        print(f"Loi khi call FB API: {e}")
        return
    
    if not insights:
        msg = f"📊 <b>BÁO CÁO FB ADS (Chưa có Data)</b>\n📅 Ngày: {display_date}\n\nTrong khoảng thời gian này tài khoản chưa cắn tiền."
        send_telegram_message(msg)
        print("Da gui bao cao (Khong co data).")
        return
        
    data = insights[0]
    spend = float(data.get('spend', 0))
    
    purchases = 0
    purchase_value = 0.0
    messages = 0
    
    if 'actions' in data:
        for act in data['actions']:
            t = act.get('action_type', '')
            if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                # Facebook co the tra ve nhieu key purchase (omni, onsite), ta uu tien lay so lon nhat de khong bi sot
                purchases = max(purchases, int(act.get('value', 0)))
            elif t == 'onsite_conversion.messaging_conversation_started_7d':
                # Bat dung luot ket noi tin nhan moi, tranh bi cong don cac log phu
                messages = int(act.get('value', 0))
                
    if 'action_values' in data:
        for act in data['action_values']:
            t = act.get('action_type', '')
            if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                purchase_value = max(purchase_value, float(act.get('value', 0)))
                
    roas = (purchase_value / spend) if spend > 0 else 0.0
    
    cpmes = (spend / messages) if messages > 0 else 0
    cpa = (spend / purchases) if purchases > 0 else 0

    msg = f"📊 <b>BÁO CÁO TỔNG QUAN FB ADS</b>\n"
    msg += f"📅 Ngày: {display_date}\n"
    msg += f"-------------------------\n"
    msg += f"💸 <b>Chi tiêu:</b> {spend:,.0f} đ\n"
    msg += f"💬 <b>Tin nhắn mới:</b> {messages}\n"
    msg += f"💵 <b>Giá / Tin nhắn:</b> {cpmes:,.0f} đ\n"
    msg += f"📦 <b>Số đơn:</b> {purchases}\n"
    msg += f"💳 <b>Giá / Đơn (CPA):</b> {cpa:,.0f} đ\n"
    msg += f"💰 <b>Doanh thu:</b> {purchase_value:,.0f} đ\n"
    msg += f"🚀 <b>ROAS:</b> {roas:.2f}x\n"
    msg += f"-------------------------\n"
    
    # --- FANPAGE INSIGHTS ---
    try:
        p_id, p_token, p_name = get_page_token(ACCESS_TOKEN, "Quần Jean Nữ")
        if p_id:
            page_data = get_page_insights(p_id, p_token, target_date=args.date)
            reach = page_data.get('page_impressions_unique', 0)
            engagements = page_data.get('page_post_engagements', 0)
            msg += f"📱 <b>Fanpage:</b> {p_name}\n"
            msg += f"👁 <b>Lượt Reach:</b> {reach:,}\n"
            msg += f"👍 <b>Tương tác:</b> {engagements:,}\n"
            msg += f"-------------------------\n"
    except Exception as e:
        print(f"Loi lay Page Insights: {e}")

    
    # --- CAMPAIGN INSIGHTS ---
    try:
        camp_params = params.copy()
        camp_params['level'] = 'campaign'
        camps = account.get_insights(fields=['campaign_name', 'spend', 'actions', 'action_values'], params=camp_params)
        camps = sorted(camps, key=lambda x: float(x.get('spend', 0)), reverse=True)
        
        if camps:
            msg += f"📌 <b>TOP CHIẾN DỊCH:</b>\n"
            for c in camps:
                c_spend = float(c.get('spend', 0))
                if c_spend < 1000: continue
                
                c_purchases = 0
                c_purchase_value = 0.0
                c_messages = 0
                
                if 'actions' in c:
                    for act in c['actions']:
                        t = act.get('action_type', '')
                        if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                            c_purchases = max(c_purchases, int(act.get('value', 0)))
                        elif t == 'onsite_conversion.messaging_conversation_started_7d':
                            c_messages = int(act.get('value', 0))
                            
                if 'action_values' in c:
                    for act in c['action_values']:
                        t = act.get('action_type', '')
                        if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                            c_purchase_value = max(c_purchase_value, float(act.get('value', 0)))
                
                c_roas = (c_purchase_value / c_spend) if c_spend > 0 else 0.0
                c_cpmes = (c_spend / c_messages) if c_messages > 0 else 0
                c_cpa = (c_spend / c_purchases) if c_purchases > 0 else 0
                
                c_name = c.get('campaign_name', '')[:20]
                msg += f"▪️ <i>{c_name}</i>\n"
                msg += f"   Tiêu: {c_spend/1000:.0f}k | TN: {c_messages} ({c_cpmes/1000:.0f}k) | Đơn: {c_purchases} | ROAS: {c_roas:.1f}x\n"
            msg += f"-------------------------\n"
            
    except Exception as e:
        print(f"Loi lay Campaign: {e}")

    msg += f"🤖 <i>Gửi từ Antigravity AI Agent</i>"
    
    print(msg)
    
    print("\nDang gui qua Telegram...")
    success, err_msg = send_telegram_message(msg)
    if success:
        print("[OK] Gửi Telegram thành công!")
    else:
        print(f"[ERR] Gửi thất bại. Loi: {err_msg}")

if __name__ == "__main__":
    main()
