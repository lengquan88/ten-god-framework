/** obsidian_plugin/main.js — 十神 Obsidian 插件 v2.3.0

在 Obsidian 中内嵌十神面板：
- 知识图谱查询侧边栏
- Oracle 咨询面板
- 笔记关联知识节点
- 一键导入知识到笔记
*/
const { Plugin, ItemView, WorkspaceLeaf, Notice, requestUrl } = require("obsidian");

const VIEW_TYPE_TENGOD = "tengod-panel-view";
const DEFAULT_API_URL = "http://localhost:8000";

class TengodPanelView extends ItemView {
    constructor(leaf, plugin) {
        super(leaf);
        this.plugin = plugin;
    }

    getViewType() {
        return VIEW_TYPE_TENGOD;
    }

    getDisplayText() {
        return "十神面板";
    }

    getIcon() {
        return "tengod-icon";
    }

    async onOpen() {
        const container = this.containerEl.children[1];
        container.empty();
        container.addClass("tengod-panel");

        // 标题
        const header = container.createEl("div", { cls: "tengod-header" });
        header.createEl("h3", { text: "十神架构" });
        header.createEl("span", { text: "v2.3.0", cls: "tengod-version" });

        // Oracle 区域
        const oracleSection = container.createEl("div", { cls: "tengod-section" });
        oracleSection.createEl("h4", { text: "Oracle 咨询" });
        const oracleInput = oracleSection.createEl("textarea", {
            placeholder: "输入问题，获取十神智慧...",
            cls: "tengod-input",
        });
        const oracleBtn = oracleSection.createEl("button", {
            text: "咨询",
            cls: "tengod-btn",
        });
        const oracleResult = oracleSection.createEl("div", { cls: "tengod-result" });

        oracleBtn.addEventListener("click", async () => {
            const question = oracleInput.value;
            if (!question) return;
            oracleBtn.disabled = true;
            oracleBtn.setText("咨询中...");
            try {
                const resp = await requestUrl({
                    url: `${this.plugin.settings.apiUrl}/api/oracle`,
                    method: "POST",
                    body: JSON.stringify({ question, mode: "auto" }),
                    headers: { "Content-Type": "application/json" },
                });
                const data = resp.json;
                if (data.code === 0) {
                    oracleResult.empty();
                    oracleResult.createEl("p", {
                        text: data.data.interpretation || "无解读",
                        cls: "tengod-oracle-text",
                    });
                    if (data.data.advice) {
                        oracleResult.createEl("p", {
                            text: "建议: " + data.data.advice,
                            cls: "tengod-advice",
                        });
                    }
                }
            } catch (e) {
                oracleResult.setText("连接失败: " + e.message);
            }
            oracleBtn.disabled = false;
            oracleBtn.setText("咨询");
        });

        // 知识搜索
        const searchSection = container.createEl("div", { cls: "tengod-section" });
        searchSection.createEl("h4", { text: "知识搜索" });
        const searchInput = searchSection.createEl("input", {
            placeholder: "搜索知识节点...",
            cls: "tengod-input",
        });
        const searchBtn = searchSection.createEl("button", {
            text: "搜索",
            cls: "tengod-btn",
        });
        const searchResult = searchSection.createEl("div", { cls: "tengod-result" });

        searchBtn.addEventListener("click", async () => {
            const query = searchInput.value;
            if (!query) return;
            try {
                const resp = await requestUrl({
                    url: `${this.plugin.settings.apiUrl}/api/knowledge/search`,
                    method: "POST",
                    body: JSON.stringify({ query, top_k: 5 }),
                    headers: { "Content-Type": "application/json" },
                });
                const data = resp.json;
                searchResult.empty();
                if (data.code === 0 && data.data.results) {
                    const list = searchResult.createEl("ul", { cls: "tengod-list" });
                    data.data.results.forEach((r) => {
                        const item = list.createEl("li");
                        item.createEl("strong", { text: r.name });
                        item.createEl("span", { text: ` [${r.node_type}] 相似度: ${r.score.toFixed(3)}` });
                        item.addEventListener("click", () => {
                            this.insertIntoNote(r.name, r.node_type);
                        });
                    });
                }
            } catch (e) {
                searchResult.setText("搜索失败: " + e.message);
            }
        });

        // 状态
        const statusSection = container.createEl("div", { cls: "tengod-section" });
        const statusEl = statusSection.createEl("p", { text: "连接中...", cls: "tengod-status" });
        this.updateStatus(statusEl);
    }

    async updateStatus(el) {
        try {
            const resp = await requestUrl({
                url: `${this.plugin.settings.apiUrl}/api/status`,
            });
            const data = resp.json;
            el.setText(`已连接 | 模块: ${Object.keys(data.data?.modules || {}).length}`);
        } catch (e) {
            el.setText("未连接");
        }
    }

    insertIntoNote(name, nodeType) {
        const editor = this.app.workspace.activeEditor?.editor;
        if (editor) {
            editor.replaceSelection(`[[${name}]] (${nodeType})`);
            new Notice(`已插入: ${name}`);
        }
    }

    async onClose() {
        // 清理
    }
}

class TengodSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();
        containerEl.createEl("h2", { text: "十神面板设置" });

        new Setting(containerEl)
            .setName("API 地址")
            .setDesc("十神服务地址")
            .addText((text) =>
                text
                    .setPlaceholder("http://localhost:8000")
                    .setValue(this.plugin.settings.apiUrl)
                    .onChange(async (value) => {
                        this.plugin.settings.apiUrl = value;
                        await this.plugin.saveSettings();
                    })
            );
    }
}

module.exports = class TengodPlugin extends Plugin {
    settings = { apiUrl: DEFAULT_API_URL };

    async onload() {
        await this.loadSettings();
        this.addSettingTab(new TengodSettingTab(this.app, this));

        this.registerView(
            VIEW_TYPE_TENGOD,
            (leaf) => new TengodPanelView(leaf, this)
        );

        this.addRibbonIcon("tengod-icon", "十神面板", () => {
            this.activateView();
        });

        this.addCommand({
            id: "open-tengod-panel",
            name: "打开十神面板",
            callback: () => this.activateView(),
        });
    }

    async activateView() {
        const { workspace } = this.app;
        let leaf = workspace.getLeavesOfType(VIEW_TYPE_TENGOD)[0];
        if (!leaf) {
            leaf = workspace.getRightLeaf(false);
            await leaf.setViewState({ type: VIEW_TYPE_TENGOD, active: true });
        }
        workspace.revealLeaf(leaf);
    }

    async loadSettings() {
        this.settings = Object.assign({}, this.settings, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
    }

    onunload() {
        // 卸载
    }
};