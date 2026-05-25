import tweepy
import os
import random
from config import Config

class XPublisher:
    def __init__(self):
        # 設定のバリデーションを実行
        Config.validate()
        
        # APIモードのときのみ Tweepy を初期化
        if Config.PUBLISH_MODE == 'api':
            # Tweepy Client (API v2) - ツイート本文投稿用
            self.client = tweepy.Client(
                consumer_key=Config.API_KEY,
                consumer_secret=Config.API_KEY_SECRET,
                access_token=Config.ACCESS_TOKEN,
                access_token_secret=Config.ACCESS_TOKEN_SECRET
            )
            
            # Tweepy API (API v1.1) - メディア（画像）アップロード用
            auth = tweepy.OAuth1UserHandler(
                consumer_key=Config.API_KEY,
                consumer_secret=Config.API_KEY_SECRET,
                access_token=Config.ACCESS_TOKEN,
                access_token_secret=Config.ACCESS_TOKEN_SECRET
            )
            self.api = tweepy.API(auth)
        else:
            self.client = None
            self.api = None
        
    def get_random_image(self) -> str:
        """
        images/ フォルダ内からランダムな画像ファイル（png, jpg, jpeg, gif）を取得します。
        """
        images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images')
        if not os.path.exists(images_dir):
            return None
            
        valid_extensions = ('.png', '.jpg', '.jpeg', '.gif')
        try:
            images = [
                os.path.join(images_dir, f) 
                for f in os.listdir(images_dir) 
                if f.lower().endswith(valid_extensions)
            ]
            if images:
                return random.choice(images)
        except Exception as e:
            print(f"⚠️ Error reading images directory: {e}")
        return None
        
    def _publish_browser(self, tweets: list, image_path: str = None) -> list:
        import threading
        result_box = {}
        
        def worker():
            try:
                result_box["result"] = self._publish_browser_internal(tweets, image_path)
            except Exception as e:
                result_box["error"] = e
                
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        
        if "error" in result_box:
            raise result_box["error"]
        return result_box["result"]

    def _publish_browser_internal(self, tweets: list, image_path: str = None) -> list:
        """
        Playwright (ブラウザ自動化) による連続投稿 (スレッド対応・画像添付対応) の内部処理
        """
        from playwright.sync_api import sync_playwright
        import time
        import os
        import json
        
        cookie_path = Config.X_COOKIE_PATH
        print(f"[*] Playwrightブラウザ自動化を使用してさくらスレッド投稿処理を開始 (クッキー: {cookie_path})...")
        
        # クッキーの存在チェック
        if not os.path.exists(cookie_path):
            import sys
            is_interactive = sys.stdin.isatty() and os.getenv("GITHUB_ACTIONS") != "true"
            if not is_interactive:
                raise FileNotFoundError(
                    f"❌ クッキーファイル '{cookie_path}' が存在しません。\n"
                    f"非インタラクティブ環境（GitHub Actions 等）では自動ログインを実行できません。\n"
                    f"ローカル環境で 'generate_cookies.py' を実行してクッキーファイルを生成し、\n"
                    f"GitHub のリポジトリシークレット (X_COOKIE_JSON) を更新してください。"
                )
                
            print(f"[!] クッキーファイル '{cookie_path}' が見つかりません。")
            print("[*] ログインセッションを作成するため、ブラウザ(UIあり)を起動します。")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                page.goto("https://x.com/i/flow/login")
                
                print("\n" + "!"*60)
                print("【手動操作のお願い：さくら用】")
                print("開いたブラウザ画面でXへのログインを完了させてください。")
                print("ログイン後、Xのホーム画面（タイムライン）が表示されたら、")
                print("こちらのターミナルに戻り、[Enter] キーを押してください。")
                print("!"*60 + "\n")
                
                input("ログイン完了後にEnterキーを押してください...")
                
                # クッキーを保存
                cookies = context.cookies()
                with open(cookie_path, "w", encoding="utf-8") as f:
                    json.dump(cookies, f)
                print(f"[+] クッキーを '{cookie_path}' に保存しました。")
                browser.close()
                
        # ヘッドレスモードでの自動投稿
        print("[*] 自動投稿を実行中...")
        published_ids = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            
            # 保存したクッキーを読み込んでPlaywright用にサニタイズ
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            cleaned_cookies = []
            for c in cookies:
                # sameSiteが想定外の値の場合はPlaywrightの仕様(Strict, Lax, None)に合わせて修正
                if "sameSite" in c:
                    val = c["sameSite"]
                    if val is None or str(val).lower() in ["no_restriction", "none"]:
                        c["sameSite"] = "None"
                    elif str(val).lower() == "lax":
                        c["sameSite"] = "Lax"
                    elif str(val).lower() == "strict":
                        c["sameSite"] = "Strict"
                    else:
                        # 予期しない値はエラー防止のため削除
                        del c["sameSite"]
                cleaned_cookies.append(c)
                
            context.add_cookies(cleaned_cookies)
            
            page = context.new_page()
            page.set_default_timeout(45000) # 安定性のためにタイムアウトを45秒に設定
            
            try:
                # 直接ポスト作成画面に遷移
                page.goto("https://x.com/compose/post")
                time.sleep(3)
                
                # ログイン状態の検証
                if "login" in page.url or "i/flow" in page.url:
                    print("[!] ログインクッキーが失効している可能性があります。")
                    browser.close()
                    
                    import sys
                    is_interactive = sys.stdin.isatty() and os.getenv("GITHUB_ACTIONS") != "true"
                    if not is_interactive:
                        raise ValueError(
                            f"❌ Xへのログインセッション（クッキー）が失効しています。\n"
                            f"非インタラクティブ環境（GitHub Actions 等）では手動再ログインを起動できません。\n"
                            f"ローカル環境で 'generate_cookies.py' を実行してクッキーを再生成し、\n"
                            f"GitHub のリポジトリシークレット (X_COOKIE_JSON) を最新のクッキー情報に更新してください。"
                        )
                        
                    # クッキーファイルを削除して手動ログインから再試行
                    if os.path.exists(cookie_path):
                        os.remove(cookie_path)
                    return self._publish_browser(tweets, image_path)
                
                # 投稿エリアが表示されるのを待つ
                page.wait_for_selector('div[role="dialog"] [data-testid="tweetTextarea_0"]', timeout=30000)
                time.sleep(2)
                
                # 1. 最初のポスト入力と画像添付
                textboxes = page.query_selector_all('div[role="dialog"] [data-testid="tweetTextarea_0"]')
                if not textboxes:
                    raise Exception("投稿入力エリアが見つかりません。")
                
                # 画像添付 (最初のポストに添付)
                if image_path and os.path.exists(image_path):
                    print(f"[*] 初回ポストに画像を添付中: {os.path.basename(image_path)}")
                    # Xの隠しファイルインプット要素にファイルをセット
                    page.set_input_files('input[data-testid="fileInput"]', image_path)
                    time.sleep(5)  # 画像のアップロード完了まで待機
                
                print("[*] 1つ目のポストを入力中...")
                first_textbox = page.locator('div[role="dialog"] [data-testid="tweetTextarea_0"]').first
                first_textbox.wait_for(timeout=15000)
                first_textbox.click()
                time.sleep(1)
                first_textbox.focus()
                time.sleep(1)
                page.keyboard.type(tweets[0])
                time.sleep(1)
                
                # 🌟 ハッシュタグ補完ドロップダウンと透明な傍受レイヤーを閉じるために Escape を送信（テキストにハッシュタグが含まれる場合のみ）
                if any("#" in t for t in tweets[:1]):
                    print("[*] ハッシュタグ自動補完オーバーレイを閉じるため Escape キーを送信中...")
                    page.keyboard.press("Escape")
                    time.sleep(1)
                
                # 2. スレッド（2つ目以降のツイート）の追加
                for idx, tweet_text in enumerate(tweets[1:], start=1):
                    print(f"[*] 返信ツリー（子ポスト #{idx+1}）を追加中...")
                    # 「スレッド追加 (＋)」ボタンをダイアログ内に限定して取得
                    add_button = page.locator('div[role="dialog"] [data-testid="addButton"]').first
                    add_button.wait_for(timeout=10000)
                    
                    # 🌟 ボタンが disabled もしくは aria-disabled="true" かチェックして React クラッシュを防ぐ
                    is_disabled = add_button.evaluate('node => node.disabled || node.getAttribute("aria-disabled") === "true"')
                    if is_disabled:
                        raise Exception("スレッド追加ボタン（addButton）が無効化されています。入力テキストがXの制限文字数（日本語140文字）を超過している可能性があります。")
                        
                    add_button.click(force=True)  # 物理クリック＋オーバーレイ強制突破
                    print("[*] スレッド追加ボタンをクリックしました。")
                    time.sleep(3)
                    
                    current_textbox = page.locator(f'div[role="dialog"] [data-testid="tweetTextarea_{idx}"]').first
                    current_textbox.wait_for(timeout=10000)
                    print(f"[*] 子ポスト #{idx+1} を入力中... (ダイアログ内の [data-testid=\"tweetTextarea_{idx}\"] を検出)")
                    current_textbox.click()
                    time.sleep(1)
                    current_textbox.focus()
                    time.sleep(1)
                    page.keyboard.type(tweet_text)
                    time.sleep(1)
                
                # URLリンクプレビュー解析のために長めの待機時間を確保
                print("[*] リンクプレビュー解析のため8秒間待機中...")
                time.sleep(8)
                
                # 3. 送信ボタンをクリックと送信完了の待ち合わせ (最大4回のインテリジェントリトライ)
                modal_closed = False
                for attempt in range(4):
                    print(f"[*] ポストスレッドを送信中... (試行 {attempt + 1}/4)")
                    post_button = page.locator('div[role="dialog"] [data-testid="tweetButton"]').first
                    post_button.wait_for(timeout=10000)
                    post_button.click(force=True)
                    
                    try:
                        # 投稿テキストエリアが画面から消える（送信成功）のを5秒監視
                        page.locator('div[role="dialog"] [data-testid="tweetTextarea_0"]').first.wait_for(state="hidden", timeout=5000)
                        print("[✔] 投稿モーダルが閉じられたことを確認しました！")
                        modal_closed = True
                        break
                    except Exception:
                        print("[!] 5秒以内にモーダルが閉じなかったため、再送信を試みます。")
                
                if not modal_closed:
                    raise Exception("送信ボタンをクリックしましたが、モーダルが閉じられず送信を完了できませんでした。")
                
                time.sleep(5)  # 最終的な送信バッファ待機
                
                print("[+] Xへのブラウザ自動スレッド投稿が完了しました！")
                # 返却用にダミーIDを作成
                published_ids = [f"browser_tweet_id_{i+1}" for i in range(len(tweets))]
                
            except Exception as e:
                print(f"[Error] ブラウザ自動投稿中にエラーが発生しました: {e}")
                # スクリーンショットを保存してエラー原因解析を容易にする
                try:
                    error_img = "publish_error_sakura_screenshot.png"
                    page.screenshot(path=error_img)
                    print(f"[!] エラー画面のスクリーンショットを '{error_img}' に保存しました。")
                except Exception:
                    pass
                raise e
            finally:
                browser.close()
                
        return published_ids

    def publish_thread(self, tweets: list) -> list:
        """
        ツイートのリストを受け取り、スレッド形式で連続投稿します。
        最初のツイートには、画像があれば自動的に添付して投稿します。
        """
        if not tweets:
            print("⚠️ No tweets to publish. Skipping.")
            return []
            
        mode = Config.PUBLISH_MODE
        print(f"📣 Publishing thread (Mode: {mode}) consisting of {len(tweets)} tweets...")
        
        # ランダム画像の取得を試みる
        image_path = self.get_random_image()
        
        # ブラウザ自動投稿モードの場合
        if mode == 'browser':
            try:
                published_ids = self._publish_browser(tweets, image_path)
                return published_ids
            except Exception as e:
                print(f"❌ X Browser Publishing Error: {e}")
                return []
                
        published_ids = []
        last_tweet_id = None
        media_id = None
        
        if image_path:
            print(f"📸 Found image to upload: {os.path.basename(image_path)}")
            if mode != 'dryrun':
                try:
                    # v1.1 API を使って画像をアップロード
                    media = self.api.media_upload(filename=image_path)
                    media_id = media.media_id_string
                    print(f"⚡ Image upload success! Media ID: {media_id}")
                except Exception as e:
                    print(f"❌ Image upload failed: {e}")
                    
        for idx, tweet_text in enumerate(tweets):
            print(f"\n--- Post #{idx + 1} ({len(tweet_text)} chars) ---")
            print(tweet_text)
            print("---------------------------------")
            
            if mode == 'dryrun':
                # テストモード
                simulated_id = f"simulated_tweet_id_{idx + 1}"
                published_ids.append(simulated_id)
                last_tweet_id = simulated_id
                if idx == 0 and image_path:
                    print(f"🧬 [DryRun] Attached simulated image: {os.path.basename(image_path)}")
                print(f"🧬 [DryRun] Simulated post success. ID: {simulated_id}")
            else:
                # 本番API
                try:
                    if last_tweet_id is None:
                        # 最初のツイート（画像があれば添付して投稿）
                        if media_id:
                            response = self.client.create_tweet(
                                text=tweet_text,
                                media_ids=[media_id]
                            )
                        else:
                            response = self.client.create_tweet(text=tweet_text)
                    else:
                        # 2枚目以降のスレッド返信
                        response = self.client.create_tweet(
                            text=tweet_text,
                            in_reply_to_tweet_id=last_tweet_id
                        )
                        
                    tweet_id = response.data['id']
                    published_ids.append(tweet_id)
                    last_tweet_id = tweet_id
                    print(f"✅ Live Post Success! Tweet ID: {tweet_id}")
                    
                except tweepy.TweepyException as e:
                    print(f"❌ X API Error on post #{idx + 1}: {e}")
                    break
                except Exception as e:
                    print(f"❌ Unexpected Error on post #{idx + 1}: {e}")
                    break
                    
        return published_ids
