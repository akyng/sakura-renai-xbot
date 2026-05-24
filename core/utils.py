import re

def calculate_weighted_length(text: str) -> float:
    """
    X (Twitter)の文字数計算ルールに従って、文字列の重み付け長さを計算します。
    日本語などの全角文字 = 2ポイント (1文字扱い)
    英数字や半角記号 = 1ポイント (0.5文字扱い)
    URL = 一律で23ポイントに置き換えて計算
    """
    # URLの検出と置換 (http:// または https:// で始まる文字列)
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(text)
    
    # URL部分を除去したテキストを作成
    clean_text = url_pattern.sub('', text)
    
    # URL以外の部分の重み付けカウント
    length = 0
    for char in clean_text:
        # ASCII文字、半角カタカナなどは1ポイント、それ以外（全角文字）は2ポイント
        if ord(char) <= 127 or (0xff61 <= ord(char) <= 0xff9f):
            length += 1
        else:
            length += 2
            
    # 検出された各URLについて一律で23ポイント（半角換算23文字分）を加算
    length += len(urls) * 23
    
    # 2半角単位 = 1全角文字換算で返す
    return length / 2

def split_thread(raw_text: str, cta_url: str = "") -> list:
    """
    Geminiが生成したテキストを、Xの1投稿制限（全角140文字 / 280ポイント）に収まるよう
    綺麗に分割し、連投スレッド用のリストを作成します。
    
    - 各ツイートの最大値は安全のため138文字（276ポイント）に制限します。
    - 最初のポストには指定のハッシュタグを自動付加します。
    - 最終ポストには自然にCTAリンク（アプリ宣伝URL）を付加します。
    """
    # 「1. 」「2. 」または改行などでセグメントに分割
    segments = [s.strip() for s in re.split(r'\n\n+', raw_text) if s.strip()]
    
    tweets = []
    current_tweet = ""
    max_length = 138.0 # 安全マージンを取った最大全角文字数
    
    # 指定のハッシュタグ (Xの最新アルゴリズムによるスパム判定回避のため1〜2個に厳選)
    hashtags = "#恋愛ゲーム #AIチャット"
    
    for seg in segments:
        # 新しいセグメントを結合した場合の予測文字数を計算
        test_tweet = f"{current_tweet}\n\n{seg}" if current_tweet else seg
        
        if calculate_weighted_length(test_tweet) <= max_length:
            current_tweet = test_tweet
        else:
            # 限界を超える場合は現在のツイートを確定させ、新規ツイートを開始
            if current_tweet:
                tweets.append(current_tweet)
            current_tweet = seg
            
    if current_tweet:
        tweets.append(current_tweet)
        
    # 最初のポストにハッシュタグを追加
    if tweets:
        first_tweet = tweets[0]
        first_tweet_with_tags = f"{first_tweet}\n\n{hashtags}"
        # ハッシュタグを追加しても文字数制限に収まる場合は結合、そうでない場合は2番目のポストとして挿入
        if calculate_weighted_length(first_tweet_with_tags) <= max_length:
            tweets[0] = first_tweet_with_tags
        else:
            tweets.insert(1, hashtags)
        
    # 最後のポストにCTAリンクを追加
    if cta_url and tweets:
        last_tweet = tweets[-1]
        cta_suffix = f"\n\n詳細と無料ダウンロードはこちらから👇\n{cta_url}"
        
        # リンクを追加した結果、制限文字数を超える場合は最後のポストを分割する
        if calculate_weighted_length(f"{last_tweet}{cta_suffix}") <= max_length:
            tweets[-1] = f"{last_tweet}{cta_suffix}"
        else:
            # 文字数オーバーする場合は、CTAリンクだけの返信ポストを末尾に新しく追加する
            tweets.append(f"アプリの無料ダウンロード・詳細はこちらからチェック！👇\n{cta_url}")
            
    return tweets

def send_chatwork_notification(message: str) -> None:
    """Chatwork に通知メッセージを送信する。"""
    import requests
    from config import Config
    token = Config.CHATWORK_API_TOKEN
    room_id = Config.CHATWORK_ROOM_ID
    if not token or not room_id:
        print("⚠️ Chatwork credentials missing. Skipping notification.")
        return
    url = f"https://api.chatwork.com/v2/rooms/{room_id}/messages"
    headers = {"X-ChatWorkToken": token}
    data = {"body": message}
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        print("✅ Chatwork notification sent!")
    except Exception as e:
        print(f"❌ Failed to send Chatwork notification: {e}")
