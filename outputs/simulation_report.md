# Asclepius 模拟报告：衰弱预防

生成日期: 2026-06-01

## 执行摘要

本次模拟共评估 5 个候选药，当前领先候选药为 二甲双胍，并汇总了 5 个虚拟试验场景。

## 候选药排名

| 排名 | 候选药 | 机制 | 评分 | 安全性 | 证据 | 建议 |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 1 | 二甲双胍 | 营养感知失调、慢性炎症、线粒体功能障碍 | 0.643 | 0.86 | 转化证据 0.72 | 进入验证实验 |
| 2 | 雷帕霉素 | 营养感知失调、蛋白稳态丧失、巨自噬受损、慢性炎症 | 0.596 | 0.55 | 转化证据 0.84 | 进入验证实验 |
| 3 | 阿卡波糖 | 营养感知失调、慢性炎症、肠道菌群失调 | 0.561 | 0.76 | 转化证据 0.70 | 进入验证实验 |
| 4 | 尿石素 A | 线粒体功能障碍、巨自噬受损、蛋白稳态丧失 | 0.559 | 0.78 | 转化证据 0.56 | 进入验证实验 |
| 5 | 卡格列净 | 营养感知失调、线粒体功能障碍、慢性炎症 | 0.512 | 0.62 | 转化证据 0.64 | 暂缓机制复核 |

## 虚拟试验摘要

| 试验 | 阶段 | 人群 | 周期 | 主要终点 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 二甲双胍 | 虚拟 IIa | 衰弱预防 | 24 months | 衰弱指数 + 生物年龄偏移 | 响应率提升 +21.1%；衰弱变化 -0.038；生物年龄变化 -0.246 |
| 雷帕霉素 | 虚拟 IIa | 衰弱预防 | 24 months | 衰弱指数 + 生物年龄偏移 | 响应率提升 +12.2%；衰弱变化 -0.033；生物年龄变化 -0.208 |
| 阿卡波糖 | 虚拟 IIa | 衰弱预防 | 24 months | 衰弱指数 + 生物年龄偏移 | 响应率提升 +8.9%；衰弱变化 -0.030；生物年龄变化 -0.192 |
| 尿石素 A | 虚拟 IIa | 衰弱预防 | 24 months | 衰弱指数 + 生物年龄偏移 | 响应率提升 +8.3%；衰弱变化 -0.031；生物年龄变化 -0.179 |
| 卡格列净 | 虚拟 IIa | 衰弱预防 | 24 months | 衰弱指数 + 生物年龄偏移 | 响应率提升 +6.1%；衰弱变化 -0.029；生物年龄变化 -0.164 |

## 解释边界

- 评分是模拟输出，不等同于临床证据。
- 候选药排名仅用于研发优先级判断，仍需要进一步实验验证。
- 虚拟试验摘要仅描述原型场景，不能用于医疗决策。

## 研发设计补充

### 推荐终点
- 年龄相关多病共存复合终点（临床结局，重要性 0.95）：参考 TAME 思路，关注心血管事件、癌症、认知障碍、糖尿病和死亡等复合事件
- 不良事件和停药率（安全性结局，重要性 0.92）：抗衰干预通常面向相对健康人群，安全性阈值应更严格
- 衰弱指数（功能结局，重要性 0.88）：结合症状、体能和缺陷累积，适合 geroscience 预防性试验
- 步速（功能结局，重要性 0.80）：简单、可重复，与老年健康状态和功能风险相关
- 生活质量（患者报告结局，重要性 0.72）：补充临床获益和功能结局，帮助区分健康老化与非健康老化

### 候选药证据锚点
- 二甲双胍：Hallmarks of aging: An expanding universe；Targeting Aging with Metformin Trial；Endpoints for geroscience clinical trials
- 雷帕霉素：Hallmarks of aging: An expanding universe；NIA Interventions Testing Program；NIA ITP genetically heterogeneous mouse model
- 阿卡波糖：NIA Interventions Testing Program；Acarbose improves health and lifespan in aging HET3 mice
- 尿石素 A：Hallmarks of aging: An expanding universe；Biomarkers of aging and evaluation techniques
- 卡格列净：NIA Interventions Testing Program

### 数据库资产完成度
- 论文：105/100，缺口 0。
- 候选基因：100/100，缺口 0。
- 公司/课题组：50/50，缺口 0。

### 可信度审计
- 可信度分：0.75；等级：B+ 可演示，需补专家复核。
- 论文审计：唯一 PMID 105，DOI 105，高信号论文 32。
- 基因审计：检索式覆盖 100，PMID 命中基因 20，高风险已标记 10。
  - 红旗：多数候选基因还没有 PMID 级本地文献命中
  - 红旗：尚未完成外部专家复核，因此可信度分设置上限
  - 红旗：候选基因分数仍是启发式研发优先级，不是实验结论

### 候选基因评分 Top 10
- SIRT6：总分 0.69，年轻化 0.66，风险 0.20，文献 0 篇，溯源 0.46，建议：优先进入 AI 文献复核和体外验证设计。
- PRKAA1：总分 0.66，年轻化 0.55，风险 0.17，文献 1 篇，溯源 0.64，建议：观察名单，需要安全闸门和证据补强。
- FOXO3：总分 0.66，年轻化 0.55，风险 0.15，文献 1 篇，溯源 0.58，建议：观察名单，需要安全闸门和证据补强。
- SIRT1：总分 0.66，年轻化 0.60，风险 0.25，文献 2 篇，溯源 0.59，建议：观察名单，需要安全闸门和证据补强。
- SIRT3：总分 0.64，年轻化 0.57，风险 0.17，文献 1 篇，溯源 0.52，建议：观察名单，需要安全闸门和证据补强。
- MTOR：总分 0.64，年轻化 0.55，风险 0.28，文献 1 篇，溯源 0.55，建议：观察名单，需要安全闸门和证据补强。
- PPARGC1A：总分 0.63，年轻化 0.60，风险 0.20，文献 0 篇，溯源 0.47，建议：观察名单，需要安全闸门和证据补强。
- KLF4：总分 0.63，年轻化 0.72，风险 0.49，文献 15 篇，溯源 0.90，建议：观察名单，需要安全闸门和证据补强。
- NAMPT：总分 0.62，年轻化 0.52，风险 0.21，文献 0 篇，溯源 0.46，建议：观察名单，需要安全闸门和证据补强。
- TFEB：总分 0.61，年轻化 0.58，风险 0.21，文献 0 篇，溯源 0.45，建议：观察名单，需要安全闸门和证据补强。

### 投资人尽调问答
- Q：这是不是拍脑袋评分？
  - A：不是单纯拍脑袋：每个基因有固定组件分、风险分和检索式；当前 20 个基因已有本地文献命中调整。
  - 证据：Top provenance genes: POU5F1、KLF4、SOX2、MYC、CDKN2A
- Q：数据库有没有过线？
  - A：论文 105 篇，候选基因 100 个，公司/课题组 50 个；可信度等级 B+ 可演示，需补专家复核。
  - 证据：PMID/URL/schema checks are represented in the audit payload.
- Q：最大风险是什么？
  - A：最大风险不是 AI 不够强，而是生物学验证窗口窄：癌变、去分化、递送和组织特异性必须逐层验证。
  - 证据：Red flags: 多数候选基因还没有 PMID 级本地文献命中；尚未完成外部专家复核，因此可信度分设置上限；候选基因分数仍是启发式研发优先级，不是实验结论
- Q：下一步花钱买什么确定性？
  - A：先买证据确定性和合作确定性：Top 20 基因证据包、Top 10 机构人工复核、1-2 个可外包体外 readout 设计。
  - 证据：Next steps: 为 Top 20 基因补 PMID 级证据包：模型、组织、readout、安全风险、复现实验边界。；对公司/课题组做人工复核：负责人、代表论文、融资/合作状态、是否真的做部分重编程。

### 评分方法卡
- 方法版本：gene-score-v2-literature-stress
- 公式：total = weighted mean(rejuvenation, identity, safety, delivery, tissue, evidence, druggability, reprogramming relevance)
- 文献调整：Local PubMed matches adjust evidence strength, tissue specificity, functional readout bonus, oncogenic risk, dedifferentiation risk, and provenance score.

### 基因研发组合分层
- PINK1｜安全辅助轴：评分 0.55，安全 0.83，溯源 0.40，动作：可作为 OSK/低风险组合的支持因子。
- PRKN｜安全辅助轴：评分 0.55，安全 0.83，溯源 0.40，动作：可作为 OSK/低风险组合的支持因子。
- TFAM｜安全辅助轴：评分 0.55，安全 0.81，溯源 0.39，动作：可作为 OSK/低风险组合的支持因子。
- ATG5｜安全辅助轴：评分 0.55，安全 0.83，溯源 0.42，动作：可作为 OSK/低风险组合的支持因子。
- ATG7｜安全辅助轴：评分 0.55，安全 0.83，溯源 0.42，动作：可作为 OSK/低风险组合的支持因子。
- NRF1｜安全辅助轴：评分 0.54，安全 0.81，溯源 0.38，动作：可作为 OSK/低风险组合的支持因子。
- BECN1｜安全辅助轴：评分 0.54，安全 0.81，溯源 0.41，动作：可作为 OSK/低风险组合的支持因子。
- MFN2｜安全辅助轴：评分 0.53，安全 0.83，溯源 0.38，动作：可作为 OSK/低风险组合的支持因子。
- ERCC1｜安全辅助轴：评分 0.53，安全 0.80，溯源 0.42，动作：可作为 OSK/低风险组合的支持因子。
- SIRT7｜安全辅助轴：评分 0.53，安全 0.75，溯源 0.35，动作：可作为 OSK/低风险组合的支持因子。
- SIRT6｜补证据候选：评分 0.69，安全 0.80，溯源 0.46，动作：先补 PMID 级证据和组织 readout。
- PRKAA1｜补证据候选：评分 0.66，安全 0.83，溯源 0.64，动作：先补 PMID 级证据和组织 readout。
- FOXO3｜补证据候选：评分 0.66，安全 0.85，溯源 0.58，动作：先补 PMID 级证据和组织 readout。
- SIRT1｜补证据候选：评分 0.66，安全 0.75，溯源 0.59，动作：先补 PMID 级证据和组织 readout。
- SIRT3｜补证据候选：评分 0.64，安全 0.83，溯源 0.52，动作：先补 PMID 级证据和组织 readout。

### 权重压力测试
- TET2：均值 0.56，跨度 0.03，稳定性：稳定，结论：保留观察。
- TET1：均值 0.56，跨度 0.02，稳定性：稳定，结论：保留观察。
- GLIS1：均值 0.51，跨度 0.03，稳定性：稳定，结论：保留观察。
- TET3：均值 0.51，跨度 0.04，稳定性：稳定，结论：保留观察。
- TERC：均值 0.51，跨度 0.01，稳定性：稳定，结论：保留观察。
- HDAC1：均值 0.50，跨度 0.04，稳定性：稳定，结论：保留观察。
- LIN28A：均值 0.50，跨度 0.04，稳定性：稳定，结论：保留观察。
- HDAC2：均值 0.50，跨度 0.04，稳定性：稳定，结论：保留观察。
- DNMT1：均值 0.50，跨度 0.04，稳定性：稳定，结论：保留观察。
- HDAC3：均值 0.50，跨度 0.04，稳定性：稳定，结论：保留观察。

### 基因证据包摘要
- SOX2：论文 16，平均证据 0.66；SOX2 命中 16 篇本地论文，平均证据分 0.66；风险信号：dedifferentiation、immune response、oncogenic risk
- KLF4：论文 15，平均证据 0.67；KLF4 命中 15 篇本地论文，平均证据分 0.67；风险信号：dedifferentiation、immune response、oncogenic risk
- POU5F1：论文 14，平均证据 0.68；POU5F1 命中 14 篇本地论文，平均证据分 0.68；风险信号：dedifferentiation、immune response、oncogenic risk
- MYC：论文 14，平均证据 0.60；MYC 命中 14 篇本地论文，平均证据分 0.60；风险信号：dedifferentiation、immune response、oncogenic risk
- CDKN2A：论文 5，平均证据 0.64；CDKN2A 命中 5 篇本地论文，平均证据分 0.64；风险信号：immune response、oncogenic risk
- CDKN1A：论文 5，平均证据 0.52；CDKN1A 命中 5 篇本地论文，平均证据分 0.52；风险信号：dedifferentiation、immune response、oncogenic risk
- DNMT3A：论文 2，平均证据 0.82；DNMT3A 命中 2 篇本地论文，平均证据分 0.82；风险信号：dedifferentiation、oncogenic risk
- NANOG：论文 2，平均证据 0.61；NANOG 命中 2 篇本地论文，平均证据分 0.61；风险信号：dedifferentiation、immune response

### 90 天研发里程碑
- 0-30 天：把候选判断从分数升级为可复核证据包。交付物：完成 Top 20 基因证据包人工复核，优先 PINK1、PRKN、TFAM、ATG5。
  - 退出门槛：可信度等级不低于 B+ 可演示，需补专家复核，所有核心/辅助候选都有明确补证据动作
- 31-60 天：锁定第一条组织年轻化路线。交付物：围绕 皮肤/成纤维细胞 输出模型、递送、主要 readout 和安全 readout 的实验 brief。
  - 退出门槛：安全闸门覆盖 红灯、红灯、红灯，高风险基因只留作反例/基准
- 61-90 天：形成可给合作方/CRO 报价的验证包。交付物：1 个局部组织 pilot、1 个阴性/风险基准、1 套表观年龄+功能+安全 readout 清单。
  - 退出门槛：能够拿到至少 2 个外部实验报价或高校合作反馈
- 3-6 个月：把 AI 文献闭环升级为专有数据闭环。交付物：接入外部实验结果、失败样本和专家复核意见，形成评分 diff 与模型卡。
  - 退出门槛：投资人能看到数据产生过程，而不是只看到静态名单

### 实验/证据 Backlog
- GENE-ATG5｜P0｜证据补强｜ATG5：ATG5 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-ATG7｜P0｜证据补强｜ATG7：ATG7 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-BECN1｜P0｜证据补强｜BECN1：BECN1 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-ERCC1｜P0｜证据补强｜ERCC1：ERCC1 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-MFN2｜P0｜证据补强｜MFN2：MFN2 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-NRF1｜P0｜证据补强｜NRF1：NRF1 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-PINK1｜P0｜证据补强｜PINK1：PINK1 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-PRKAA1｜P0｜证据补强｜PRKAA1：PRKAA1 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-PRKN｜P0｜证据补强｜PRKN：PRKN PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-SIRT6｜P0｜证据补强｜SIRT6：SIRT6 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-SIRT7｜P0｜证据补强｜SIRT7：SIRT7 PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界
- GENE-TFAM｜P0｜证据补强｜TFAM：TFAM PMID 证据包补齐到至少 3 篇高相关论文。
  - 成功标准：至少包含组织、模型、readout、安全风险和失败边界

### 合作方短名单
- NewLimit（company，USA）：匹配 0.67；部分重编程相关；AI/单细胞/计算能力。
  - 切入：以数据互补/候选复核切入，避免一上来谈全栈合作
- Turn Biotechnologies（company，USA）：匹配 0.65；部分重编程相关；递送或基因表达平台。
  - 切入：以递送可控表达和安全开关评估切入
- YouthBio Therapeutics（company，USA）：匹配 0.65；部分重编程相关；递送或基因表达平台。
  - 切入：以递送可控表达和安全开关评估切入
- Kyoto University CiRA（research_institute，Japan）：匹配 0.53；部分重编程相关。
  - 切入：以 fibroblast 组织模型、readout 设计或小规模验证合作切入
- Altos Labs（company，USA）：匹配 0.53；部分重编程相关。
  - 切入：以竞品/生态情报跟踪为主，先人工确认真实项目边界
- Life Biosciences（company，USA）：匹配 0.53；部分重编程相关。
  - 切入：以竞品/生态情报跟踪为主，先人工确认真实项目边界
- Salk Institute（research_institute，USA）：匹配 0.53；部分重编程相关。
  - 切入：以 fibroblast 组织模型、readout 设计或小规模验证合作切入
- Insilico Medicine（company，Hong Kong）：匹配 0.39；AI/单细胞/计算能力。
  - 切入：以数据互补/候选复核切入，避免一上来谈全栈合作

### Data Room 清单
- 数据库清单｜已具备：论文 105，候选基因 100，机构 50。下一步：导出 schema、字段字典和数据来源说明。
- 评分方法卡｜已具备：gene-score-v2-literature-stress。下一步：冻结版本，并记录每次文献导入后的评分 diff。
- Top 基因证据包｜部分具备：6/20 个证据包已有至少 3 篇本地文献。下一步：人工复核 PMID、模型、readout、安全风险和失败证据。
- 权重敏感性｜已具备：已测试 30 个候选的平衡/安全/年轻化/证据优先场景。下一步：把高敏感候选移出核心叙事或补证据。
- 核心候选边界｜待补强：核心候选 0 个；低证据高分候选被转入补证据候选。下一步：只用可复核证据支撑核心候选，不把启发式高分当结论。
- 专家复核｜缺失：尚未完成外部专家复核，因此可信度分设置上限；候选基因分数仍是启发式研发优先级，不是实验结论。下一步：找 2-3 位表观重编程/单细胞/递送专家做盲审备注。
- 外包实验报价｜缺失：尚未接入 CRO 或高校实验反馈。下一步：用实验 backlog 生成询价包，拿到报价和可行性反馈。

### 部分重编程因子优先级
- SIRT6：优先级 0.69，安全分 0.80，文献 0 篇，评分：基础，建议：优先做聚焦验证。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.69；安全分为 0.80。
  - 过程：主要加分项：安全性 0.80 × 0.24；年轻化潜力 0.66 × 0.22；细胞身份保留 0.82 × 0.16
  - 下一步：优先选择 fibroblast、immune、liver 的体外模型，比较年轻/老年细胞状态。
  - 下一步：最小 readout：RNA-seq/qPCR、DNA甲基化年龄、细胞身份标志、p16/p21、Ki67/EdU。
  - 实验草案：验证 SIRT6 是否能让老化 fibroblast 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：若年轻化 readout 改善且安全 readout 稳定，可进入更复杂组织模型或局部递送验证。
- FOXO3：优先级 0.68，安全分 0.84，文献 1 篇，评分：动态，建议：观察名单，需安全闸门。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.68；安全分为 0.84。
  - 过程：主要加分项：安全性 0.84 × 0.24；细胞身份保留 0.84 × 0.16；年轻化潜力 0.56 × 0.22
  - 下一步：优先选择 immune、metabolic_tissue、stress_response 的体外模型，比较年轻/老年细胞状态。
  - 下一步：最小 readout：RNA-seq/qPCR、DNA甲基化年龄、细胞身份标志、p16/p21、Ki67/EdU。
  - 实验草案：验证 FOXO3 是否能让老化 immune 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：若年轻化 readout 改善且安全 readout 稳定，可进入更复杂组织模型或局部递送验证。
- OCT4 + SOX2 + KLF4：优先级 0.67，安全分 0.45，文献 30 篇，评分：动态，建议：暂缓，先复核机制。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.67；安全分为 0.45。
  - 过程：主要加分项：年轻化潜力 0.98 × 0.22；安全性 0.45 × 0.24；细胞身份保留 0.62 × 0.16
  - 下一步：优先选择 retina、neuron、fibroblast 的体外模型，比较年轻/老年细胞状态。
  - 下一步：最小 readout：RNA-seq/qPCR、DNA甲基化年龄、细胞身份标志、p16/p21、Ki67/EdU。
  - 实验草案：验证 OCT4 + SOX2 + KLF4 是否能让老化 retina 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：进入下一步前必须同时满足年轻化 readout 改善、身份保留、多能性/异常增殖无明显上升。
- KLF4：优先级 0.61，安全分 0.50，文献 16 篇，评分：动态，建议：观察名单，需安全闸门。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.61；安全分为 0.50。
  - 过程：主要加分项：年轻化潜力 0.70 × 0.22；安全性 0.50 × 0.24；细胞身份保留 0.67 × 0.16
  - 下一步：优先选择 epithelial、fibroblast、retina 的体外模型，比较年轻/老年细胞状态。
  - 下一步：最小 readout：RNA-seq/qPCR、DNA甲基化年龄、细胞身份标志、p16/p21、Ki67/EdU。
  - 实验草案：验证 KLF4 是否能让老化 epithelial 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：进入下一步前必须同时满足年轻化 readout 改善、身份保留、多能性/异常增殖无明显上升。
- TET2：优先级 0.57，安全分 0.61，文献 0 篇，评分：基础，建议：暂缓，先复核机制。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.57；安全分为 0.61。
  - 过程：主要加分项：安全性 0.61 × 0.24；年轻化潜力 0.58 × 0.22；细胞身份保留 0.72 × 0.16
  - 下一步：优先选择 hematopoietic、immune、fibroblast 的体外模型，比较年轻/老年细胞状态。
  - 下一步：最小 readout：RNA-seq/qPCR、DNA甲基化年龄、细胞身份标志、p16/p21、Ki67/EdU。
  - 实验草案：验证 TET2 是否能让老化 hematopoietic 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：若年轻化 readout 改善且安全 readout 稳定，可进入更复杂组织模型或局部递送验证。
- SOX2：优先级 0.53，安全分 0.33，文献 16 篇，评分：动态，建议：仅作高风险基准。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.53；安全分为 0.33。
  - 过程：主要加分项：年轻化潜力 0.68 × 0.22；证据强度 0.71 × 0.12；细胞身份保留 0.52 × 0.16
  - 下一步：先做文献复核和风险基准，不建议直接设计体内验证。
  - 下一步：重点整理癌症、畸胎瘤、去分化和异常增殖证据。
  - 实验草案：验证 SOX2 是否能让老化 neuron 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：只有在风险标志不上升且身份标志稳定时，才允许从高风险基准转入候选验证。
- OCT4 + SOX2 + KLF4 + MYC：优先级 0.50，安全分 0.08，文献 14 篇，评分：动态，建议：仅作高风险基准。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.50；安全分为 0.08。
  - 过程：主要加分项：年轻化潜力 1.00 × 0.22；证据强度 0.76 × 0.12；细胞身份保留 0.35 × 0.16
  - 下一步：先做文献复核和风险基准，不建议直接设计体内验证。
  - 下一步：重点整理癌症、畸胎瘤、去分化和异常增殖证据。
  - 实验草案：验证 OCT4 + SOX2 + KLF4 + MYC 是否能让老化 fibroblast 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：只有在风险标志不上升且身份标志稳定时，才允许从高风险基准转入候选验证。
- OCT4：优先级 0.50，安全分 0.22，文献 14 篇，评分：动态，建议：仅作高风险基准。
  - 过程：总优先级 = Σ(组件分 × 权重)，当前为 0.50；安全分为 0.22。
  - 过程：主要加分项：年轻化潜力 0.74 × 0.22；证据强度 0.73 × 0.12；细胞身份保留 0.45 × 0.16
  - 下一步：先做文献复核和风险基准，不建议直接设计体内验证。
  - 下一步：重点整理癌症、畸胎瘤、去分化和异常增殖证据。
  - 实验草案：验证 OCT4 是否能让老化 fibroblast 恢复年轻状态，同时保留细胞身份。
  - Go/No-Go：只有在风险标志不上升且身份标志稳定时，才允许从高风险基准转入候选验证。

### 部分重编程组合策略
- 低风险染色质/稳态支持轴：优先级 0.65，安全下限 0.61，风险档：保守，因子：SIRT6 + TET2。
  - 策略：先用安全性较高的染色质修复、应激稳态或表观调控轴建立低风险年轻化基线。
  - 验证：在年轻/老年 fibroblast 体外模型中先做分步验证：单因子、两两组合、完整组合。
  - 验证：所有组合必须比较年轻化 signature、DNA 甲基化年龄、细胞身份标志和功能 readout。
- OSK 短暂表达 + 安全辅助轴：优先级 0.58，安全下限 0.45，风险档：保守，因子：OCT4 + SOX2 + KLF4 + SIRT6 + TET2。
  - 策略：把 OSK 作为年轻化核心信号，但只允许短时程、局部、可关闭表达，并配套低风险支持轴。
  - 验证：在年轻/老年 fibroblast 体外模型中先做分步验证：单因子、两两组合、完整组合。
  - 验证：所有组合必须比较年轻化 signature、DNA 甲基化年龄、细胞身份标志和功能 readout。
- 高风险重编程基准：优先级 0.38，安全下限 0.08，风险档：仅基准，因子：OCT4 + SOX2 + KLF4 + MYC。
  - 策略：只作为风险上限和阳性基准，帮助模型识别去分化、异常增殖和癌变信号。
  - 验证：在年轻/老年 fibroblast 体外模型中先做分步验证：单因子、两两组合、完整组合。
  - 验证：所有组合必须比较年轻化 signature、DNA 甲基化年龄、细胞身份标志和功能 readout。

### 组织优先研发路线
- 皮肤/成纤维细胞：优先级 0.67，首选因子：SIRT6 + KLF4 + TET2，组合：低风险染色质/稳态支持轴。
  - 模型：年轻/老年人源成纤维细胞；可扩展到皮肤类器官或伤口愈合模型
  - 递送：短暂 mRNA、小分子调控或可关闭表达系统；先避开全身递送
- 神经/脑：优先级 0.74，首选因子：SIRT6，组合：低风险染色质/稳态支持轴。
  - 模型：神经元、胶质细胞或脑类器官；先做体外年龄状态逆转
  - 递送：局部/细胞类型特异递送，必须限制表达窗口
- 免疫/造血：优先级 0.69，首选因子：SIRT6 + FOXO3 + TET2，组合：低风险染色质/稳态支持轴。
  - 模型：外周免疫细胞、造血祖细胞；先做 ex vivo 状态恢复
  - 递送：ex vivo 编辑或可逆表观调控优先；体内递送风险较高
- 视网膜/视神经：优先级 0.66，首选因子：KLF4，组合：低风险染色质/稳态支持轴。
  - 模型：视网膜神经节细胞、视网膜类器官；后续才考虑局部动物模型
  - 递送：局部递送和可控表达优先；AAV 类方案必须绑定表达开关
- 肌肉/再生：优先级 0.54，首选因子：LIN28A，组合：低风险染色质/稳态支持轴。
  - 模型：肌管、肌卫星细胞或肌肉类器官；关注肌少症相关功能 readout
  - 递送：局部 mRNA/LNP 或短时程表达；优先避免长期转录因子表达

### 安全闸门矩阵
- 红灯｜OCT4：安全分 0.22；必须通过：年轻化 signature 改善；细胞身份标志不下降；DNA 损伤不升高。
- 红灯｜OCT4 + SOX2 + KLF4 + MYC：安全分 0.08；必须通过：年轻化 signature 改善；细胞身份标志不下降；DNA 损伤不升高。
- 红灯｜SOX2：安全分 0.33；必须通过：年轻化 signature 改善；细胞身份标志不下降；DNA 损伤不升高。
- 红灯｜高风险重编程基准：安全分 0.08；必须通过：年轻化 signature 改善；细胞身份标志不下降；DNA 损伤不升高。
- 黄灯｜KLF4：安全分 0.50；必须通过：年轻化 signature 改善；细胞身份标志不下降；DNA 损伤不升高。
- 黄灯｜OCT4 + SOX2 + KLF4：安全分 0.45；必须通过：年轻化 signature 改善；细胞身份标志不下降；DNA 损伤不升高。

### 证据缺口与 AI 任务
- LIN28A：紧急度 1.00；缺口：本地文献不足；证据强度不足；递送可控性不足。
  - 检索式：("LIN28A" OR lin28a) partial reprogramming aging (regeneration OR muscle OR metabolic_tissue) safety
  - AI任务：AI 检索并结构化 LIN28A 的部分重编程证据，重点回答：本地文献不足、证据强度不足、递送可控性不足；输出模型、组织、readout、安全风险和可复现实验边界。
- SIRT6：紧急度 0.79；缺口：本地文献不足；证据强度不足。
  - 检索式：("SIRT6" OR sirt6) partial reprogramming aging (fibroblast OR immune OR liver) safety
  - AI任务：AI 检索并结构化 SIRT6 的部分重编程证据，重点回答：本地文献不足、证据强度不足；输出模型、组织、readout、安全风险和可复现实验边界。
- OCT4 + SOX2 + KLF4 + MYC：紧急度 0.76；缺口：递送可控性不足；安全窗口不足；身份保留不足。
  - 检索式：("OCT4 + SOX2 + KLF4 + MYC" OR oskm) partial reprogramming aging (fibroblast OR iPSC_model) safety
  - AI任务：AI 检索并结构化 OCT4 + SOX2 + KLF4 + MYC 的部分重编程证据，重点回答：递送可控性不足、安全窗口不足、身份保留不足；输出模型、组织、readout、安全风险和可复现实验边界。
- TET2：紧急度 0.73；缺口：本地文献不足；证据强度不足；递送可控性不足。
  - 检索式：("TET2" OR tet2) partial reprogramming aging (hematopoietic OR immune OR fibroblast) safety
  - AI任务：AI 检索并结构化 TET2 的部分重编程证据，重点回答：本地文献不足、证据强度不足、递送可控性不足；输出模型、组织、readout、安全风险和可复现实验边界。
- KLF4：紧急度 0.70；缺口：安全窗口不足。
  - 检索式：("KLF4" OR klf4) partial reprogramming aging (epithelial OR fibroblast OR retina) safety
  - AI任务：AI 检索并结构化 KLF4 的部分重编程证据，重点回答：安全窗口不足；输出模型、组织、readout、安全风险和可复现实验边界。
- OCT4 + SOX2 + KLF4：紧急度 0.70；缺口：安全窗口不足。
  - 检索式：("OCT4 + SOX2 + KLF4" OR osk) partial reprogramming aging (retina OR neuron OR fibroblast) safety
  - AI任务：AI 检索并结构化 OCT4 + SOX2 + KLF4 的部分重编程证据，重点回答：安全窗口不足；输出模型、组织、readout、安全风险和可复现实验边界。

### 公司/课题组地图样例
- Insilico Medicine（company，Hong Kong）：AI drug discovery for aging and disease。
- Genflow Biosciences（company，UK）：SIRT6 gene therapy and longevity。
- Shift Bioscience（company，UK）：cell simulation and rejuvenation factors。
- AgeX Therapeutics（company，USA）：regenerative medicine and induced tissue regeneration。
- Altos Labs（company，USA）：cellular rejuvenation and reprogramming。
- BioAge Labs（company，USA）：omics driven aging therapeutics。
- Calico（company，USA）：aging biology and age related disease。
- Cambrian Bio（company，USA）：portfolio of longevity therapeutics。
- Fauna Bio（company，USA）：comparative genomics for disease and longevity。
- Gordian Biotechnology（company，USA）：in vivo screening for age related disease。
- Life Biosciences（company，USA）：aging therapeutics and partial epigenetic reprogramming。
- NewLimit（company，USA）：epigenetic reprogramming and cell age models。

### 资料来源
- Hallmarks of aging: An expanding universe，Cell，2023：https://www.cell.com/cell/fulltext/S0092-8674(22)01377-0
- Induction of pluripotent stem cells from mouse embryonic and adult fibroblast cultures by defined factors，Cell，2006：https://doi.org/10.1016/j.cell.2006.07.024
- Induction of pluripotent stem cells from adult human fibroblasts by defined factors，Cell，2007：https://doi.org/10.1016/j.cell.2007.11.019
- Surrogate endpoint resources，FDA，2026：https://www.fda.gov/drugs/development-resources/surrogate-endpoint-resources-drug-and-biologic-development
- Reprogramming to recover youthful epigenetic information and restore vision，Nature，2020：https://doi.org/10.1038/s41586-020-2975-4
- NIA Interventions Testing Program，JAX Aging Center，2026：https://www.jax.org/research-and-faculty/research-centers/aging-center/research/itp
- In vivo amelioration of age-associated hallmarks by partial reprogramming，Cell，2016：https://doi.org/10.1016/j.cell.2016.11.052
- Targeting Aging with Metformin Trial，AFAR，2026：https://www.afar.org/tame-trial
- Reprogramming in vivo produces teratomas and iPS cells with totipotency features，Nature，2013：https://doi.org/10.1038/nature12586
- NIA ITP genetically heterogeneous mouse model，EBioMedicine，2017：https://www.sciencedirect.com/science/article/pii/S2352396416305540
- Endpoints for geroscience clinical trials，GeroScience，2023：https://link.springer.com/article/10.1007/s11357-022-00671-8
- Acarbose improves health and lifespan in aging HET3 mice，Aging Cell，2019：https://pmc.ncbi.nlm.nih.gov/articles/PMC6413665/
- Targeted partial reprogramming as a novel therapeutic strategy for age-related decline，Ageing Research Reviews，2025：https://doi.org/10.1016/j.arr.2025.102731
- Biomarkers of aging and evaluation techniques，Review，2024：https://pmc.ncbi.nlm.nih.gov/articles/PMC11081160/

### 软件与数据库路线图
- RDKit（化学信息学）：SMILES 解析、描述符、Morgan 指纹、QED 和分子绘图；状态：可选自动检测。
- AutoDock Vina（结构对接）：蛋白-小分子 docking 和虚拟筛选；状态：可选自动检测。
- GNINA（深度学习对接）：CNN scoring 与 docking pose reranking；状态：规划接入。
- SwissTargetPrediction（靶点预测）：基于 2D/3D 相似性预测小分子蛋白靶点；状态：方法参考。
- Similarity Ensemble Approach（靶点预测）：基于配体集合相似性推断靶点；状态：方法参考。
- ADMETlab 3.0（ADMET）：综合 ADMET、理化性质和药物化学评估；状态：规划接入。
- DeepChem（分子机器学习）：分子 ML、图模型和药物发现建模；状态：规划接入。
- PubChem PUG-REST（化学数据库）：按名称、CID、SMILES 获取结构和性质；状态：规划接入。
- ChEMBL（活性数据库）：化合物、靶点、活性和相似性搜索；状态：规划接入。
- RCSB PDB（结构数据库）：获取 PDB 结构、配体和实验结构元数据；状态：规划接入。
- BindingDB（结合数据库）：蛋白-小分子结合数据和活性记录；状态：规划接入。
- PubMed E-utilities（文献数据库）：按关键词检索论文并抓取 PMID、摘要、DOI 和期刊元数据；状态：已接入。
