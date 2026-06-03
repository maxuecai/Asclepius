# Asclepius

这是一个本地桌面版原型，用来做部分表观遗传重编程研发情报：候选因子评分、文献雷达、证据抽取、风险提示，并保留小分子抗衰分析作为辅助工具。它适合研发规划和方法演示，不是临床、监管、投资或用药决策工具。

## 功能

1. 部分表观遗传重编程因子评分器：按年轻化潜力、身份保留、安全性、递送、组织特异性和证据强度排序 OSK/OSKM 等候选方案。
2. 文献雷达：通过 PubMed E-utilities 检索论文，保存到本地 SQLite，并抽取干预、匹配因子、组织、模型、readout、安全风险和证据分。
3. 因子详情页自动关联本地文献证据，显示相关论文数量、平均证据分、风险词和 PMID。
4. 动态评分层：本地文献会调整因子的证据强度、组织适配和风险惩罚，并标记评分来自基础表还是文献动态调整。
5. 评分过程解释：展开总分公式、主要加分项、限制项、文献如何影响评分、安全闸门和下一步验证 readout。
6. 证据归因表：按论文说明它贡献了模型证据、readout、组织适配，还是带来了安全扣分。
7. 实验设计草案：为每个因子生成目标、模型、对照组、时间点、有效性 readout、安全 readout 和 Go/No-Go 门槛。
8. 组合策略设计器：把低风险支持轴、OSK 短暂表达核心和 OSKM/MYC 高风险基准分开，输出组合理由、排除因子和验证路径。
9. 组织优先路线图：按皮肤/成纤维、视网膜、肌肉、免疫、神经等组织生成模型、递送重点、readout 和下一步动作。
10. 安全闸门矩阵：把因子和组合分成绿灯/黄灯/红灯，列出必须通过的 readout、停止触发条件和复核节奏。
11. 证据缺口与 AI 任务：自动生成 PubMed 检索式和下一轮文献结构化任务，服务“搜索-抽取-重评分”的闭环。
12. 数据库资产页：跟踪 `100 篇论文 + 100 个候选基因 + 50 个公司/课题组` 的完成度，并展示候选基因库和机构地图。
13. 任意基因评分器：输入基因 Symbol 或别名，输出年轻化潜力、风险分、安全分、组织适配、机制解释、警告和下一步文献检索式；本地论文命中会动态调整证据强度、组织适配和安全惩罚。
14. 决策台：把基因分为核心候选、安全辅助轴、补证据候选、风险基准和观察池，并给出下一步动作。
15. 权重压力测试：在平衡、安全优先、年轻化优先、证据优先四种权重下测试基因评分是否稳定，避免“换个权重结论就变”。
16. 基因证据包：为每个命中文献的基因输出 PMID、贡献、readout、组织、模型、安全风险和证据缺口。
17. 研发闭环：自动生成 90 天里程碑、实验/证据 Backlog、合作方短名单和 Data Room 清单，把评分结果变成可执行项目。
18. 尽调审计层：输出可信度分、红旗、PMID/DOI/URL/schema 覆盖、文献支撑 Top 基因和投资人问答。
19. 投资人尽调摘要：自动生成 `outputs/investor_diligence.md`，明确披露证据边界、风险和下一步验证计划。
20. 顶部指标卡围绕重编程因子、证据覆盖、风险提示和本地文献库规模。
21. 保留 SMILES 小分子辅助分析：分子性质、ADMET、PAINS/Brenk、靶点预测、结构对接估算和分子评分。
22. 使用 SQLite 保存分子库、文献库、外部 ID 和分析 JSON。
23. 提供 PubChem、ChEMBL、BindingDB、RCSB PDB、PubMed 的 stdlib 客户端/URL builder，联网调用显式 opt-in。
24. 保留旧版候选药虚拟试验，用于历史抗衰药物候选排序和报告生成。
25. 桌面 GUI 改为五个一级模块：`核心重编程`、`数据与评分`、`决策执行`、`分子辅助`、`工具与旧版`；具体页面作为二级标签放入对应模块。

## 数据文件

- `data/aging_hallmarks.csv`：12 项衰老标志及权重。
- `data/candidate_drugs.csv`：候选干预、靶向标志、评分输入和证据锚点。
- `data/aging_targets.csv`：抗衰相关靶点、通路、衰老标志和 PDB ID。
- `data/known_ligands.csv`：已知配体 SMILES，用于相似性靶点预测。
- `data/sample_molecules.csv`：可直接测试的示例分子。
- `data/evidence_sources.csv`：资料来源、证据类型、质量分和 URL。
- `data/trial_endpoints.csv`：推荐临床/功能/安全性/探索性终点。
- `data/software_tools.csv`：外部软件/数据库路线图。
- `data/reprogramming_factors.csv`：部分表观遗传重编程候选因子/组合、风险和证据输入。
- `data/candidate_genes.csv`：100 个候选基因，包含年轻化潜力、身份保留、安全风险、递送、证据和可药物化评分。
- `data/research_organizations.csv`：50 个公司、科研院所、高校和平台机构，用于合作/竞品/课题组地图。
- `data/asclepius_library.sqlite`：桌面 GUI 自动创建的本地分子库数据库。
- `data/asclepius_research.sqlite`：文献雷达自动创建的本地论文和抽取信号数据库；当前已导入超过 100 篇部分重编程/表观遗传重编程相关 PubMed 文献。

## 分子结构后端

Asclepius 会自动检测 RDKit：

- 如果安装了 RDKit：使用 RDKit 解析 SMILES、计算分子描述符、QED 和 Morgan fingerprint。
- 如果没有 RDKit：使用内置轻量 SMILES 规则和字符指纹，保证桌面版仍可运行。

结构对接同理：

- 如果检测到 `vina` 或 `smina`：界面会标记为可接入真实 docking 后端。
- 如果未检测到：使用结构性质 + 靶点概率的可解释估算，并在界面中明确标注。

## 界面信息

桌面界面现在按层级组织为五个一级模块：

- `核心重编程`：包含 `因子评分`、`组合设计`、`组织路线`。这是主工作流，围绕 OSK/OSKM、低风险调控轴、组织优先级、安全闸门和验证路径。
- `数据与评分`：包含 `数据库资产`、`基因评分`、`文献雷达`。这里负责论文库、候选基因库、机构地图、任意基因评分和 PubMed 证据抽取。
- `决策执行`：包含 `决策台`、`研发闭环`、`尽调审计`。这里把候选、证据包、权重压力测试、90 天里程碑、合作方短名单和投资人问答串成执行层。
- `分子辅助`：包含 `分子库与 ADMET`、`靶点预测`、`结构对接`。小分子能力保留为部分重编程研究的辅助工具，不再和核心重编程页面平级。
- `工具与旧版`：包含 `旧版候选排序`、`软件与外部库`。这里保留历史抗衰候选药虚拟试验和外部数据库/软件路线图。

## 外部数据客户端

`src/gerodrug_sim/external.py` 提供：

- PubChem name -> CID/SMILES/InChIKey URL 和解析器。
- ChEMBL SMILES similarity URL 和结果解析器。
- BindingDB ligand URL builder。
- RCSB PDB entry URL builder。
- PubMed 文献雷达在 `src/gerodrug_sim/literature.py` 中提供 ESearch/EFetch URL builder、XML 解析、本地 SQLite 存储和规则抽取。

测试默认不联网；实际联网调用需要显式调用 fetch 函数并设置 timeout。

## 启动桌面界面

在 Finder 中双击：

```text
启动Asclepius桌面GUI.command
```

也可以在终端运行：

```bash
PYTHONPATH=src python3 -m gerodrug_sim.desktop
```

## 命令行运行

```bash
PYTHONPATH=src python3 -m gerodrug_sim.cli \
  --condition "衰弱预防" \
  --participants 240 \
  --months 24 \
  --output outputs/simulation_report.md
```

## 测试

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 说明

- 评分是模拟结果，不代表真实临床证据。
- 当前样例数据用于演示流程，可以继续扩展候选药和衰老标志。
- 虚拟试验结果只用于研发优先级判断，不能用于医疗建议。
- 表观遗传时钟等生物标志物只作为探索性指标，不单独替代临床获益终点。
- 重编程因子评分是研发情报层面的风险/优先级排序，不代表体内疗效、安全性或临床可用性。

## 当前资料依据

- Cell 2023：`Hallmarks of aging: An expanding universe`
- NIA/JAX Interventions Testing Program：多站点异质小鼠干预测试框架
- AFAR TAME：二甲双胍靶向衰老的多中心复合终点试验设计
- FDA surrogate endpoint resources：替代终点需要能预测真实临床获益
- GeroScience endpoint literature：功能结局、复合疾病终点和生物标志物组合
- RDKit：分子描述符、QED、Morgan fingerprint 和分子绘图
- AutoDock Vina / GNINA：结构对接和深度学习重评分
- SwissTargetPrediction / SEA：配体相似性靶点预测思路
- ADMETlab 3.0 / DeepChem：ADMET 和分子机器学习路线
- PubChem / ChEMBL / RCSB PDB / BindingDB：结构、活性、靶点和蛋白结构数据源
- PubMed E-utilities：文献雷达检索和摘要元数据导入
- Cell 2016 / Nature 2020 / Ageing Research Reviews 2025：体内部分重编程和靶向部分重编程治疗策略
