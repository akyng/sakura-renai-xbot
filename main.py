#!/usr/bin/env python3
import os
import sys
import json

# Add project root to sys.path to ensure correct imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from core.generator import ContentGenerator
from core.utils import split_thread, send_chatwork_notification
from core.publisher import XPublisher

STATE_FILE = os.path.join(os.path.dirname(__file__), 'state.json')

def load_state() -> dict:
    """
    state.json から現在のローテーションインデックスをロードします。
    """
    default_state = {"categories": [1, 2, 3, 4, 5, 6, 7], "current_index": 0}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                # 必要なキーがあることを保証
                if "categories" in state and "current_index" in state:
                    return state
        except Exception as e:
            print(f"⚠️ State load failed, using default: {e}")
    return default_state

def save_state(state: dict):
    """
    現在のローテーションインデックスを state.json に保存します。
    """
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"💾 State saved successfully: Index {state['current_index']}")
    except Exception as e:
        print(f"❌ State save failed: {e}")

def main():
    print("===========================================================")
    print("      🌸 --- 恋AIモードXbot 起動開始 --- 🌸         ")
    print("      -- 恋愛心理学＆会話術 24/7 自動投稿エンジン -- ")
    print("===========================================================")

    # 1. 環境変数の検証
    try:
        Config.validate()
        print("✅ Environment configuration successfully validated.")
    except Exception as e:
        print(f"❌ Configuration Validation Error: {e}")
        print("⚠️ .env ファイルが未作成、またはキーが不足しています。")
        sys.exit(1)

    # 2. ローテーション状態のロード
    state = load_state()
    categories = state.get("categories", [1, 2, 3, 4, 5, 6, 7])
    current_idx = state.get("current_index", 0)

    # 安全対策：インデックス範囲外の修正
    if current_idx >= len(categories):
        current_idx = 0

    active_category = categories[current_idx]
    print(f"📊 ローテーション順次実行: カテゴリ {active_category} (全 {len(categories)} テーマ)")

    # 3. Geminiによる恋愛考察スレッド原稿の生成
    try:
        generator = ContentGenerator()
        raw_text = generator.generate_romance_thread(active_category)
        
        if not raw_text:
            err_msg = "AI content generation returned empty. Aborting."
            print(f"❌ {err_msg}")
            send_chatwork_notification(f"[info][title]🔴 【さくら】AI生成失敗[/title]テーマカテゴリ {active_category} の生成結果が空文字でした。[/info]")
            sys.exit(1)
            
    except Exception as e:
        err_msg = f"AI Generation Engine failed: {e}"
        print(f"❌ {err_msg}")
        send_chatwork_notification(f"[info][title]🔴 【さくら】AI生成エンジン異常[/title]エラー詳細:\n{err_msg}[/info]")
        sys.exit(1)

    # 4. 文字数カウントとツリー分割
    print("✂️ Splitting thread...")
    # すべての投稿の末尾にアプリダウンロード用のスマートリンクを必ず掲載！
    tweets = split_thread(raw_text, cta_url=Config.APP_URL)
    
    if not tweets:
        err_msg = "Thread splitting failed or returned no text. Aborting."
        print(f"❌ {err_msg}")
        send_chatwork_notification(f"[info][title]🔴 【さくら】スレッド分割失敗[/title]生成された原稿の分割処理に失敗しました。[/info]")
        sys.exit(1)

    # 5. X (Twitter) への連投ポスト配信
    try:
        publisher = XPublisher()
        published_ids = publisher.publish_thread(tweets)
        
        if len(published_ids) == len(tweets):
            print("🎉 Thread successfully published all tweets!")
            
            # 6. 成功時のみローテーション状態を進めてセーブ
            next_idx = (current_idx + 1) % len(categories)
            state["current_index"] = next_idx
            save_state(state)
            
            print(f"➡️ 次回実行カテゴリ: カテゴリ {categories[next_idx]}")
            
            # Chatwork 成功通知！
            thread_preview = "\n\n---\n\n".join(tweets)
            msg = (
                "[info][title]🌸 【さくら】自動投稿成功！[/title]"
                f"動作モード: {Config.PUBLISH_MODE.upper()}\n"
                f"実行テーマカテゴリ: {active_category}\n\n"
                f"【投稿スレッド内容】\n{thread_preview}[/info]"
            )
            send_chatwork_notification(msg)
        else:
            print("⚠️ Thread was partially published or failed midway. Rotation index preserved.")
            msg = (
                "[info][title]⚠️ 【さくら】スレッドの一部投稿失敗[/title]"
                f"動作モード: {Config.PUBLISH_MODE.upper()}\n"
                f"期待した投稿数: {len(tweets)} 件\n"
                f"実際の投稿数: {len(published_ids)} 件\n\n"
                "※投稿処理中にエラーが発生したため、一部のツイートのみ投稿され、ローテーションは維持されました。[/info]"
            )
            send_chatwork_notification(msg)
            
    except Exception as e:
        err_msg = f"Publishing Engine error: {e}"
        print(f"❌ {err_msg}")
        msg = (
            "[info][title]🔴 【さくら】投稿エンジンで予期せぬエラー[/title]"
            f"動作モード: {Config.PUBLISH_MODE.upper()}\n"
            f"実行テーマカテゴリ: {active_category}\n\n"
            f"❌ エラー内容:\n{err_msg}[/info]"
        )
        send_chatwork_notification(msg)
        sys.exit(1)

    print("\n🎉 Process execution completed successfully!")

if __name__ == "__main__":
    main()
