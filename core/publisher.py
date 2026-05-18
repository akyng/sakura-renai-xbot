import tweepy
from config import Config

class XPublisher:
    def __init__(self):
        # 設定のバリデーションを実行
        Config.validate()
        
        # Tweepy Client の初期化 (API v2 を使用)
        self.client = tweepy.Client(
            consumer_key=Config.API_KEY,
            consumer_secret=Config.API_KEY_SECRET,
            access_token=Config.ACCESS_TOKEN,
            access_token_secret=Config.ACCESS_TOKEN_SECRET
        )
        
    def publish_thread(self, tweets: list) -> list:
        """
        ツイートのリストを受け取り、スレッド形式で連続投稿します。
        戻り値として、投稿されたツイートのIDリストを返します。
        """
        if not tweets:
            print("⚠️ No tweets to publish. Skipping.")
            return []
            
        published_ids = []
        last_tweet_id = None
        
        mode = Config.PUBLISH_MODE
        print(f"📣 Publishing thread (Mode: {mode}) consisting of {len(tweets)} tweets...")
        
        for idx, tweet_text in enumerate(tweets):
            print(f"\n--- Post #{idx + 1} ({len(tweet_text)} chars) ---")
            print(tweet_text)
            print("---------------------------------")
            
            if mode == 'dryrun':
                # テストモードの場合は投稿をシミュレート
                simulated_id = f"simulated_tweet_id_{idx + 1}"
                published_ids.append(simulated_id)
                last_tweet_id = simulated_id
                print(f"🧬 [DryRun] Simulated post success. ID: {simulated_id}")
            else:
                # 本番APIモードの場合は実際にXにポスト
                try:
                    if last_tweet_id is None:
                        # 最初のツイート（スレッドの親）を投稿
                        response = self.client.create_tweet(text=tweet_text)
                    else:
                        # 2番目以降のツイート（前のツイートへの返信としてスレッドを繋げる）
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
                    # スレッドが途中でちぎれないよう、エラーが発生した場合は実行を中断
                    break
                except Exception as e:
                    print(f"❌ Unexpected Error on post #{idx + 1}: {e}")
                    break
                    
        return published_ids
