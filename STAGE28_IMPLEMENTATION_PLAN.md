# 阶段二十八：高级可视化 — 技术实现方案

> 目标：打造差异化视觉体验，提升产品竞争力（3D命盘/大运动画/五行实时流/图谱交互）
> 依赖：现有 `web_console/index.html`（八字数据）、`data_store.py`（命理数据）
> 预计工作量：2-3 人/周

---

## 28.0 架构总览

```
      浏览器
         │
         ▼
    HTML 入口页面
  (加载 Three.js / D3.js 库)
         │
   ┌─────┴─────┬──────┬──────┬──────┐
   ▼           ▼      ▼      ▼      ▼
  3D命盘      大运     五行     知识图谱 分享截图
Three.js    动画     实时流     (WebGL)   (Canvas→PNG)
 WebGL       D3       Canvas
```

---

## 28.1 3D 交互命盘（1天）

### 页面结构：`web_console/visualizations/3d-chart.html`

```
┌─ 顶部: 八字信息（日主:甲木 格局:正官格）
│
├─ 中央: 3D 命盘主视图（Three.js）
│  · 四柱以立体柱体呈现（天干在上层，地支在下层）
│  · 天干:甲/乙/丙/丁... 用立体字形+色彩（木=绿，火=红，土=黄，金=白，水=黑）
│  · 地支:子/丑/寅/卯... 用圆环/四面体/八面体等不同几何
│  · 五行能量球环绕中心，颜色随强度变化
│  · 十神关系用连线表示（比肩/劫财→白色，正官/七杀→红色，食神/伤官→黄色，正财/偏财→绿色，正印/偏印→蓝色）
│
└─ 底部: 交互控制
   [旋转] [缩放] [重置视角]
   [切换视图:正视图/俯视图/第一视角]
   [动画:自动旋转/暂停]
   [截屏分享]
```

### 关键技术参数

```
Three.js 场景:
  · Camera: PerspectiveCamera(fov=60, aspect, near=0.1, far=1000)
  · Lighting: AmbientLight + 3 DirectionalLights（模拟三维）
  · Renderer: WebGLRenderer({antialias: true, alpha: true})
  · Control: OrbitControls（鼠标拖拽旋转+滚轮缩放）
  · 使用: GLTFLoader（可选，加载3D模型替代几何体）

四柱渲染策略:
  · 每柱 = 天干（大立方体，带发光材质）+ 地支（大球体，带纹理）
  · 四柱位置: 左上=年柱，右上=月柱，左下=日柱，右下=时柱
  · 每柱内部: 五行属性用颜色表示，十神关系用发光连线

五行能量分布:
  · 五个能量球（金木水火土）围绕中心旋转
  · 半径 = 标准化五行计数 (0.5 ～ 2.0)
  · 颜色 = 五行对应颜色
```

### 简化实现方案

```javascript
// 核心代码结构
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

// 1. 创建四柱（天干 + 地支）
function createPillars(pillarsData) {
    // pillarsData = [{tiangan, dizhi, shigan, wuxing}, ...] × 4
    const group = new THREE.Group();
    pillarsData.forEach((p, i) => {
        const pillar = new THREE.Group();
        // 天干: 立方体
        const tianganGeo = new THREE.BoxGeometry(1.2, 1.2, 1.2);
        const tianganMat = new THREE.MeshPhongMaterial({ color: wuxingColor(p.tiangan) });
        pillar.add(new THREE.Mesh(tianganGeo, tianganMat));
        // 地支: 八面体
        const dizhiGeo = new THREE.OctahedronGeometry(0.9);
        const dizhiMat = new THREE.MeshPhongMaterial({ color: wuxingColor(p.dizhi) });
        pillar.add(new THREE.Mesh(dizhiGeo, dizhiMat));
        // 文本标签（使用 Canvas 贴图）
        pillar.add(createTextLabel(p.tiangan + "/" + p.dizhi));
        group.add(pillar);
    });
    return group;
}

// 2. 创建五行能量球（5个围绕中心旋转）
function createWuxingOrbit(wuxingData) {
    const orbit = new THREE.Group();
    // ...
}

// 3. 十神关系连线（从日柱天干画到其他三柱）
function createShiganLines(shiganData) {
    // ...
}

// 4. 动画循环
function animate() {
    requestAnimationFrame(animate);
    scene.rotation.y += 0.002;
    // 五行球继续旋转
    renderer.render(scene, camera);
}
animate();
```

---

## 28.2 大运流年动画时间轴（0.5天）

### 页面结构：`web_console/visualizations/luck-timeline.html`

```
┌─ 大运时间轴 ─────────────────────────────────────────────
│  (10岁)  (20岁)  (30岁)  (40岁)  (50岁)  (60岁)  (70岁)
│    │       │       │       │       │       │       │
│  辛酉大运  壬戌   癸亥   甲子   乙丑   丙寅   丁卯
│  [伤官]  [食神] [劫财] [比肩] [正印] [偏印] [正官]
│   ═══     ▆▆    ═══    ▆▆▆    ▆▆    ═══    ▆▆▆
│
└─ 流年刻度 (点击某年展开流年分析)
   [2020] [2021] [2022] [2023] [2024] [2025] [2026]
     ▾
   流年庚子:
     天干庚金, 地支子水
     日主甲木遇庚金七杀 → 注意职场挑战
     地支子水与日支申金 → 申子合水, 贵人助力
```

### D3.js 实现要点

```javascript
// 1. 时间轴绘制
const xScale = d3.scaleLinear().domain([startYear, endYear]).range([0, width]);
const axis = d3.axisBottom(xScale).ticks(endYear - startYear + 1).tickFormat(d => d + "岁");

// 2. 大运区块（每步10年，彩色条形）
dayunData.forEach((yun, i) => {
    const bar = g.append("rect")
        .attr("x", xScale(yun.start_age))
        .attr("width", xScale(yun.start_age + 10) - xScale(yun.start_age))
        .attr("y", 20)
        .attr("height", 40)
        .attr("fill", wuxingColor(yun.wuxing))
        .attr("opacity", 0.7)
        .on("click", () => showDayunDetail(yun));
});

// 3. 流年刻度（每年一条竖线）
const flowYears = d3.range(2020, 2030);
flowYears.forEach((year, i) => {
    g.append("line").attr("x1", xScale(ageAtYear(year))).attr("x2", xScale(ageAtYear(year)))
                     .attr("y1", 65).attr("y2", 75).attr("stroke", "#ccc");
});

// 4. 鼠标悬停交互：显示该流年干支 + 吉凶分数
const tooltip = d3.select("body").append("div").attr("class", "tooltip");
bar.on("mouseover", d => tooltip.text(d.ganzhi + ": " + d.jixiong_score).style("visibility", "visible"))
   .on("mouseout", () => tooltip.style("visibility", "hidden"));

// 5. 动画过渡：从第一个大运渐显到最后一个
bars.attr("opacity", 0)
    .transition().duration(300).delay((d, i) => i * 150).attr("opacity", 0.7);
```

---

## 28.3 五行实时动态流（0.5天）

### 页面结构：`web_console/visualizations/wuxing-flow.html`

```
┌─ 五行动态能量图 ────────────────────────────────
│                                                  │
│     (金) ══▶ (水) ══▶ (木) ══▶ (火) ══▶ (土)    │
│       ╲    ╱     ╲     ╱     ╲    ╱            │
│        ╲  ╱       ╲   ╱       ╲  ╱             │
│         ▼           ▼           ▼              │
│     金生水       水生木       木生火              │
│                                                  │
│     五行能量条:                                 │
│     ████████ 金 (8)                             │
│     ██████   水 (6)                             │
│     █████    木 (5)                             │
│     ████████ 火 (8)                             │
│     ████     土 (4)                             │
│                                                  │
└─────────────────────────────────────────────────┘

   动态更新: 能量根据季节/月份流动
```

### Canvas 动画实现

```javascript
// 核心: 粒子系统 + 五行生克路径
class WuxingFlow {
    constructor(canvasId, wuxingData) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext("2d");
        this.particles = this.createParticles(wuxingData);
        this.elements = this.createElements(wuxingData);
        this.start();
    }

    createParticles(wuxingData) {
        // 每种五行若干粒子，在对应位置随机生成，沿生克路径移动
        const particles = [];
        wuxingData.forEach((element, count) => {
            for (let i = 0; i < count * 20; i++) {
                particles.push({
                    element,
                    x: Math.random() * this.canvas.width,
                    y: Math.random() * this.canvas.height,
                    vx: (Math.random() - 0.5) * 2,
                    vy: (Math.random() - 0.5) * 2,
                    life: Math.random() * 200 + 100,
                });
            }
        });
        return particles;
    }

    render() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        // 绘制五行生克路径线
        this.elements.forEach(el => {
            this.ctx.beginPath();
            this.ctx.arc(el.x, el.y, el.radius, 0, Math.PI * 2);
            this.ctx.fillStyle = el.color;
            this.ctx.fill();
            this.ctx.font = "18px serif";
            this.ctx.fillStyle = "#fff";
            this.ctx.textAlign = "center";
            this.ctx.fillText(el.name, el.x, el.y + 5);
        });
        // 粒子沿生克方向移动
        this.particles.forEach(p => {
            p.x += p.vx; p.y += p.vy; p.life--;
            if (p.life <= 0) this.resetParticle(p);
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
            this.ctx.fillStyle = this.elementColor(p.element);
            this.ctx.fill();
        });
        requestAnimationFrame(() => this.render());
    }
}
```

---

## 28.4 知识图谱交互升级（0.5天）

### 页面结构：`web_console/visualizations/kg-explorer.html`

```
┌─ 知识图谱探索器 ──────────────────────────────────
│
│  搜索: [ 十神 / 五行 / 八卦 / 天干 ... ]        │
│
│  ┌─ 中心图区 (WebGL 加速 1000+ 节点) ──┐
│  │  节点 = 知识实体                   │
│  │  连线 = 关系 (五行生/克/十神关联)   │
│  │  点击节点 → 展开邻居               │
│  │  双击节点 → 进入子图谱             │
│  │  右键 → 截图/保存路径              │
│  └──────────────────────────────┘
│
│  └─ 右侧: 节点详情卡
│     名称: 正官
│     类别: 十神
│     定义: 克我且阴阳异
│     相关: 正财(生), 正印(生), 比肩(克)...
│     [在命盘中定位]
│
└─────────────────────────────────────────────────┘
```

### WebGL 加速渲染

```javascript
// 使用 regl 或 Three.js Points 绘制大量节点
class KGGraph {
    constructor(canvasId, nodes, links) {
        this.renderer = new THREE.WebGLRenderer({ canvas: document.getElementById(canvasId) });
        this.scene = new THREE.Scene();
        this.nodes = nodes.map(n => ({
            ...n,
            mesh: new THREE.Mesh(
                new THREE.SphereGeometry(n.category === "shigan" ? 0.5 : 0.3),
                new THREE.MeshBasicMaterial({ color: this.colorByCategory(n.category) })
            )
        }));
        this.links = links;
    }

    // 力导向布局（每帧更新节点位置）
    updateLayout() {
        // 简单库仑斥力 + 胡克力
        // ...
    }

    // 单击节点展开邻居
    onNodeClick(node) {
        fetch('/api/knowledge/neighbors?entity=' + node.name)
            .then(r => r.json())
            .then(neighbors => this.expandNode(node, neighbors));
    }

    // 路径高亮（查询 A→B 的最短路径时动画展示）
    highlightPath(path) {
        path.forEach(node => {
            node.mesh.material.emissive = new THREE.Color(0xffff00);
            // 闪烁动画
        });
    }
}
```

---

## 28.5 截图分享（0.5天）

### 功能：3D 命盘 / 大运图 / 五行流 一键生成 PNG 图片

```javascript
function captureScreenshot(renderer, filename) {
    const dataURL = renderer.domElement.toDataURL("image/png");
    // 或使用 html2canvas 捕获整个 DOM
    const link = document.createElement("a");
    link.download = filename;
    link.href = dataURL;
    link.click();
    // 同步上传到服务器（可选）
    fetch('/api/share/upload-screenshot', {
        method: 'POST',
        body: JSON.stringify({ image: dataURL })
    }).then(r => r.json()).then(d => showShareDialog(d.share_url));
}

// 额外支持: 生成方形海报（适合微信朋友圈）
function generatePoster(pillars, wuxing, wuxingScore) {
    const canvas = document.createElement("canvas");
    canvas.width = 800; canvas.height = 1200;  // 4:3 纵向
    const ctx = canvas.getContext("2d");
    // 背景渐变
    const grd = ctx.createLinearGradient(0, 0, 0, canvas.height);
    grd.addColorStop(0, "#1a1a2e");
    grd.addColorStop(1, "#16213e");
    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // 绘制四柱（大字体+五行色）
    pillars.forEach((p, i) => {
        ctx.fillStyle = wuxingColor(p.wuxing);
        ctx.font = "120px serif";
        ctx.textAlign = "center";
        ctx.fillText(p.tiangan, 200 + (i % 2) * 400, 300 + Math.floor(i / 2) * 300);
    });
    // 标题 + 五行得分 + 二维码占位
    // ...
    return canvas.toDataURL("image/png");
}
```

---

## 28.6 文件结构汇总

```
新增:
  web_console/visualizations/3d-chart.html      # 3D 命盘
  web_console/visualizations/luck-timeline.html # 大运动画
  web_console/visualizations/wuxing-flow.html   # 五行实时流
  web_console/visualizations/kg-explorer.html   # 知识图谱 WebGL

修改:
  web_console/index.html                        # 增加"高级可视化"入口
  tengod/api_server.py                          # 新增 /api/visualization/* 端点
                                                  (如 GET /api/visualization/full-report-data)

测试:
  手工测试 + 浏览器兼容测试
```

---

## 28.7 实施顺序

```
第1天:   3D 命盘（Three.js）+ 截图分享
第2天:   大运动画（D3.js）+ 五行动态流（Canvas）
第3天:   知识图谱 WebGL 升级 + 集成首页入口
```

---

## 28.8 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| WebGL 不兼容（移动端/旧浏览器） | 中 | 中 | 提供降级方案（2D Canvas 替代） |
| 3D 渲染帧率 < 30 fps | 中 | 低 | 限制节点数量 + LOD（细节层级）+ 移动端使用较少粒子 |
| 八字数据到 3D 模型映射不清 | 高 | 低 | 提供多层级视图（正视图/俯视图），用户可切换 |
| Canvas 截图跨域/字体加载问题 | 低 | 低 | 使用 base64 字体/颜色，避免外部资源 |
