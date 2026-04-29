# main.py
# PicProcess ver 1.1 入口檔案

import sys
from ui import launch

def main():
    try:
        # 啟動圖形介面主程式
        launch()
    except KeyboardInterrupt:
        # 處理使用者在終端機按下 Ctrl+C 的情況
        print("\n[系統訊息] 程式已由使用者關閉。")
        sys.exit(0)
    except Exception as e:
        # 捕捉啟動時可能發生的未預期錯誤
        print(f"\n[系統錯誤] 程式啟動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()