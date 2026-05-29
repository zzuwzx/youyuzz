#!/bin/bash
# ==============================================================
#  鱿郁仔仔 — NAS 定时清理脚本
#  用途：每日清理 30 天过期的游戏缓存文件
#  部署：crontab -e → 0 3 * * * /path/to/nas_cleanup.sh
# ==============================================================

set -euo pipefail

# ---- 配置 ----
CACHE_DIR="${YOUCUZZ_CACHE_DIR:-/volume1/youyuzz/cache}"
LOG_FILE="${YOUCUZZ_LOG:-/var/log/youyuzz_cleanup.log}"
MAX_AGE_DAYS=30
DRY_RUN=false

# ---- 日志函数 ----
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ---- 参数解析 ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --cache-dir) CACHE_DIR="$2"; shift 2 ;;
        --max-age) MAX_AGE_DAYS="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ---- 主逻辑 ----
log "=========================================="
log "鱿郁仔仔 NAS 缓存清理开始"
log "缓存目录: $CACHE_DIR"
log "过期天数: $MAX_AGE_DAYS"
log "Dry Run:  $DRY_RUN"
log "=========================================="

if [[ ! -d "$CACHE_DIR" ]]; then
    log "缓存目录不存在，跳过清理"
    exit 0
fi

# 统计清理前空间
before_size=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
log "清理前缓存大小: $before_size"

# 查找并删除过期游戏文件
deleted=0
while IFS= read -r -d '' file; do
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] 将删除: $file"
    else
        rm -f "$file"
        log "已删除: $file"
    fi
    ((deleted++))
done < <(find "$CACHE_DIR" -type f -mtime +"$MAX_AGE_DAYS" \( -name "*.nsp" -o -name "*.nsz" -o -name "*.zip" -o -name "*.rar" \) -print0 2>/dev/null)

if [[ "$deleted" -eq 0 ]]; then
    log "没有发现过期文件"
else
    log "共处理 $deleted 个过期文件"
fi

# 清理空目录
if [[ "$DRY_RUN" != "true" ]]; then
    find "$CACHE_DIR" -type d -empty -delete 2>/dev/null || true
fi

# 统计清理后空间
after_size=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
log "清理后缓存大小: $after_size"

# 清理 metadata.json 中过期条目
metadata_file="$CACHE_DIR/metadata.json"
if [[ -f "$metadata_file" ]] && command -v python3 &>/dev/null; then
    python3 -c "
import json, sys, time
from pathlib import Path

metadata = Path('$metadata_file')
if not metadata.exists():
    sys.exit(0)

data = json.loads(metadata.read_text(encoding='utf-8'))
now = time.time()
max_age = $MAX_AGE_DAYS * 86400

cleaned = {k: v for k, v in data.items() 
           if now - v.get('created_at', now) < max_age}

removed = len(data) - len(cleaned)
if removed > 0:
    metadata.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'清理了 {removed} 条过期元数据')
" 2>/dev/null || true
fi

log "=========================================="
log "清理完成"
log "=========================================="