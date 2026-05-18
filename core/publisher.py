import tweepy
import os
import random
from config import Config

class XPublisher:
    def __init__(self):
        # 設定のバリデーションを実行
        Config.validate()
        
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
        
    def publish_thread(self, tweets: list) -> list:
        """
        ツイートのリストを受け取り、スレッド形式で連続投稿します。
        最初のツイートには、画像があれば自動的に添付して投稿します。
        """
        if not tweets:
            print("⚠️ No tweets to publish. Skipping.")
            return []
            
        published_ids = []
        last_tweet_id = None
        
        mode = Config.PUBLISH_MODE
        print(f"📣 Publishing thread (Mode: {mode}) consisting of {len(tweets)} tweets...")
        
        # ランダム画像の取得を試みる
        image_path = self.get_random_image()
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
