(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  // --- Cognitive Layer Heatmap ---
  var layers = ['L1 信息编码', 'L2 语义流', 'L3 拓扑结构', 'L4 意识涌现', 'L5 注意力调度', 'L6 元认知', 'L7 认知固化', 'L8 境界跃迁'];
  var repos = [
    'DeepSeek-V3', 'DeepSeek-R1', 'DeepSeek-V2', 'DeepSeek-LLM',
    'DeepSeek-MoE', 'V3.2-Exp', 'DeepEP', 'DeepGEMM',
    'FlashMLA', 'TileKernels', '3FS', 'DualPipe',
    'EPLB', 'LPLB', 'Engram', 'profile-data',
    'DeepSeek-OCR', 'DeepSeek-OCR-2', 'DeepSeek-VL', 'DeepSeek-VL2',
    'Janus', 'DeepSeek-Coder', 'Coder-V2', 'DeepSeek-Math',
    'Math-V2', 'Prover-V1.5', 'Prover-V2', 'DreamCraft3D',
    'ESFT', 'smallpond', 'awesome-integration', 'awesome-agent',
    'awesome-coder', 'open-infra-index', 'DeepSpec'
  ];

  // Weight matrix: [layer_idx, repo_idx, weight] where weight is 0-10
  var data = [
    // L1 信息编码
    [0,0,10],[0,1,8],[0,2,7],[0,3,9],[0,27,3],[0,29,5],[0,30,4],[0,32,3],[0,33,3],
    // L2 语义流
    [1,1,10],[1,16,8],[1,17,8],[1,18,6],[1,19,7],[1,20,7],[1,21,5],[1,22,5],[1,23,6],[1,24,6],[1,25,5],[1,26,5],[1,27,5],[1,31,3],
    // L3 拓扑结构
    [2,2,6],[2,6,9],[2,7,10],[2,8,9],[2,9,8],[2,10,8],[2,24,7],[2,26,7],
    // L4 意识涌现
    [3,3,4],[3,4,10],[3,5,9],[3,14,7],
    // L5 注意力调度
    [4,2,5],[4,3,4],[4,8,10],[4,12,8],[4,13,7],[4,28,5],[4,34,10],
    // L6 元认知
    [5,14,10],[5,15,7],[5,31,5],
    // L7 认知固化
    [6,10,10],[6,11,8],[6,22,7],[6,27,6],[6,32,3],[6,34,8],
    // L8 境界跃迁
    [7,5,10],[7,14,9],[7,24,6],[7,28,3],[7,31,3],[7,33,4]
  ];

  // Fill missing cells with null
  var fullData = data.slice();
  repos.forEach(function(_, ri) {
    layers.forEach(function(_, li) {
      if (!data.some(function(d) { return d[0] === li && d[1] === ri; })) {
        fullData.push([li, ri, '-']);
      }
    });
  });

  var chart = echarts.init(document.getElementById('chart-cognitive-heatmap'), null, { renderer: 'svg' });
  chart.setOption({
    animation: false,
    tooltip: {
      appendToBody: true,
      formatter: function(p) {
        if (p.value[2] === '-') return repos[p.value[1]] + ' × ' + layers[p.value[0]] + '<br/>权重: N/A';
        return repos[p.value[1]] + ' × ' + layers[p.value[0]] + '<br/>权重: <b>' + p.value[2] + '</b>';
      }
    },
    grid: {
      left: 140,
      right: 60,
      top: 30,
      bottom: 10
    },
    xAxis: {
      type: 'category',
      data: layers,
      position: 'top',
      axisLabel: { color: muted, fontSize: 11, rotate: 25 },
      axisLine: { lineStyle: { color: rule } },
      splitArea: { show: false }
    },
    yAxis: {
      type: 'category',
      data: repos,
      axisLabel: { color: ink, fontSize: 11 },
      axisLine: { lineStyle: { color: rule } },
      splitArea: { show: false }
    },
    visualMap: {
      min: 0,
      max: 10,
      calculable: true,
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { color: muted },
      inRange: { color: [bg2, accent2, accent] },
      outOfRange: { color: 'transparent' }
    },
    series: [{
      type: 'heatmap',
      data: fullData,
      label: {
        show: true,
        formatter: function(p) { return p.value[2] === '-' ? '' : p.value[2]; },
        color: ink,
        fontSize: 10
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: accent }
      }
    }]
  });
  window.addEventListener('resize', function() { chart.resize(); });
})();