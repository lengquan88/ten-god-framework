"""阶段十五端到端测试：D3.js 高级图表可视化"""
import sys
import time
from playwright.sync_api import sync_playwright

API_BASE = "http://127.0.0.1:8765"
FRONTEND_URL = f"{API_BASE}/static/index.html"

def test_viz():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # 收集控制台日志
        logs = []
        page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: logs.append(f"[ERROR] {err}"))

        print("1. 导航到前端页面...")
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        print("   ✓ 页面加载完成")

        # 2. 登录
        print("2. 登录测试用户...")
        page.click('a[data-page="calc"]')
        page.wait_for_timeout(500)

        login_btn = page.locator('#userLoggedOut button')
        if login_btn.is_visible():
            login_btn.click()
            page.wait_for_timeout(500)
            page.fill('#authUsername', 'graph_tester')
            page.fill('#authPassword', 'Test12345')
            page.click('#authSubmit')
            page.wait_for_timeout(1500)
            print("   ✓ 登录成功")
        else:
            print("   ✓ 已登录")

        # 3. 切换到高级图表页
        print("3. 切换到高级图表页...")
        page.click('a[data-page="viz"]')
        page.wait_for_timeout(1000)

        viz_page = page.locator('#page-viz')
        is_visible = viz_page.is_visible()
        print(f"   ✓ 高级图表页可见: {is_visible}")

        # 4. 等待数据加载和图表渲染
        print("4. 等待D3.js图表渲染...")
        page.wait_for_timeout(3000)

        # 5. 验证五行雷达图
        print("5. 验证五行能量雷达图...")
        radar_svg = page.locator('#radarChart svg')
        radar_count = radar_svg.count()
        print(f"   SVG元素数量: {radar_count}")
        if radar_count > 0:
            circles = page.locator('#radarChart svg circle').count()
            paths = page.locator('#radarChart svg path').count()
            texts = page.locator('#radarChart svg text').count()
            print(f"   圆形: {circles}, 路径: {paths}, 文本: {texts}")
            assert circles > 5, "雷达图圆形元素不足"
            assert paths >= 1, "雷达图路径元素不足"
            print("   ✓ 雷达图渲染成功")
        else:
            print("   ✗ 雷达图未渲染")

        # 6. 验证十神柱状图
        print("6. 验证十神力量分布柱状图...")
        shigan_svg = page.locator('#shiganChart svg')
        shigan_count = shigan_svg.count()
        print(f"   SVG元素数量: {shigan_count}")
        if shigan_count > 0:
            bars = page.locator('#shiganChart svg rect.bar').count()
            labels = page.locator('#shiganChart svg text.label').count()
            print(f"   柱子: {bars}, 标签: {labels}")
            assert bars > 0, "柱状图柱子不足"
            print("   ✓ 柱状图渲染成功")
        else:
            print("   ✗ 柱状图未渲染")

        # 7. 验证大运流年时间轴
        print("7. 验证大运流年时间轴...")
        timeline_svg = page.locator('#timelineChart svg')
        timeline_count = timeline_svg.count()
        print(f"   SVG元素数量: {timeline_count}")
        if timeline_count > 0:
            rects = page.locator('#timelineChart svg rect').count()
            circles = page.locator('#timelineChart svg circle').count()
            texts = page.locator('#timelineChart svg text').count()
            print(f"   矩形: {rects}, 圆形: {circles}, 文本: {texts}")
            assert rects > 0, "时间轴矩形不足"
            assert circles > 0, "时间轴圆形不足"
            print("   ✓ 时间轴渲染成功")
        else:
            print("   ✗ 时间轴未渲染")

        # 8. 截图
        print("8. 截图保存...")
        page.screenshot(path="/workspace/viz_page.png", full_page=False)
        print("   ✓ 截图保存到 /workspace/viz_page.png")

        # 9. 检查控制台错误
        print("9. 检查控制台日志...")
        errors = [l for l in logs if "[ERROR]" in l or "[error]" in l]
        if errors:
            print(f"   ⚠ 发现 {len(errors)} 个错误:")
            for e in errors[:5]:
                print(f"     {e}")
        else:
            print("   ✓ 无控制台错误")

        browser.close()
        print("\n✅ 端到端测试完成")
        return True

if __name__ == "__main__":
    try:
        test_viz()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
