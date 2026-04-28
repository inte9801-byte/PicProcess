# undo_manager.py
# PicProcess ver 1.0
# 功能：記錄操作動作、執行還原

import os
import shutil


class UndoManager:
    """
    管理本次執行的所有檔案移動記錄
    程式關閉後清除，僅限當次 session 有效
    """

    def __init__(self):
        self.action_table = []  # 動作清單

    def record(self, original_path, moved_to_path):
        """記錄一筆移動動作"""
        self.action_table.append({
            'original': original_path,
            'moved_to': moved_to_path
        })

    def can_undo(self):
        """是否有可還原的動作"""
        return len(self.action_table) > 0

    def undo_all(self):
        """
        還原所有動作：把所有檔案搬回原始位置
        回傳：(成功數, 失敗數, 失敗清單)
        """
        success = 0
        failed = 0
        failed_list = []

        # 反向還原（後移動的先還原）
        for action in reversed(self.action_table):
            original = action['original']
            moved_to = action['moved_to']

            try:
                # 確認目前檔案還在移動後的位置
                if not os.path.exists(moved_to):
                    failed += 1
                    failed_list.append(f"找不到檔案：{moved_to}")
                    continue

                # 還原：建立原始資料夾（如果不存在）
                original_dir = os.path.dirname(original)
                os.makedirs(original_dir, exist_ok=True)

                # 安全移回原位
                shutil.copy2(moved_to, original)
                if os.path.exists(original):
                    os.remove(moved_to)
                    success += 1
                else:
                    failed += 1
                    failed_list.append(f"還原失敗：{original}")

            except Exception as e:
                failed += 1
                failed_list.append(f"錯誤：{moved_to} → {str(e)}")

        # 還原完畢後清空動作清單
        self.action_table.clear()
        return success, failed, failed_list

    def get_summary(self):
        """回傳目前記錄的動作數量摘要"""
        return len(self.action_table)


# ── 測試區 ────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    print("=== UndoManager 測試 ===")

    # 建立暫時測試環境
    with tempfile.TemporaryDirectory() as tmpdir:
        # 建立測試檔案
        src = os.path.join(tmpdir, "test_photo.jpg")
        dest_folder = os.path.join(tmpdir, "2025-04-28")
        os.makedirs(dest_folder)

        with open(src, 'w') as f:
            f.write("fake image content")

        dest = os.path.join(dest_folder, "test_photo.jpg")

        # 模擬移動
        shutil.copy2(src, dest)
        os.remove(src)

        # 記錄動作
        undo = UndoManager()
        undo.record(src, dest)
        print(f"  記錄動作數：{undo.get_summary()}")
        print(f"  可還原：{undo.can_undo()}")

        # 執行還原
        print("\n  執行還原...")
        s, f, fl = undo.undo_all()
        print(f"  成功：{s}　失敗：{f}")

        # 確認檔案回到原位
        if os.path.exists(src):
            print(f"  ✅ 檔案已還原至原始位置")
        else:
            print(f"  ❌ 還原失敗")

        print(f"  還原後動作清單數量：{undo.get_summary()}")

    print("\n✅ undo_manager.py 測試完成")