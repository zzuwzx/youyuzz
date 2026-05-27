"""
简单的图标生成脚本
使用 PIL 创建一个基本的应用图标
"""
from PIL import Image, ImageDraw
import os

def create_icon(output_path, size=256):
    """创建一个简单的应用图标"""
    # 创建图像 (带透明背景)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制背景圆形
    margin = size // 16
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(26, 26, 46, 255),  # #1A1A2E
        outline=(233, 69, 96, 255),  # #E94560
        width=size // 32
    )
    
    # 绘制中心图案 (简化的 Switch 图标)
    center = size // 2
    radius = size // 4
    
    # 左侧圆点
    left_x = center - radius // 2
    draw.ellipse(
        [left_x - radius//3, center - radius//3, left_x + radius//3, center + radius//3],
        fill=(0, 200, 83, 255)  # #00C853
    )
    
    # 右侧圆点
    right_x = center + radius // 2
    draw.ellipse(
        [right_x - radius//3, center - radius//3, right_x + radius//3, center + radius//3],
        fill=(233, 69, 96, 255)  # #E94560
    )
    
    # 中间横线
    line_width = size // 20
    draw.rectangle(
        [center - radius, center - line_width//2, center + radius, center + line_width//2],
        fill=(224, 224, 224, 255)  # #E0E0E0
    )
    
    # 保存为多种尺寸的 ICO
    sizes = [16, 32, 48, 256]
    images = []
    
    for s in sizes:
        if s == size:
            images.append(img)
        else:
            images.append(img.resize((s, s), Image.Resampling.LANCZOS))
    
    # 保存 ICO 文件
    img.save(
        output_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    
    print(f"[OK] Icon created: {output_path}")
    return True

if __name__ == "__main__":
    # 确保目录存在
    os.makedirs("pc-client\\backend", exist_ok=True)
    os.makedirs("pc-client\\frontend\\assets", exist_ok=True)
    
    # 创建后端图标
    backend_icon = r"pc-client\backend\icon.ico"
    create_icon(backend_icon)
    
    # 创建前端图标
    frontend_icon = r"pc-client\frontend\assets\icon.ico"
    create_icon(frontend_icon)
    
    print("\n[OK] All icon files created successfully")
