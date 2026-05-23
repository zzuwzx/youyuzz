import os
import sys
from datetime import datetime, timedelta

BASE_DIR = r"C:\Users\wzxxx\Documents\switch 双系统自动化"
DEVLOG_DIR = os.path.join(BASE_DIR, "devlog")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def get_log_path(date=None):
    """Get the devlog file path for a given date (defaults to today)."""
    if date is None:
        date = datetime.now()
    year_dir = os.path.join(DEVLOG_DIR, str(date.year))
    month_dir = os.path.join(year_dir, f"{date.month:02d}")
    filename = f"{date.strftime('%Y-%m-%d')}.md"
    ensure_dir(month_dir)
    return os.path.join(month_dir, filename)

def create_daily_log():
    """Create today's devlog if it doesn't exist, with a template."""
    today = datetime.now()
    path = get_log_path(today)

    if os.path.exists(path):
        print(f"[SKIP] {path} already exists")
        return path

    # Check yesterday's log for carry-over todos
    yesterday = today - timedelta(days=1)
    yesterday_path = get_log_path(yesterday)
    carry_over = ""
    if os.path.exists(yesterday_path):
        with open(yesterday_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Extract unchecked todos from yesterday
        unchecked = [line for line in content.split("\n") if line.strip().startswith("- [ ]")]
        if unchecked:
            carry_over = "## 🔄 昨日未完成\n\n" + "\n".join(unchecked) + "\n\n"

    template = f"""# 开发日志 — {today.strftime('%Y-%m-%d')} ({['周一','周二','周三','周四','周五','周六','周日'][today.weekday()]})

---

## ✅ 今日完成

- [ ] 

## 📋 待办事项

- [ ] 

{carry_over}## 📝 备注

> 
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"[CREATED] {path}")
    return path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--view":
        today_path = get_log_path()
        if os.path.exists(today_path):
            with open(today_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print(f"No devlog for today yet. Run without --view to create.")
    else:
        create_daily_log()
