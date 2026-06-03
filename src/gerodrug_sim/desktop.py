"""Native desktop GUI for the geroscience simulation prototype."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Iterable, Mapping

from gerodrug_sim.external import summarize_external_status
from gerodrug_sim.knowledge_assets import (
    audit_asset_quality,
    asset_summary,
    build_data_room_checklist,
    build_experiment_backlog,
    build_gene_evidence_packs,
    build_gene_portfolio,
    build_partner_shortlist,
    build_program_milestones,
    gene_score_report_rows,
    investor_diligence_rows,
    load_candidate_genes,
    load_research_organizations,
    organization_report_rows,
    rank_candidate_genes,
    rank_candidate_genes_with_literature,
    score_gene_query,
    score_gene_query_with_literature,
    scoring_method_card,
    stress_test_report_rows,
)
from gerodrug_sim.literature import DEFAULT_RESEARCH_DB, ResearchLibrary, fetch_pubmed_records
from gerodrug_sim.library import MoleculeLibrary
from gerodrug_sim.molecular_workflow import analyze_molecule
from gerodrug_sim.cli import _recommendation, _score_to_treatment_effect
from gerodrug_sim.data import load_candidate_drugs, load_evidence_sources, load_hallmarks, load_software_tools, load_trial_endpoints
from gerodrug_sim.reporting import render_markdown_report
from gerodrug_sim.reprogramming import (
    ReprogrammingFactorScore,
    combination_report_rows,
    design_reprogramming_combinations,
    design_tissue_reprogramming_plans,
    design_validation_experiment,
    evidence_attribution_rows,
    evidence_gap_rows,
    load_reprogramming_factors,
    rank_reprogramming_factors_with_literature,
    reprogramming_report_rows,
    safety_gate_rows,
    tissue_plan_report_rows,
)
from gerodrug_sim.scoring import DEFAULT_COMPONENT_WEIGHTS, CandidateScore, rank_candidates
from gerodrug_sim.simulation import VirtualTrialResult, run_virtual_trial


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "outputs" / "simulation_report.md"
DEFAULT_DILIGENCE_OUTPUT = ROOT / "outputs" / "investor_diligence.md"
DEFAULT_LIBRARY = ROOT / "data" / "asclepius_library.sqlite"


class AsclepiusDesktop(tk.Tk):
    """A local desktop cockpit for candidate ranking and virtual trials."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Asclepius")
        self.geometry("1480x940")
        self.minsize(1220, 760)
        self.configure(bg="#e8eeeb")

        self.condition_var = tk.StringVar(value="衰弱预防")
        self.participants_var = tk.IntVar(value=180)
        self.months_var = tk.IntVar(value=24)
        self.seed_var = tk.IntVar(value=42)
        self.top_var = tk.IntVar(value=5)
        self.smiles_var = tk.StringVar(value="CN(C)C(=N)N=C(N)N")
        self.gene_query_var = tk.StringVar(value="SIRT6")
        self.literature_query_var = tk.StringVar(value="partial reprogramming aging")
        self.literature_count_var = tk.StringVar(value="本地文献库：0 篇")
        self.status_var = tk.StringVar(value="就绪")
        self.library = MoleculeLibrary(DEFAULT_LIBRARY)
        self.research_library = ResearchLibrary(DEFAULT_RESEARCH_DB)
        self.candidate_genes = load_candidate_genes()
        self.research_orgs = load_research_organizations()
        self.current_molecular_result: dict[str, Any] | None = None
        self.weight_vars = {
            key: tk.DoubleVar(value=value)
            for key, value in DEFAULT_COMPONENT_WEIGHTS.items()
        }

        self._configure_style()
        self._build_layout()
        if not self.library.list_compounds():
            self.library.import_seed()
        self.refresh_library()
        self.refresh_literature()
        self.run_simulation(update_cards=True)
        self.notebook.select(self.core_section)
        self.core_notebook.select(self.reprogramming_tab)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Helvetica", 13), background="#e8eeeb", foreground="#192025")
        style.configure("Sidebar.TFrame", background="#fbfcfb")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Soft.TFrame", background="#f6f8f7")
        style.configure("Title.TLabel", background="#e8eeeb", foreground="#192025", font=("Helvetica", 31, "bold"))
        style.configure("Subtitle.TLabel", background="#e8eeeb", foreground="#53636f", font=("Helvetica", 13))
        style.configure("Eyebrow.TLabel", background="#e8eeeb", foreground="#1f8a70", font=("Helvetica", 11, "bold"))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#192025", font=("Helvetica", 15, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#63707a", font=("Helvetica", 11))
        style.configure("Sidebar.TLabel", background="#fbfcfb", foreground="#53636f", font=("Helvetica", 12))
        style.configure("Brand.TLabel", background="#fbfcfb", foreground="#192025", font=("Helvetica", 20, "bold"))
        style.configure("Accent.TButton", background="#1f8a70", foreground="#ffffff", font=("Helvetica", 13, "bold"), padding=10)
        style.map("Accent.TButton", background=[("active", "#176e5a")])
        style.configure("Treeview", rowheight=30, font=("Helvetica", 12), background="#ffffff", fieldbackground="#ffffff", borderwidth=0)
        style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))

    def _build_layout(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, style="Sidebar.TFrame", padding=(26, 24))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame")
        brand.grid(row=0, column=0, sticky="ew", pady=(0, 28))
        mark = tk.Label(brand, text="A", bg="#26364a", fg="white", width=3, height=1, font=("Helvetica", 22, "bold"))
        mark.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="n")
        ttk.Label(brand, text="Asclepius", style="Brand.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            brand,
            text="部分表观遗传重编程研究工作台",
            style="Sidebar.TLabel",
        ).grid(row=1, column=1, sticky="w")

        controls = ttk.Frame(sidebar, style="Sidebar.TFrame")
        controls.grid(row=1, column=0, sticky="new")
        controls.columnconfigure(0, weight=1)
        self._labeled_entry(controls, "重编程研究场景", self.condition_var, 0)
        self._number_grid(controls, 1)
        self._weight_controls(controls, 2)
        ttk.Label(controls, text="文献雷达关键词", style="Sidebar.TLabel").grid(row=5, column=0, sticky="w", pady=(14, 0))
        ttk.Entry(controls, textvariable=self.literature_query_var, width=28).grid(row=6, column=0, sticky="ew", pady=(6, 10))
        ttk.Button(controls, text="搜索部分重编程文献", command=self.fetch_literature, style="Accent.TButton").grid(
            row=7, column=0, sticky="ew", pady=(8, 0)
        )
        ttk.Button(controls, text="刷新重编程评分", command=self.run_simulation, style="Accent.TButton").grid(
            row=8, column=0, sticky="ew", pady=(10, 0)
        )

        workspace = ttk.Frame(self, padding=(30, 24))
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.columnconfigure(0, weight=1)
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(2, weight=1)

        header = ttk.Frame(workspace)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="ASCLEPIUS · PARTIAL EPIGENETIC REPROGRAMMING", style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w")
        self.title_label = ttk.Label(header, text="部分表观遗传重编程研发雷达", style="Title.TLabel")
        self.title_label.grid(row=1, column=0, sticky="w")
        ttk.Label(header, text="围绕 OSK/OSKM、低风险调控轴、文献证据和安全风险构建本地研发判断", style="Subtitle.TLabel").grid(row=2, column=0, sticky="w", pady=(2, 0))
        status = tk.Label(header, textvariable=self.status_var, bg="#ffffff", fg="#53636f", padx=18, pady=8, font=("Helvetica", 12, "bold"))
        status.grid(row=0, column=1, rowspan=3, sticky="e")

        self.metrics_frame = ttk.Frame(workspace)
        self.metrics_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        for column in range(4):
            self.metrics_frame.columnconfigure(column, weight=1)
        self.metric_labels: dict[str, tk.Label] = {}
        for column, key in enumerate(("首选重编程因子", "本地证据覆盖", "风险提示", "文献库规模")):
            frame = tk.Frame(self.metrics_frame, bg="#ffffff", highlightbackground="#d3dee2", highlightthickness=1)
            frame.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0 if column == 3 else 8))
            tk.Frame(frame, bg="#1f8a70", height=4).pack(fill="x")
            tk.Label(frame, text=key, bg="#ffffff", fg="#53636f", font=("Helvetica", 11)).pack(anchor="w", padx=16, pady=(14, 4))
            value = tk.Label(frame, text="-", bg="#ffffff", fg="#192025", font=("Helvetica", 17, "bold"), wraplength=190, justify="left")
            value.pack(anchor="w", padx=16, pady=(0, 16))
            self.metric_labels[key] = value

        self.notebook = ttk.Notebook(workspace)
        self.notebook.grid(row=2, column=0, columnspan=2, rowspan=2, sticky="nsew")

        self.core_section = ttk.Frame(self.notebook)
        evidence_section = ttk.Frame(self.notebook)
        execution_section = ttk.Frame(self.notebook)
        molecule_section = ttk.Frame(self.notebook)
        utility_section = ttk.Frame(self.notebook)
        self.notebook.add(self.core_section, text="核心重编程")
        self.notebook.add(evidence_section, text="数据与评分")
        self.notebook.add(execution_section, text="决策执行")
        self.notebook.add(molecule_section, text="分子辅助")
        self.notebook.add(utility_section, text="工具与旧版")

        self.core_notebook = self._section_notebook(self.core_section)
        evidence_notebook = self._section_notebook(evidence_section)
        execution_notebook = self._section_notebook(execution_section)
        molecule_notebook_root = self._section_notebook(molecule_section)
        utility_notebook = self._section_notebook(utility_section)

        reprogramming_tab = ttk.Frame(self.core_notebook, padding=14)
        combination_tab = ttk.Frame(self.core_notebook, padding=14)
        roadmap_tab = ttk.Frame(self.core_notebook, padding=14)
        database_tab = ttk.Frame(evidence_notebook, padding=14)
        gene_tab = ttk.Frame(evidence_notebook, padding=14)
        literature_tab = ttk.Frame(evidence_notebook, padding=14)
        decision_tab = ttk.Frame(execution_notebook, padding=14)
        program_tab = ttk.Frame(execution_notebook, padding=14)
        diligence_tab = ttk.Frame(execution_notebook, padding=14)
        molecule_tab = ttk.Frame(molecule_notebook_root, padding=14)
        target_tab = ttk.Frame(molecule_notebook_root, padding=14)
        docking_tab = ttk.Frame(molecule_notebook_root, padding=14)
        ranking_tab = ttk.Frame(utility_notebook, padding=14)
        resources_tab = ttk.Frame(utility_notebook, padding=14)
        self.reprogramming_tab = reprogramming_tab
        self.core_notebook.add(reprogramming_tab, text="因子评分")
        self.core_notebook.add(combination_tab, text="组合设计")
        self.core_notebook.add(roadmap_tab, text="组织路线")
        evidence_notebook.add(database_tab, text="数据库资产")
        evidence_notebook.add(gene_tab, text="基因评分")
        evidence_notebook.add(literature_tab, text="文献雷达")
        execution_notebook.add(decision_tab, text="决策台")
        execution_notebook.add(program_tab, text="研发闭环")
        execution_notebook.add(diligence_tab, text="尽调审计")
        molecule_notebook_root.add(molecule_tab, text="分子库与 ADMET")
        molecule_notebook_root.add(target_tab, text="靶点预测")
        molecule_notebook_root.add(docking_tab, text="结构对接")
        utility_notebook.add(ranking_tab, text="旧版候选排序")
        utility_notebook.add(resources_tab, text="软件与外部库")

        molecule_tab.columnconfigure(0, weight=1)
        molecule_tab.columnconfigure(1, weight=1)
        molecule_tab.rowconfigure(0, weight=1)
        molecule_tab.rowconfigure(1, weight=1)
        library_panel = self._panel(molecule_tab, "分子库")
        library_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 12))
        library_panel.rowconfigure(1, weight=1)
        library_panel.columnconfigure(0, weight=1)
        library_actions = ttk.Frame(library_panel, style="Panel.TFrame")
        library_actions.grid(row=0, column=0, sticky="e", padx=16, pady=(8, 0))
        ttk.Button(library_actions, text="导入示例", command=self.import_seed_library).grid(row=0, column=0, padx=4)
        ttk.Button(library_actions, text="保存当前分析", command=self.save_current_analysis).grid(row=0, column=1, padx=4)
        self.library_tree = ttk.Treeview(
            library_panel,
            columns=("smiles", "notes"),
            show="tree headings",
            selectmode="browse",
            height=5,
        )
        self.library_tree.heading("#0", text="名称")
        self.library_tree.heading("smiles", text="SMILES")
        self.library_tree.heading("notes", text="备注")
        self.library_tree.column("#0", width=140)
        self.library_tree.column("smiles", width=360)
        self.library_tree.column("notes", width=260)
        self.library_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.library_tree.bind("<<TreeviewSelect>>", self.on_library_select)

        mol_panel = self._panel(molecule_tab, "分子性质与 ADMET")
        mol_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        mol_panel.rowconfigure(1, weight=1)
        mol_panel.columnconfigure(0, weight=1)
        molecule_notebook = ttk.Notebook(mol_panel)
        molecule_notebook.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        property_frame = ttk.Frame(molecule_notebook, padding=8)
        admet_frame = ttk.Frame(molecule_notebook, padding=8)
        property_frame.rowconfigure(0, weight=1)
        property_frame.columnconfigure(0, weight=1)
        admet_frame.rowconfigure(0, weight=1)
        admet_frame.columnconfigure(0, weight=1)
        molecule_notebook.add(property_frame, text="结构指标")
        molecule_notebook.add(admet_frame, text="ADMET 解释")
        self.property_tree = ttk.Treeview(
            property_frame,
            columns=("value", "note"),
            show="tree headings",
        )
        self.property_tree.heading("#0", text="指标")
        self.property_tree.heading("value", text="数值")
        self.property_tree.heading("note", text="解释")
        self.property_tree.column("#0", width=150)
        self.property_tree.column("value", width=120, anchor="center")
        self.property_tree.column("note", width=320)
        self.property_tree.grid(row=0, column=0, sticky="nsew")
        self.molecule_text = tk.Text(admet_frame, wrap="word", bg="#ffffff", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.molecule_text.grid(row=0, column=0, sticky="nsew")
        score_panel = self._panel(molecule_tab, "Asclepius 分子评分")
        score_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        score_panel.rowconfigure(2, weight=1)
        score_panel.columnconfigure(0, weight=1)
        self.score_canvas = tk.Canvas(score_panel, height=210, bg="#f8faf9", highlightthickness=1, highlightbackground="#d8e1e6")
        self.score_canvas.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.molecular_score_text = tk.Text(score_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.molecular_score_text.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))

        target_tab.columnconfigure(0, weight=1)
        target_tab.rowconfigure(0, weight=1)
        target_panel = self._panel(target_tab, "相似性靶点预测")
        target_panel.grid(row=0, column=0, sticky="nsew")
        target_panel.rowconfigure(1, weight=1)
        target_panel.columnconfigure(0, weight=1)
        self.target_tree = ttk.Treeview(
            target_panel,
            columns=("probability", "hallmark", "pathway", "ligand", "similarity", "pdb"),
            show="tree headings",
        )
        self.target_tree.heading("#0", text="靶点")
        self.target_tree.heading("probability", text="概率")
        self.target_tree.heading("hallmark", text="衰老标志")
        self.target_tree.heading("pathway", text="通路")
        self.target_tree.heading("ligand", text="最相似配体")
        self.target_tree.heading("similarity", text="相似度")
        self.target_tree.heading("pdb", text="PDB")
        self.target_tree.column("#0", width=160)
        self.target_tree.column("probability", width=80, anchor="center")
        self.target_tree.column("hallmark", width=160)
        self.target_tree.column("pathway", width=150)
        self.target_tree.column("ligand", width=160)
        self.target_tree.column("similarity", width=80, anchor="center")
        self.target_tree.column("pdb", width=100)
        self.target_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        docking_tab.columnconfigure(0, weight=1)
        docking_tab.rowconfigure(0, weight=1)
        docking_panel = self._panel(docking_tab, "对接结果")
        docking_panel.grid(row=0, column=0, sticky="nsew")
        docking_panel.rowconfigure(1, weight=1)
        docking_panel.columnconfigure(0, weight=1)
        self.docking_tree = ttk.Treeview(
            docking_panel,
            columns=("score", "norm", "backend", "notes"),
            show="tree headings",
        )
        self.docking_tree.heading("#0", text="靶点")
        self.docking_tree.heading("score", text="估算结合能")
        self.docking_tree.heading("norm", text="归一化")
        self.docking_tree.heading("backend", text="后端")
        self.docking_tree.heading("notes", text="说明")
        self.docking_tree.column("#0", width=160)
        self.docking_tree.column("score", width=110, anchor="center")
        self.docking_tree.column("norm", width=80, anchor="center")
        self.docking_tree.column("backend", width=110, anchor="center")
        self.docking_tree.column("notes", width=520)
        self.docking_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        reprogramming_tab.columnconfigure(0, weight=1)
        reprogramming_tab.columnconfigure(1, weight=1)
        reprogramming_tab.rowconfigure(0, weight=1)
        reprogramming_tab.rowconfigure(1, weight=1)
        reprogramming_panel = self._panel(reprogramming_tab, "部分表观遗传重编程因子排名")
        reprogramming_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 18))
        reprogramming_panel.rowconfigure(1, weight=1)
        reprogramming_panel.columnconfigure(0, weight=1)
        self.reprogramming_tree = ttk.Treeview(
            reprogramming_panel,
            columns=("score", "safety", "papers", "basis", "tissues", "recommendation"),
            show="tree headings",
            selectmode="browse",
        )
        self.reprogramming_tree.heading("#0", text="因子/组合")
        self.reprogramming_tree.heading("score", text="优先级")
        self.reprogramming_tree.heading("safety", text="安全分")
        self.reprogramming_tree.heading("papers", text="文献")
        self.reprogramming_tree.heading("basis", text="评分")
        self.reprogramming_tree.heading("tissues", text="组织")
        self.reprogramming_tree.heading("recommendation", text="建议")
        self.reprogramming_tree.column("#0", width=220, anchor="w")
        self.reprogramming_tree.column("score", width=80, anchor="center")
        self.reprogramming_tree.column("safety", width=80, anchor="center")
        self.reprogramming_tree.column("papers", width=70, anchor="center")
        self.reprogramming_tree.column("basis", width=110, anchor="center")
        self.reprogramming_tree.column("tissues", width=250, anchor="w")
        self.reprogramming_tree.column("recommendation", width=170, anchor="w")
        self.reprogramming_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.reprogramming_tree.bind("<<TreeviewSelect>>", self.on_reprogramming_select)

        factor_panel = self._panel(reprogramming_tab, "因子解释")
        factor_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        factor_panel.rowconfigure(1, weight=1)
        factor_panel.columnconfigure(0, weight=1)
        self.reprogramming_detail_text = tk.Text(factor_panel, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.reprogramming_detail_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        factor_score_panel = self._panel(reprogramming_tab, "评分过程与验证路径")
        factor_score_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        factor_score_panel.rowconfigure(1, weight=1)
        factor_score_panel.columnconfigure(0, weight=1)
        self.reprogramming_score_text = tk.Text(factor_score_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.reprogramming_score_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        combination_tab.columnconfigure(0, weight=1)
        combination_tab.columnconfigure(1, weight=1)
        combination_tab.rowconfigure(0, weight=1)
        combination_tab.rowconfigure(1, weight=1)
        combination_panel = self._panel(combination_tab, "重编程组合策略")
        combination_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 18))
        combination_panel.rowconfigure(1, weight=1)
        combination_panel.columnconfigure(0, weight=1)
        self.combination_tree = ttk.Treeview(
            combination_panel,
            columns=("score", "safety", "risk", "target", "factors"),
            show="tree headings",
            selectmode="browse",
        )
        self.combination_tree.heading("#0", text="组合")
        self.combination_tree.heading("score", text="优先级")
        self.combination_tree.heading("safety", text="安全下限")
        self.combination_tree.heading("risk", text="风险档")
        self.combination_tree.heading("target", text="目标组织")
        self.combination_tree.heading("factors", text="因子")
        self.combination_tree.column("#0", width=220, anchor="w")
        self.combination_tree.column("score", width=80, anchor="center")
        self.combination_tree.column("safety", width=90, anchor="center")
        self.combination_tree.column("risk", width=90, anchor="center")
        self.combination_tree.column("target", width=120, anchor="center")
        self.combination_tree.column("factors", width=520, anchor="w")
        self.combination_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.combination_tree.bind("<<TreeviewSelect>>", self.on_combination_select)

        combination_detail_panel = self._panel(combination_tab, "组合逻辑")
        combination_detail_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        combination_detail_panel.rowconfigure(1, weight=1)
        combination_detail_panel.columnconfigure(0, weight=1)
        self.combination_detail_text = tk.Text(combination_detail_panel, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.combination_detail_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        combination_plan_panel = self._panel(combination_tab, "验证路径")
        combination_plan_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        combination_plan_panel.rowconfigure(1, weight=1)
        combination_plan_panel.columnconfigure(0, weight=1)
        self.combination_plan_text = tk.Text(combination_plan_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.combination_plan_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        roadmap_tab.columnconfigure(0, weight=1)
        roadmap_tab.columnconfigure(1, weight=1)
        roadmap_tab.rowconfigure(0, weight=1)
        roadmap_tab.rowconfigure(1, weight=1)
        tissue_panel = self._panel(roadmap_tab, "组织路线图")
        tissue_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 18))
        tissue_panel.rowconfigure(1, weight=1)
        tissue_panel.columnconfigure(0, weight=1)
        self.tissue_plan_tree = ttk.Treeview(
            tissue_panel,
            columns=("priority", "factors", "combination", "model"),
            show="tree headings",
            selectmode="browse",
        )
        self.tissue_plan_tree.heading("#0", text="组织")
        self.tissue_plan_tree.heading("priority", text="优先级")
        self.tissue_plan_tree.heading("factors", text="首选因子")
        self.tissue_plan_tree.heading("combination", text="首选组合")
        self.tissue_plan_tree.heading("model", text="模型")
        self.tissue_plan_tree.column("#0", width=150, anchor="w")
        self.tissue_plan_tree.column("priority", width=80, anchor="center")
        self.tissue_plan_tree.column("factors", width=260, anchor="w")
        self.tissue_plan_tree.column("combination", width=230, anchor="w")
        self.tissue_plan_tree.column("model", width=460, anchor="w")
        self.tissue_plan_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.tissue_plan_tree.bind("<<TreeviewSelect>>", self.on_tissue_plan_select)

        safety_panel = self._panel(roadmap_tab, "安全闸门矩阵")
        safety_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        safety_panel.rowconfigure(1, weight=1)
        safety_panel.columnconfigure(0, weight=1)
        self.safety_gate_text = tk.Text(safety_panel, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.safety_gate_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        gap_panel = self._panel(roadmap_tab, "证据缺口与 AI 任务")
        gap_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        gap_panel.rowconfigure(1, weight=1)
        gap_panel.columnconfigure(0, weight=1)
        self.evidence_gap_text = tk.Text(gap_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.evidence_gap_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        database_tab.columnconfigure(0, weight=1)
        database_tab.columnconfigure(1, weight=1)
        database_tab.rowconfigure(1, weight=1)
        asset_panel = self._panel(database_tab, "数据库完成度")
        asset_panel.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        asset_panel.columnconfigure(0, weight=1)
        self.asset_summary_text = tk.Text(asset_panel, height=7, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.asset_summary_text.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

        gene_asset_panel = self._panel(database_tab, "候选基因库")
        gene_asset_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        gene_asset_panel.rowconfigure(1, weight=1)
        gene_asset_panel.columnconfigure(0, weight=1)
        self.asset_gene_tree = ttk.Treeview(
            gene_asset_panel,
            columns=("score", "risk", "tissues", "recommendation"),
            show="tree headings",
            selectmode="browse",
        )
        self.asset_gene_tree.heading("#0", text="基因")
        self.asset_gene_tree.heading("score", text="评分")
        self.asset_gene_tree.heading("risk", text="风险")
        self.asset_gene_tree.heading("tissues", text="组织")
        self.asset_gene_tree.heading("recommendation", text="建议")
        self.asset_gene_tree.column("#0", width=110, anchor="w")
        self.asset_gene_tree.column("score", width=70, anchor="center")
        self.asset_gene_tree.column("risk", width=70, anchor="center")
        self.asset_gene_tree.column("tissues", width=190, anchor="w")
        self.asset_gene_tree.column("recommendation", width=260, anchor="w")
        self.asset_gene_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        org_asset_panel = self._panel(database_tab, "公司/课题组/科研机构")
        org_asset_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        org_asset_panel.rowconfigure(1, weight=1)
        org_asset_panel.columnconfigure(0, weight=1)
        self.asset_org_tree = ttk.Treeview(
            org_asset_panel,
            columns=("type", "country", "focus", "tags"),
            show="tree headings",
        )
        self.asset_org_tree.heading("#0", text="名称")
        self.asset_org_tree.heading("type", text="类型")
        self.asset_org_tree.heading("country", text="国家")
        self.asset_org_tree.heading("focus", text="方向")
        self.asset_org_tree.heading("tags", text="标签")
        self.asset_org_tree.column("#0", width=180, anchor="w")
        self.asset_org_tree.column("type", width=110, anchor="center")
        self.asset_org_tree.column("country", width=80, anchor="center")
        self.asset_org_tree.column("focus", width=250, anchor="w")
        self.asset_org_tree.column("tags", width=220, anchor="w")
        self.asset_org_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        gene_tab.columnconfigure(0, weight=1)
        gene_tab.columnconfigure(1, weight=1)
        gene_tab.rowconfigure(1, weight=1)
        gene_controls = ttk.Frame(gene_tab)
        gene_controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        gene_controls.columnconfigure(1, weight=1)
        ttk.Label(gene_controls, text="输入基因 Symbol", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Entry(gene_controls, textvariable=self.gene_query_var).grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Button(gene_controls, text="评分基因", command=self.run_gene_analysis, style="Accent.TButton").grid(row=0, column=2)

        gene_score_panel = self._panel(gene_tab, "候选基因评分")
        gene_score_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        gene_score_panel.rowconfigure(1, weight=1)
        gene_score_panel.columnconfigure(0, weight=1)
        self.gene_score_tree = ttk.Treeview(
            gene_score_panel,
            columns=("score", "young", "risk", "band", "tissues"),
            show="tree headings",
            selectmode="browse",
        )
        self.gene_score_tree.heading("#0", text="基因")
        self.gene_score_tree.heading("score", text="总分")
        self.gene_score_tree.heading("young", text="年轻化")
        self.gene_score_tree.heading("risk", text="风险")
        self.gene_score_tree.heading("band", text="风险档")
        self.gene_score_tree.heading("tissues", text="组织")
        self.gene_score_tree.column("#0", width=120, anchor="w")
        self.gene_score_tree.column("score", width=70, anchor="center")
        self.gene_score_tree.column("young", width=80, anchor="center")
        self.gene_score_tree.column("risk", width=70, anchor="center")
        self.gene_score_tree.column("band", width=70, anchor="center")
        self.gene_score_tree.column("tissues", width=260, anchor="w")
        self.gene_score_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.gene_score_tree.bind("<<TreeviewSelect>>", self.on_gene_select)

        gene_detail_panel = self._panel(gene_tab, "基因解释")
        gene_detail_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        gene_detail_panel.rowconfigure(1, weight=1)
        gene_detail_panel.columnconfigure(0, weight=1)
        self.gene_detail_text = tk.Text(gene_detail_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.gene_detail_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        decision_tab.columnconfigure(0, weight=1)
        decision_tab.columnconfigure(1, weight=1)
        decision_tab.rowconfigure(0, weight=1)
        decision_tab.rowconfigure(1, weight=1)
        portfolio_panel = self._panel(decision_tab, "基因研发组合分层")
        portfolio_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 18))
        portfolio_panel.rowconfigure(1, weight=1)
        portfolio_panel.columnconfigure(0, weight=1)
        self.portfolio_tree = ttk.Treeview(
            portfolio_panel,
            columns=("bucket", "score", "safety", "provenance", "papers", "action"),
            show="tree headings",
            selectmode="browse",
        )
        self.portfolio_tree.heading("#0", text="基因")
        self.portfolio_tree.heading("bucket", text="分层")
        self.portfolio_tree.heading("score", text="评分")
        self.portfolio_tree.heading("safety", text="安全")
        self.portfolio_tree.heading("provenance", text="溯源")
        self.portfolio_tree.heading("papers", text="论文")
        self.portfolio_tree.heading("action", text="动作")
        self.portfolio_tree.column("#0", width=100, anchor="w")
        self.portfolio_tree.column("bucket", width=100, anchor="center")
        self.portfolio_tree.column("score", width=70, anchor="center")
        self.portfolio_tree.column("safety", width=70, anchor="center")
        self.portfolio_tree.column("provenance", width=70, anchor="center")
        self.portfolio_tree.column("papers", width=70, anchor="center")
        self.portfolio_tree.column("action", width=520, anchor="w")
        self.portfolio_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        stress_panel = self._panel(decision_tab, "权重压力测试")
        stress_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        stress_panel.rowconfigure(1, weight=1)
        stress_panel.columnconfigure(0, weight=1)
        self.stress_text = tk.Text(stress_panel, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.stress_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        pack_panel = self._panel(decision_tab, "基因证据包")
        pack_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        pack_panel.rowconfigure(1, weight=1)
        pack_panel.columnconfigure(0, weight=1)
        self.evidence_pack_text = tk.Text(pack_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.evidence_pack_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        program_tab.columnconfigure(0, weight=1)
        program_tab.columnconfigure(1, weight=1)
        program_tab.rowconfigure(0, weight=1)
        program_tab.rowconfigure(1, weight=1)
        milestone_panel = self._panel(program_tab, "90 天研发里程碑")
        milestone_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 9), pady=(0, 18))
        milestone_panel.rowconfigure(1, weight=1)
        milestone_panel.columnconfigure(0, weight=1)
        self.milestone_tree = ttk.Treeview(
            milestone_panel,
            columns=("objective", "deliverable", "gate"),
            show="tree headings",
            selectmode="browse",
        )
        self.milestone_tree.heading("#0", text="阶段")
        self.milestone_tree.heading("objective", text="目标")
        self.milestone_tree.heading("deliverable", text="交付物")
        self.milestone_tree.heading("gate", text="退出门槛")
        self.milestone_tree.column("#0", width=90, anchor="w")
        self.milestone_tree.column("objective", width=220, anchor="w")
        self.milestone_tree.column("deliverable", width=360, anchor="w")
        self.milestone_tree.column("gate", width=280, anchor="w")
        self.milestone_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        backlog_panel = self._panel(program_tab, "实验/证据 Backlog")
        backlog_panel.grid(row=0, column=1, sticky="nsew", padx=(9, 0), pady=(0, 18))
        backlog_panel.rowconfigure(1, weight=1)
        backlog_panel.columnconfigure(0, weight=1)
        self.backlog_tree = ttk.Treeview(
            backlog_panel,
            columns=("lane", "priority", "target", "deliverable", "status"),
            show="tree headings",
        )
        self.backlog_tree.heading("#0", text="任务")
        self.backlog_tree.heading("lane", text="泳道")
        self.backlog_tree.heading("priority", text="优先")
        self.backlog_tree.heading("target", text="对象")
        self.backlog_tree.heading("deliverable", text="交付物")
        self.backlog_tree.heading("status", text="状态")
        self.backlog_tree.column("#0", width=96, anchor="w")
        self.backlog_tree.column("lane", width=110, anchor="center")
        self.backlog_tree.column("priority", width=56, anchor="center")
        self.backlog_tree.column("target", width=86, anchor="center")
        self.backlog_tree.column("deliverable", width=430, anchor="w")
        self.backlog_tree.column("status", width=80, anchor="center")
        self.backlog_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        partner_panel = self._panel(program_tab, "合作方短名单")
        partner_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        partner_panel.rowconfigure(1, weight=1)
        partner_panel.columnconfigure(0, weight=1)
        self.partner_text = tk.Text(partner_panel, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.partner_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        data_room_panel = self._panel(program_tab, "Data Room 清单")
        data_room_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        data_room_panel.rowconfigure(1, weight=1)
        data_room_panel.columnconfigure(0, weight=1)
        self.data_room_text = tk.Text(data_room_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.data_room_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        diligence_tab.columnconfigure(0, weight=1)
        diligence_tab.columnconfigure(1, weight=1)
        diligence_tab.rowconfigure(0, weight=1)
        diligence_tab.rowconfigure(1, weight=1)
        audit_panel = self._panel(diligence_tab, "证据可信度审计")
        audit_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 9), pady=(0, 18))
        audit_panel.rowconfigure(1, weight=1)
        audit_panel.columnconfigure(0, weight=1)
        self.audit_text = tk.Text(audit_panel, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.audit_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        diligence_panel = self._panel(diligence_tab, "投资人问答")
        diligence_panel.grid(row=0, column=1, sticky="nsew", padx=(9, 0), pady=(0, 18))
        diligence_panel.rowconfigure(1, weight=1)
        diligence_panel.columnconfigure(0, weight=1)
        self.diligence_text = tk.Text(diligence_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.diligence_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        provenance_panel = self._panel(diligence_tab, "文献支撑 Top 基因")
        provenance_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")
        provenance_panel.rowconfigure(1, weight=1)
        provenance_panel.columnconfigure(0, weight=1)
        self.provenance_tree = ttk.Treeview(
            provenance_panel,
            columns=("score", "provenance", "papers", "basis", "risk", "recommendation"),
            show="tree headings",
        )
        self.provenance_tree.heading("#0", text="基因")
        self.provenance_tree.heading("score", text="评分")
        self.provenance_tree.heading("provenance", text="溯源")
        self.provenance_tree.heading("papers", text="论文")
        self.provenance_tree.heading("basis", text="依据")
        self.provenance_tree.heading("risk", text="风险")
        self.provenance_tree.heading("recommendation", text="建议")
        self.provenance_tree.column("#0", width=120, anchor="w")
        self.provenance_tree.column("score", width=70, anchor="center")
        self.provenance_tree.column("provenance", width=70, anchor="center")
        self.provenance_tree.column("papers", width=70, anchor="center")
        self.provenance_tree.column("basis", width=110, anchor="center")
        self.provenance_tree.column("risk", width=70, anchor="center")
        self.provenance_tree.column("recommendation", width=360, anchor="w")
        self.provenance_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        literature_tab.columnconfigure(0, weight=1)
        literature_tab.columnconfigure(1, weight=1)
        literature_tab.rowconfigure(1, weight=1)
        literature_tab.rowconfigure(2, weight=1)
        literature_controls = ttk.Frame(literature_tab)
        literature_controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        literature_controls.columnconfigure(0, weight=1)
        ttk.Entry(literature_controls, textvariable=self.literature_query_var).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(literature_controls, text="搜索 PubMed", command=self.fetch_literature, style="Accent.TButton").grid(row=0, column=1, padx=(0, 8))
        ttk.Button(literature_controls, text="刷新本地库", command=self.refresh_literature).grid(row=0, column=2)
        ttk.Label(literature_controls, textvariable=self.literature_count_var, style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        literature_panel = self._panel(literature_tab, "本地文献库")
        literature_panel.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 18))
        literature_panel.rowconfigure(1, weight=1)
        literature_panel.columnconfigure(0, weight=1)
        self.literature_tree = ttk.Treeview(
            literature_panel,
            columns=("year", "journal", "score", "evidence", "factors", "risks"),
            show="tree headings",
            selectmode="browse",
        )
        self.literature_tree.heading("#0", text="标题")
        self.literature_tree.heading("year", text="年份")
        self.literature_tree.heading("journal", text="期刊")
        self.literature_tree.heading("score", text="证据分")
        self.literature_tree.heading("evidence", text="证据")
        self.literature_tree.heading("factors", text="匹配因子")
        self.literature_tree.heading("risks", text="风险")
        self.literature_tree.column("#0", width=420, anchor="w")
        self.literature_tree.column("year", width=70, anchor="center")
        self.literature_tree.column("journal", width=180, anchor="w")
        self.literature_tree.column("score", width=80, anchor="center")
        self.literature_tree.column("evidence", width=90, anchor="center")
        self.literature_tree.column("factors", width=160, anchor="w")
        self.literature_tree.column("risks", width=220, anchor="w")
        self.literature_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.literature_tree.bind("<<TreeviewSelect>>", self.on_literature_select)

        literature_detail_panel = self._panel(literature_tab, "结构化摘要")
        literature_detail_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 9))
        literature_detail_panel.rowconfigure(1, weight=1)
        literature_detail_panel.columnconfigure(0, weight=1)
        self.literature_detail_text = tk.Text(literature_detail_panel, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.literature_detail_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        literature_signal_panel = self._panel(literature_tab, "抽取信号")
        literature_signal_panel.grid(row=2, column=1, sticky="nsew", padx=(9, 0))
        literature_signal_panel.rowconfigure(1, weight=1)
        literature_signal_panel.columnconfigure(0, weight=1)
        self.literature_signal_text = tk.Text(literature_signal_panel, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.literature_signal_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        ranking_panel = self._panel(ranking_tab, "候选药排名")
        ranking_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 9), pady=(0, 18))
        ranking_tab.columnconfigure(0, weight=1)
        ranking_tab.columnconfigure(1, weight=1)
        ranking_tab.rowconfigure(0, weight=1)
        ranking_tab.rowconfigure(1, weight=1)
        ranking_panel.rowconfigure(1, weight=1)
        ranking_panel.columnconfigure(0, weight=1)
        self.candidate_tree = ttk.Treeview(
            ranking_panel,
            columns=("score", "safety", "translation", "decision"),
            show="tree headings",
            selectmode="browse",
        )
        self.candidate_tree.heading("#0", text="候选药")
        self.candidate_tree.heading("score", text="评分")
        self.candidate_tree.heading("safety", text="安全性")
        self.candidate_tree.heading("translation", text="转化证据")
        self.candidate_tree.heading("decision", text="建议")
        self.candidate_tree.column("#0", width=190, anchor="w")
        self.candidate_tree.column("score", width=72, anchor="center")
        self.candidate_tree.column("safety", width=72, anchor="center")
        self.candidate_tree.column("translation", width=92, anchor="center")
        self.candidate_tree.column("decision", width=160, anchor="w")
        self.candidate_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        chart_panel = self._panel(ranking_tab, "虚拟试验信号")
        chart_panel.grid(row=0, column=1, sticky="nsew", padx=(9, 0), pady=(0, 18))
        chart_panel.rowconfigure(1, weight=1)
        chart_panel.columnconfigure(0, weight=1)
        self.chart = tk.Canvas(chart_panel, height=280, bg="#f6f8f7", highlightthickness=1, highlightbackground="#d8e1e6")
        self.chart.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        hallmark_panel = self._panel(ranking_tab, "研发知识库")
        hallmark_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 9))
        hallmark_panel.columnconfigure(0, weight=1)
        self.hallmark_text = tk.Text(hallmark_panel, height=9, wrap="word", bg="#ffffff", fg="#30404a", relief="flat", font=("Helvetica", 12))
        self.hallmark_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        report_panel = self._panel(ranking_tab, "报告预览")
        report_panel.grid(row=1, column=1, sticky="nsew", padx=(9, 0))
        report_panel.rowconfigure(1, weight=1)
        report_panel.columnconfigure(0, weight=1)
        self.report_text = tk.Text(report_panel, height=9, wrap="word", bg="#f8faf9", fg="#24313a", relief="flat", font=("Menlo", 11))
        self.report_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        resources_tab.columnconfigure(0, weight=1)
        resources_tab.rowconfigure(0, weight=1)
        resources_panel = self._panel(resources_tab, "软件、数据库与文献来源")
        resources_panel.grid(row=0, column=0, sticky="nsew")
        resources_panel.rowconfigure(1, weight=1)
        resources_panel.columnconfigure(0, weight=1)
        self.resources_text = tk.Text(resources_panel, wrap="word", bg="#ffffff", fg="#24313a", relief="flat", font=("Helvetica", 12))
        self.resources_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def refresh_library(self) -> None:
        if not hasattr(self, "library_tree"):
            return
        self.library_tree.delete(*self.library_tree.get_children())
        for compound in self.library.list_compounds():
            self.library_tree.insert(
                "",
                "end",
                iid=str(compound.compound_id),
                text=compound.name,
                values=(compound.smiles, compound.notes),
            )

    def import_seed_library(self) -> None:
        imported = self.library.import_seed()
        self.refresh_library()
        self.status_var.set(f"已导入/更新 {imported} 个示例分子")

    def on_library_select(self, _event: object) -> None:
        selected = self.library_tree.selection()
        if not selected:
            return
        item = self.library_tree.item(selected[0])
        values = item.get("values", [])
        if values:
            self.smiles_var.set(str(values[0]))
            self.run_molecular_analysis()

    def save_current_analysis(self) -> None:
        if self.current_molecular_result is None:
            messagebox.showinfo("没有分析结果", "请先分析一个 SMILES。")
            return
        smiles = self.current_molecular_result["properties"]["smiles"]
        name = self.smiles_var.get()[:32] or "未命名分子"
        compound = self.library.upsert_compound(name=name, smiles=smiles, notes="GUI 保存")
        self.library.store_analysis(compound.compound_id, self.current_molecular_result)
        self.refresh_library()
        self.status_var.set("当前分子分析已保存")

    def fetch_literature(self) -> None:
        try:
            query = self.literature_query_var.get().strip()
            if not query:
                messagebox.showinfo("缺少关键词", "请输入 PubMed 搜索关键词。")
                return
            self.status_var.set("检索 PubMed 中")
            self.update_idletasks()
            papers = fetch_pubmed_records(query, retmax=20)
            imported = self.research_library.import_papers(papers)
            self.refresh_literature()
            self.status_var.set(f"已导入/更新 {imported} 篇文献")
        except Exception as exc:
            self.status_var.set("文献检索失败")
            messagebox.showerror("PubMed 检索出错", str(exc))

    def refresh_literature(self) -> None:
        if not hasattr(self, "literature_tree"):
            return
        query = self.literature_query_var.get().strip()
        papers = self.research_library.search_papers(query, limit=100) if query else self.research_library.list_papers(limit=100)
        self.literature_tree.delete(*self.literature_tree.get_children())
        for paper in papers:
            self.literature_tree.insert(
                "",
                "end",
                iid=str(paper.paper_id),
                text=paper.title[:110],
                values=(
                    paper.year or "-",
                    paper.journal[:36],
                    _score(paper.signals.evidence_score),
                    paper.signals.evidence_level,
                    "；".join(paper.signals.matched_factors) or "-",
                    "；".join(paper.signals.safety_risks) or "-",
                ),
            )
        self.literature_count_var.set(f"显示 {len(papers)} 篇；本地库 {len(self.research_library.list_papers(limit=10000))} 篇")
        self._render_literature_detail(papers[0] if papers else None)

    def on_literature_select(self, _event: object) -> None:
        selected = self.literature_tree.selection()
        if not selected:
            return
        paper_id = int(selected[0])
        paper = next((item for item in self.research_library.list_papers(limit=200) if item.paper_id == paper_id), None)
        self._render_literature_detail(paper)

    def _render_literature_detail(self, paper: Any | None) -> None:
        if not hasattr(self, "literature_detail_text"):
            return
        self.literature_detail_text.delete("1.0", "end")
        self.literature_signal_text.delete("1.0", "end")
        if paper is None:
            self.literature_detail_text.insert("1.0", "本地文献库为空。输入关键词后点击“搜索 PubMed”开始积累资料。")
            return
        self.literature_detail_text.insert(
            "1.0",
            "\n".join(
                [
                    paper.title,
                    "",
                    f"{paper.journal} · {paper.year}",
                    f"PMID：{paper.pmid}",
                    f"DOI：{paper.doi or '-'}",
                    f"链接：{paper.url}",
                    "",
                    paper.abstract or "无摘要。",
                ]
            ),
        )
        signals = paper.signals
        self.literature_signal_text.insert(
            "1.0",
            "\n".join(
                [
                    f"证据等级：{signals.evidence_level}",
                    f"证据分：{_score(signals.evidence_score)}",
                    f"分类：{_join_or_dash(signals.categories)}",
                    f"干预：{_join_or_dash(signals.interventions)}",
                    f"匹配因子：{_join_or_dash(signals.matched_factors)}",
                    f"组织/细胞：{_join_or_dash(signals.tissues)}",
                    f"模型：{_join_or_dash(signals.models)}",
                    f"Readout：{_join_or_dash(signals.readouts)}",
                    f"安全风险：{_join_or_dash(signals.safety_risks)}",
                ]
            ),
        )

    def _section_notebook(self, parent: ttk.Frame) -> ttk.Notebook:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        notebook = ttk.Notebook(parent)
        notebook.grid(row=0, column=0, sticky="nsew")
        return notebook

    def _panel(self, parent: ttk.Frame, title: str) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Panel.TFrame")
        ttk.Label(panel, text=title, style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", padx=16, pady=14)
        return panel

    def _labeled_entry(self, parent: ttk.Frame, label: str, variable: tk.Variable, row: int) -> None:
        ttk.Label(parent, text=label, style="Sidebar.TLabel").grid(row=row * 2, column=0, sticky="w")
        ttk.Entry(parent, textvariable=variable, width=28).grid(row=row * 2 + 1, column=0, sticky="ew", pady=(6, 14))

    def _number_grid(self, parent: ttk.Frame, start_row: int) -> None:
        frame = ttk.Frame(parent, style="Sidebar.TFrame")
        frame.grid(row=start_row * 2, column=0, sticky="ew", pady=(2, 14))
        for column in range(2):
            frame.columnconfigure(column, weight=1)
        values = (
            ("受试者数", self.participants_var),
            ("试验月数", self.months_var),
            ("随机种子", self.seed_var),
            ("显示前 N", self.top_var),
        )
        for index, (label, variable) in enumerate(values):
            row, column = divmod(index, 2)
            ttk.Label(frame, text=label, style="Sidebar.TLabel").grid(row=row * 2, column=column, sticky="w", padx=(0, 10))
            ttk.Entry(frame, textvariable=variable, width=12).grid(row=row * 2 + 1, column=column, sticky="ew", padx=(0, 10), pady=(6, 12))

    def _weight_controls(self, parent: ttk.Frame, row: int) -> None:
        frame = tk.LabelFrame(parent, text="评分权重", bg="#fbfcfb", fg="#53636f", padx=12, pady=10)
        frame.grid(row=row * 2, column=0, sticky="ew")
        frame.columnconfigure(1, weight=1)
        labels = {
            "hallmark_target": "衰老标志靶向",
            "expression_reversal": "表达逆转",
            "safety": "安全性",
            "translational_evidence": "转化证据",
            "trial_feasibility": "试验可行性",
            "regulatory_readiness": "监管成熟度",
            "biomarker_relevance": "标志物相关性",
        }
        for index, (key, label) in enumerate(labels.items()):
            tk.Label(frame, text=label, bg="#fbfcfb", fg="#53636f", font=("Helvetica", 12)).grid(row=index, column=0, sticky="w", pady=5)
            tk.Scale(
                frame,
                from_=0,
                to=1,
                resolution=0.01,
                orient="horizontal",
                variable=self.weight_vars[key],
                showvalue=False,
                bg="#fbfcfb",
                highlightthickness=0,
                troughcolor="#dfe7e8",
                activebackground="#1f8a70",
            ).grid(row=index, column=1, sticky="ew", padx=10)
            tk.Label(frame, textvariable=self.weight_vars[key], bg="#fbfcfb", fg="#192025", width=4, font=("Helvetica", 11)).grid(row=index, column=2, sticky="e")

    def run_molecular_analysis(self) -> None:
        try:
            self.status_var.set("分析中")
            self.update_idletasks()
            result = analyze_molecule(self.smiles_var.get())
            self.current_molecular_result = result
            self._render_molecule(result)
            self.status_var.set("就绪")
        except Exception as exc:
            self.status_var.set("错误")
            messagebox.showerror("分子分析出错", str(exc))

    def _render_molecule(self, result: Mapping[str, Any]) -> None:
        props = result["properties"]

        self.property_tree.delete(*self.property_tree.get_children())
        property_rows = [
            ("SMILES", props["smiles"], "输入或标准化后的结构"),
            ("分子式", props["formula"], "由结构估算"),
            ("重原子 / 杂原子", f"{props['heavy_atom_count']} / {props['hetero_atom_count']}", "结构规模与极性负担"),
            ("分子量", props["molecular_weight"], "口服药常见 < 500"),
            ("LogP", props["logp"], "脂溶性代理指标"),
            ("TPSA", props["tpsa"], "极性表面积"),
            ("HBD / HBA", f"{props['hbd']} / {props['hba']}", "氢键供体/受体"),
            ("可旋转键", props["rotatable_bonds"], "柔性与构象熵"),
            ("芳香环", props["aromatic_rings"], "平面疏水结构负担"),
            ("QED", props["qed"], "类药性综合指标"),
            ("先导物相似度", props["lead_likeness"], "早期优化友好度"),
            ("Lipinski 违规", props["lipinski_violations"], "口服规则违规数"),
            ("口服倾向", props["oral_likeness"], "内置规则综合"),
            ("溶解性", props["solubility_class"], "规则估计"),
            ("BBB", props["bbb_permeability"], "中枢暴露倾向"),
            ("CYP / hERG / 肝毒性", f"{props['cyp_risk']} / {props['herg_risk']} / {props['hepatotoxicity_risk']}", "安全性早筛"),
            ("合成可行性", props["synthetic_accessibility"], "结构复杂度代理"),
        ]
        for metric, value, note in property_rows:
            self.property_tree.insert("", "end", text=str(metric), values=(str(value), str(note)))

        self.molecule_text.delete("1.0", "end")
        lines = [
            f"ADMET 总体安全分：{result['admet']['overall_safety_score']}",
            "",
            _risk_block("GI 吸收", result["admet"]["gi_absorption"]),
            _risk_block("P-gp 底物可能性", result["admet"]["pgp_substrate_likelihood"]),
            _risk_block("DILI", result["admet"]["dili_risk"]),
            _risk_block("Ames", result["admet"]["ames_risk"]),
            _risk_block("线粒体毒性", result["admet"]["mitochondrial_toxicity_risk"]),
            _risk_block("不确定性", result["admet"]["uncertainty"]),
            f"PAINS 警报：{'；'.join(props['pains_alerts']) if props['pains_alerts'] else '无明显警报'}",
            f"Brenk 警报：{'；'.join(props['brenk_alerts']) if props['brenk_alerts'] else '无明显警报'}",
            "CYP 风险：" + "；".join(
                f"{isoform} {call['level']}({call['score']})"
                for isoform, call in result["admet"]["cyp_isoform_risks"].items()
            ),
        ]
        self.molecule_text.insert("1.0", "\n".join(lines))

        self.molecular_score_text.delete("1.0", "end")
        score_lines = [
            f"总分：{result['score']['total']}",
            "",
            "四类研发子分数",
            f"Discovery：{result['readiness']['discovery']}",
            f"Safety：{result['readiness']['safety']}",
            f"Translatability：{result['readiness']['translatability']}",
            f"Evidence：{result['readiness']['evidence']}",
            "",
            "结构驱动组件",
        ]
        labels = {
            "target_relevance": "靶点相关性",
            "docking_score_norm": "对接分",
            "admet_score": "ADMET",
            "drug_likeness": "类药性",
            "novelty": "新颖性",
            "aging_pathway_coverage": "抗衰通路覆盖",
            "safety_margin": "安全边际",
            "synthesis_feasibility": "合成可行性",
            "clinical_repositioning_potential": "临床重定位潜力",
        }
        for key, label in labels.items():
            score_lines.append(f"{label}：{result['score'][key]}")
        self.molecular_score_text.insert("1.0", "\n".join(score_lines))
        self._draw_readiness_bars(result)

        self.target_tree.delete(*self.target_tree.get_children())
        for prediction in result["predictions"]:
            self.target_tree.insert(
                "",
                "end",
                text=f"{prediction['target_name']} ({prediction['target_id']})",
                values=(
                    _score(prediction["probability"]),
                    prediction["hallmark_name"],
                    prediction["pathway"],
                    prediction["best_ligand"],
                    _score(prediction["similarity"]),
                    "；".join(prediction["pdb_ids"]) if prediction["pdb_ids"] else "-",
                ),
            )
        self.docking_tree.delete(*self.docking_tree.get_children())
        for docking in result["docking"]:
            self.docking_tree.insert(
                "",
                "end",
                text=f"{docking['target_name']} ({docking['target_id']})",
                values=(
                    f"{docking['score_kcal_mol']} kcal/mol",
                    _score(docking["normalized_score"]),
                    docking["backend"],
                    docking["notes"],
                ),
            )

    def _draw_readiness_bars(self, result: Mapping[str, Any]) -> None:
        canvas = self.score_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 520)
        labels = [
            ("总分", result["score"]["total"], "#1f8a70"),
            ("Discovery", result["readiness"]["discovery"], "#2f6f9f"),
            ("Safety", result["readiness"]["safety"], "#1f8a70"),
            ("Translatability", result["readiness"]["translatability"], "#b7791f"),
            ("Evidence", result["readiness"]["evidence"], "#6f5aa7"),
        ]
        left = 132
        top = 24
        bar_width = max(220, width - left - 92)
        for index, (label, value, color) in enumerate(labels):
            y = top + index * 34
            canvas.create_text(18, y + 9, text=label, anchor="w", fill="#30404a", font=("Helvetica", 12, "bold"))
            canvas.create_rectangle(left, y, left + bar_width, y + 18, fill="#e7eeef", outline="")
            canvas.create_rectangle(left, y, left + bar_width * float(value), y + 18, fill=color, outline="")
            canvas.create_text(left + bar_width + 12, y + 9, text=_score(value), anchor="w", fill="#192025", font=("Helvetica", 12, "bold"))

    def run_simulation(self, update_cards: bool = True) -> None:
        try:
            self.status_var.set("运行中")
            self.update_idletasks()
            payload = build_desktop_payload(
                {
                    "condition": self.condition_var.get(),
                    "participants": self.participants_var.get(),
                    "months": self.months_var.get(),
                    "seed": self.seed_var.get(),
                    "top": self.top_var.get(),
                    "weights": {key: variable.get() for key, variable in self.weight_vars.items()},
                }
            )
            self.last_payload = payload
            self._render(payload, update_cards=update_cards)
            self.status_var.set("就绪")
        except Exception as exc:  # pragma: no cover - GUI safety boundary.
            self.status_var.set("错误")
            messagebox.showerror("模拟出错", str(exc))

    def _render(self, payload: Mapping[str, Any], update_cards: bool = True) -> None:
        candidates = payload["candidates"]
        trials = payload["trials"]

        if update_cards:
            self.title_label.configure(text="部分表观遗传重编程研发雷达")
            self._render_reprogramming_metrics(payload.get("reprogramming", []))

        self.candidate_tree.delete(*self.candidate_tree.get_children())
        for candidate in candidates:
            self.candidate_tree.insert(
                "",
                "end",
                text=f"{candidate['rank']}. {candidate['name']}",
                values=(
                    _score(candidate["score"]),
                    _score(candidate["safety"]),
                    candidate["evidence"].replace("转化证据 ", ""),
                    candidate["recommendation"],
                ),
            )

        self._render_reprogramming(payload.get("reprogramming", []))
        self._render_combinations(payload.get("combinations", []))
        self._render_roadmap(
            payload.get("tissue_plans", []),
            payload.get("safety_gates", []),
            payload.get("evidence_gaps", []),
        )
        self._render_database_assets(payload)
        self._render_gene_scores(payload.get("gene_rankings", [])[:20])
        self._render_decision_workbench(payload)
        self._render_program_workbench(payload)
        self._render_diligence(payload)
        self._draw_chart(trials)
        self._render_knowledge_panel(payload["hallmarks"], payload["endpoints"], payload["evidence"])
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", payload["report"])
        self._render_resources(payload["software"], payload["evidence"])

    def _render_reprogramming_metrics(self, rows: list[Mapping[str, Any]]) -> None:
        lead = rows[0] if rows else {}
        all_papers = self.research_library.list_papers(limit=10000)
        factor_hits = 0
        risk_terms: set[str] = set()
        for row in rows:
            related = self.research_library.papers_for_factor(str(row.get("id", "")), limit=200)
            if related:
                factor_hits += 1
            for paper in related:
                risk_terms.update(paper.signals.safety_risks)
        self.metric_labels["首选重编程因子"].configure(
            text=f"{lead.get('name', '-')} {_score(lead.get('score')) if lead else ''}".strip()
        )
        self.metric_labels["本地证据覆盖"].configure(text=f"{factor_hits}/{len(rows)} 个因子")
        self.metric_labels["风险提示"].configure(text=_join_or_dash(sorted(risk_terms))[:42])
        self.metric_labels["文献库规模"].configure(text=f"{len(all_papers)} 篇")

    def _render_resources(
        self,
        software: list[Mapping[str, Any]],
        evidence: list[Mapping[str, Any]],
    ) -> None:
        self.resources_text.delete("1.0", "end")
        self.resources_text.insert("end", "外部数据源状态\n", "section")
        self.resources_text.insert("end", summarize_external_status() + "\n\n")
        self.resources_text.insert("end", "可接入软件与数据库\n", "section")
        for tool in software:
            self.resources_text.insert("end", f"{tool['name']}（{tool['category']}）\n", "title")
            self.resources_text.insert(
                "end",
                f"角色：{tool['role']}\n状态：{tool['integration_status']}\n链接：{tool['url']}\n说明：{tool['notes']}\n\n",
            )
        self.resources_text.insert("end", "文献与资料来源\n", "section")
        for source in evidence:
            self.resources_text.insert("end", f"{source['title']}\n", "title")
            self.resources_text.insert(
                "end",
                f"{source['source']} · {source['year']} · 质量分 {_score(source['quality'])}\n{source['url']}\n\n",
            )
        self.resources_text.tag_configure("title", font=("Helvetica", 12, "bold"), foreground="#192025")
        self.resources_text.tag_configure("section", font=("Helvetica", 13, "bold"), foreground="#1f8a70")

    def _render_reprogramming(self, rows: list[Mapping[str, Any]]) -> None:
        self.reprogramming_tree.delete(*self.reprogramming_tree.get_children())
        for row in rows:
            self.reprogramming_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                text=f"{row['rank']}. {row['name']}",
                values=(
                    _score(row["score"]),
                    _score(row["safety"]),
                    row.get("literature_count", 0),
                    "动态" if row.get("evidence_basis") == "literature_adjusted" else "基础",
                    row["tissues"],
                    row["recommendation"],
                ),
            )
        self._render_reprogramming_detail(rows[0] if rows else None)

    def on_reprogramming_select(self, _event: object) -> None:
        payload = getattr(self, "last_payload", None)
        if not payload:
            return
        selected = self.reprogramming_tree.selection()
        if not selected:
            return
        selected_id = selected[0]
        rows = payload.get("reprogramming", [])
        selected_row = next((row for row in rows if str(row.get("id")) == selected_id), None)
        self._render_reprogramming_detail(selected_row)

    def _render_reprogramming_detail(self, row: Mapping[str, Any] | None) -> None:
        self.reprogramming_detail_text.delete("1.0", "end")
        self.reprogramming_score_text.delete("1.0", "end")
        if not row:
            self.reprogramming_detail_text.insert("1.0", "暂无重编程因子数据。")
            return
        related_papers = self.research_library.papers_for_factor(str(row["id"]), limit=8)
        evidence_scores = [paper.signals.evidence_score for paper in related_papers]
        average_evidence = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0
        risk_terms = sorted({risk for paper in related_papers for risk in paper.signals.safety_risks})
        attribution_rows = evidence_attribution_rows(related_papers)
        paper_lines = [
            f"- {paper.year or '-'} · {paper.title[:92]}（证据分 {_score(paper.signals.evidence_score)}，PMID {paper.pmid}）"
            for paper in related_papers[:5]
        ]
        attribution_lines = [
            f"- PMID {item['pmid']}｜{item['evidence_score']:.2f}｜{str(item['title'])[:70]}：{item['contribution']}"
            for item in attribution_rows[:5]
        ]

        self.reprogramming_detail_text.insert(
            "1.0",
            "\n".join(
                [
                    f"名称：{row['name']}",
                    f"类型：{row['modality']}",
                    f"适合组织：{row['tissues']}",
                    f"机制：{row['mechanism']}",
                    f"建议：{row['recommendation']}",
                    "",
                    f"备注：{row['notes']}",
                    "",
                    f"评分来源：{'文献动态调整' if row.get('evidence_basis') == 'literature_adjusted' else '基础评分表'}",
                    f"动态安全警告：{_join_or_dash(row.get('safety_warnings', []))}",
                    f"本地相关文献：{len(related_papers)} 篇；平均证据分：{_score(average_evidence)}",
                    f"风险词汇总：{_join_or_dash(risk_terms)}",
                    *(["相关文献：", *paper_lines] if paper_lines else ["相关文献：暂无；可在文献雷达搜索该因子。"]),
                    "",
                    *(["证据归因：", *attribution_lines] if attribution_lines else ["证据归因：暂无本地文献可归因。"]),
                    "",
                    "解释边界：这是基于公开资料的研发优先级评分，不代表真实疗效或临床安全性。",
                ]
            ),
        )

        labels = {
            "rejuvenation_potential": "年轻化潜力",
            "identity_preservation": "身份保留",
            "safety": "安全性",
            "delivery_feasibility": "递送可行性",
            "tissue_specificity": "组织特异性",
            "evidence_strength": "证据强度",
            "druggability": "可药物化",
            "novelty_ip": "新颖性/IP空间",
        }
        components = row.get("components", {})
        experiment = design_validation_experiment(_row_to_score(row))
        lines = [
            f"总优先级：{_score(row['score'])}",
            f"安全分：{_score(row['safety'])}",
            f"评分来源：{'文献动态调整' if row.get('evidence_basis') == 'literature_adjusted' else '基础评分表'}",
            f"相关文献数：{row.get('literature_count', 0)}",
            "",
            "评分过程",
            *[f"- {note}" for note in row.get("process_notes", [])],
            "",
            "下一步验证",
            *[f"- {step}" for step in row.get("next_steps", [])],
            "",
            "实验设计草案",
            f"- 目标：{experiment['objective']}",
            f"- 模型：{experiment['model']}",
            f"- 分组：{_join_or_dash(experiment['arms'])}",
            f"- 时间点：{_join_or_dash(experiment['timepoints'])}",
            f"- 有效性 readout：{_join_or_dash(experiment['efficacy_readouts'])}",
            f"- 安全 readout：{_join_or_dash(experiment['safety_readouts'])}",
            f"- 递送说明：{experiment['delivery_note']}",
            f"- Go/No-Go：{experiment['decision_gate']}",
            "",
            "组件分",
        ]
        for key, label in labels.items():
            if key in components:
                lines.append(f"{label}：{_score(components[key])}")
        self.reprogramming_score_text.insert("1.0", "\n".join(lines))

    def _render_combinations(self, rows: list[Mapping[str, Any]]) -> None:
        if not hasattr(self, "combination_tree"):
            return
        self.combination_tree.delete(*self.combination_tree.get_children())
        for row in rows:
            self.combination_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                text=f"{row['rank']}. {row['name']}",
                values=(
                    _score(row["score"]),
                    _score(row["safety"]),
                    row["risk_profile"],
                    row["target_tissue"],
                    row["factors"],
                ),
            )
        self._render_combination_detail(rows[0] if rows else None)

    def on_combination_select(self, _event: object) -> None:
        payload = getattr(self, "last_payload", None)
        if not payload:
            return
        selected = self.combination_tree.selection()
        if not selected:
            return
        selected_id = selected[0]
        rows = payload.get("combinations", [])
        selected_row = next((row for row in rows if str(row.get("id")) == selected_id), None)
        self._render_combination_detail(selected_row)

    def _render_combination_detail(self, row: Mapping[str, Any] | None) -> None:
        self.combination_detail_text.delete("1.0", "end")
        self.combination_plan_text.delete("1.0", "end")
        if not row:
            self.combination_detail_text.insert("1.0", "暂无组合策略。")
            return
        rationale = [f"- {item}" for item in row.get("rationale", [])]
        excluded = row.get("excluded_factors", [])
        self.combination_detail_text.insert(
            "1.0",
            "\n".join(
                [
                    f"名称：{row['name']}",
                    f"因子：{row['factors']}",
                    f"目标组织：{row['target_tissue']}",
                    f"风险档：{row['risk_profile']}",
                    f"优先级：{_score(row['score'])}",
                    f"安全下限：{_score(row['safety'])}",
                    "",
                    "策略：",
                    str(row["strategy"]),
                    "",
                    "为什么这样组合：",
                    *rationale,
                    "",
                    "排除/降级因子：",
                    _join_or_dash(excluded),
                ]
            ),
        )
        plan = [f"- {item}" for item in row.get("validation_plan", [])]
        self.combination_plan_text.insert(
            "1.0",
            "\n".join(
                [
                    "验证路径",
                    *plan,
                    "",
                    "Go/No-Go 规则",
                    "- 只要出现细胞身份丢失、多能性标志持续上升、异常增殖或 DNA 损伤上升，即停止推进。",
                    "- 只有年轻化 readout、功能 readout 和安全 readout 同时过线，才进入更复杂组织模型。",
                    "",
                    "边界",
                    "这是研发路线设计，不是实验操作协议，也不是临床方案。",
                ]
            ),
        )

    def _render_roadmap(
        self,
        tissue_plans: list[Mapping[str, Any]],
        safety_gates: list[Mapping[str, Any]],
        evidence_gaps: list[Mapping[str, Any]],
    ) -> None:
        if not hasattr(self, "tissue_plan_tree"):
            return
        self.tissue_plan_tree.delete(*self.tissue_plan_tree.get_children())
        for row in tissue_plans:
            self.tissue_plan_tree.insert(
                "",
                "end",
                iid=str(row["tissue"]),
                text=f"{row['rank']}. {row['label']}",
                values=(
                    _score(row["priority"]),
                    row["lead_factors"],
                    row["lead_combination"],
                    row["model_system"],
                ),
            )
        self._render_tissue_plan_detail(tissue_plans[0] if tissue_plans else None)
        self._render_safety_gates(safety_gates)
        self._render_evidence_gaps(evidence_gaps)

    def on_tissue_plan_select(self, _event: object) -> None:
        payload = getattr(self, "last_payload", None)
        if not payload:
            return
        selected = self.tissue_plan_tree.selection()
        if not selected:
            return
        selected_tissue = selected[0]
        row = next((item for item in payload.get("tissue_plans", []) if str(item.get("tissue")) == selected_tissue), None)
        self._render_tissue_plan_detail(row)

    def _render_tissue_plan_detail(self, row: Mapping[str, Any] | None) -> None:
        if row is None:
            return
        lines = [
            f"组织路线：{row['label']}",
            f"优先级：{_score(row['priority'])}",
            f"首选因子：{row['lead_factors']}",
            f"首选组合：{row['lead_combination']}",
            f"模型系统：{row['model_system']}",
            f"递送重点：{row['delivery_focus']}",
            "",
            "主要 readout",
            *[f"- {item}" for item in row.get("primary_readouts", [])],
            "",
            "安全重点",
            *[f"- {item}" for item in row.get("safety_focus", [])],
            "",
            "下一步",
            *[f"- {item}" for item in row.get("next_actions", [])],
        ]
        self.safety_gate_text.delete("1.0", "end")
        self.safety_gate_text.insert("1.0", "\n".join(lines))

    def _render_safety_gates(self, rows: list[Mapping[str, Any]]) -> None:
        if not rows:
            return
        lines = ["安全闸门总览"]
        for row in rows[:8]:
            lines.extend(
                [
                    "",
                    f"{row['gate']}｜{row['name']}｜安全分 {_score(row['safety'])}",
                    "必须通过：" + _join_or_dash(row.get("must_pass", [])),
                    "停止触发：" + _join_or_dash(row.get("stop_triggers", [])),
                    f"复核节奏：{row['cadence']}",
                ]
            )
        current = self.safety_gate_text.get("1.0", "end").strip()
        if current:
            self.safety_gate_text.insert("end", "\n\n" + "\n".join(lines))
        else:
            self.safety_gate_text.insert("1.0", "\n".join(lines))

    def _render_evidence_gaps(self, rows: list[Mapping[str, Any]]) -> None:
        self.evidence_gap_text.delete("1.0", "end")
        if not rows:
            self.evidence_gap_text.insert("1.0", "暂无证据缺口。")
            return
        lines = ["证据缺口与 AI 文献任务"]
        for row in rows[:10]:
            lines.extend(
                [
                    "",
                    f"{row['name']}｜紧急度 {_score(row['urgency'])}",
                    "缺口：" + _join_or_dash(row.get("gaps", [])),
                    f"检索式：{row['query']}",
                    f"AI 任务：{row['ai_task']}",
                ]
            )
        self.evidence_gap_text.insert("1.0", "\n".join(lines))

    def _render_database_assets(self, payload: Mapping[str, Any]) -> None:
        if not hasattr(self, "asset_summary_text"):
            return
        summary = payload.get("asset_summary", {})
        counts = summary.get("counts", {})
        targets = summary.get("targets", {})
        missing = summary.get("missing", {})
        completion = summary.get("completion", {})
        lines = [
            "三项数据库目标",
            f"- 论文：{counts.get('papers', 0)}/{targets.get('papers', 100)}，完成度 {_percent(completion.get('papers', 0.0))}，缺口 {missing.get('papers', 0)}",
            f"- 候选基因：{counts.get('candidate_genes', 0)}/{targets.get('candidate_genes', 100)}，完成度 {_percent(completion.get('candidate_genes', 0.0))}，缺口 {missing.get('candidate_genes', 0)}",
            f"- 公司/课题组：{counts.get('organizations', 0)}/{targets.get('organizations', 50)}，完成度 {_percent(completion.get('organizations', 0.0))}，缺口 {missing.get('organizations', 0)}",
            "",
            "状态：" + ("已达到第一版数据库目标" if summary.get("database_ready") else "还需要继续补论文库"),
        ]
        self.asset_summary_text.delete("1.0", "end")
        self.asset_summary_text.insert("1.0", "\n".join(lines))

        self.asset_gene_tree.delete(*self.asset_gene_tree.get_children())
        for row in payload.get("gene_rankings", [])[:40]:
            self.asset_gene_tree.insert(
                "",
                "end",
                text=row["symbol"],
                values=(
                    _score(row["score"]),
                    row["risk_band"],
                    row["tissues"],
                    row["recommendation"],
                ),
            )

        self.asset_org_tree.delete(*self.asset_org_tree.get_children())
        for row in payload.get("organizations", []):
            self.asset_org_tree.insert(
                "",
                "end",
                text=row["name"],
                values=(row["type"], row["country"], row["focus"], row["tags"]),
            )

    def run_gene_analysis(self) -> None:
        try:
            local_papers = self.research_library.list_papers(limit=100000)
            score = score_gene_query_with_literature(self.gene_query_var.get(), self.candidate_genes, local_papers)
            top_rows = getattr(self, "last_payload", {}).get("gene_rankings", [])
            rows = gene_score_report_rows([score])
            rows.extend(row for row in top_rows if row.get("symbol") != score.symbol)
            self._render_gene_scores(rows[:20])
            self.status_var.set(f"已评分基因 {score.symbol}")
        except Exception as exc:
            self.status_var.set("基因评分失败")
            messagebox.showerror("基因评分出错", str(exc))

    def _render_gene_scores(self, rows: list[Mapping[str, Any]]) -> None:
        if not hasattr(self, "gene_score_tree"):
            return
        self.gene_score_tree.delete(*self.gene_score_tree.get_children())
        for row in rows:
            self.gene_score_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                text=row["symbol"],
                values=(
                    _score(row["score"]),
                    _score(row["rejuvenation_potential"]),
                    _score(row["risk"]),
                    row["risk_band"],
                    row["tissues"],
                ),
            )
        self._render_gene_detail(rows[0] if rows else None)

    def on_gene_select(self, _event: object) -> None:
        payload = getattr(self, "last_payload", None)
        selected = self.gene_score_tree.selection()
        if not selected:
            return
        selected_id = selected[0]
        rows = []
        if payload:
            rows = payload.get("gene_rankings", [])
        current = next((row for row in rows if str(row.get("id")) == selected_id), None)
        if current is None:
            current = next(
                (
                    {
                        "id": selected_id,
                        "symbol": self.gene_score_tree.item(selected_id).get("text", selected_id),
                        "score": 0.0,
                        "rejuvenation_potential": 0.0,
                        "risk": 0.0,
                        "risk_band": "-",
                        "recommendation": "-",
                        "mechanism": "-",
                        "tissues": "-",
                        "evidence_query": "-",
                        "warnings": [],
                        "components": {},
                    }
                    for _ in (0,)
                ),
                None,
            )
        self._render_gene_detail(current)

    def _render_gene_detail(self, row: Mapping[str, Any] | None) -> None:
        self.gene_detail_text.delete("1.0", "end")
        if not row:
            self.gene_detail_text.insert("1.0", "输入基因 Symbol 后点击评分。")
            return
        components = row.get("components", {})
        component_lines = [
            f"- {key}：{_score(value)}"
            for key, value in components.items()
        ]
        lines = [
            f"基因：{row['symbol']}",
            f"命中本地库：{'是' if row.get('matched', True) else '否'}",
            f"总分：{_score(row['score'])}",
            f"年轻化潜力：{_score(row['rejuvenation_potential'])}",
            f"风险分：{_score(row['risk'])}",
            f"风险档：{row['risk_band']}",
            f"证据依据：{'文献动态调整' if row.get('evidence_basis') == 'literature_adjusted' else row.get('evidence_basis', '-')}",
            f"本地命中文献：{row.get('literature_count', 0)} 篇",
            f"溯源分：{_score(row.get('provenance_score', 0.0))}",
            f"建议：{row['recommendation']}",
            "",
            f"机制：{row['mechanism']}",
            f"组织：{row['tissues']}",
            f"PMID：{_join_or_dash(row.get('evidence_pmids', []))}",
            "",
            "警告：",
            *([f"- {warning}" for warning in row.get("warnings", [])] or ["- 暂无额外警告"]),
            "",
            "审计备注：",
            *([f"- {note}" for note in row.get("audit_notes", [])] or ["- 暂无"]),
            "",
            "下一步文献任务：",
            str(row["evidence_query"]),
            "",
            "组件分：",
            *component_lines,
        ]
        self.gene_detail_text.insert("1.0", "\n".join(lines))

    def _render_decision_workbench(self, payload: Mapping[str, Any]) -> None:
        if not hasattr(self, "portfolio_tree"):
            return
        self.portfolio_tree.delete(*self.portfolio_tree.get_children())
        for row in payload.get("gene_portfolio", [])[:60]:
            self.portfolio_tree.insert(
                "",
                "end",
                text=row["symbol"],
                values=(
                    row["bucket"],
                    _score(row["score"]),
                    _score(row["safety"]),
                    _score(row["provenance"]),
                    row["literature_count"],
                    row["action"],
                ),
            )

        method = payload.get("scoring_method", {})
        stress_lines = [
            f"方法版本：{method.get('method_version', '-')}",
            f"公式：{method.get('formula', '-')}",
            "",
            "压力测试 Top",
        ]
        for row in payload.get("stress_tests", [])[:12]:
            scenario_bits = [
                f"{item['scenario']}={float(item['score']):.2f}"
                for item in row.get("scenario_scores", [])
            ]
            stress_lines.extend(
                [
                    "",
                    f"{row['symbol']}｜均值 {_score(row['average_score'])}｜跨度 {_score(row['spread'])}｜{row['stability']}｜{row['decision']}",
                    "场景：" + "；".join(scenario_bits),
                ]
            )
        self.stress_text.delete("1.0", "end")
        self.stress_text.insert("1.0", "\n".join(stress_lines))

        pack_lines = []
        for pack in payload.get("gene_evidence_packs", [])[:8]:
            top_papers = [
                f"- PMID {paper['pmid']}｜{paper['year']}｜{float(paper['evidence_score']):.2f}｜{str(paper['title'])[:72]}：{paper['contribution']}"
                for paper in pack.get("top_papers", [])[:3]
            ]
            pack_lines.extend(
                [
                    f"{pack['symbol']}｜论文 {pack['paper_count']}｜平均证据 {_score(pack['average_evidence_score'])}",
                    str(pack["summary"]),
                    "readout：" + _join_or_dash(pack.get("readouts", [])),
                    "组织：" + _join_or_dash(pack.get("tissues", [])),
                    "缺口：" + _join_or_dash(pack.get("gaps", [])),
                    *top_papers,
                    "",
                ]
            )
        self.evidence_pack_text.delete("1.0", "end")
        self.evidence_pack_text.insert("1.0", "\n".join(pack_lines).strip() or "暂无证据包。")

    def _render_program_workbench(self, payload: Mapping[str, Any]) -> None:
        if not hasattr(self, "milestone_tree"):
            return
        self.milestone_tree.delete(*self.milestone_tree.get_children())
        for row in payload.get("program_milestones", []):
            self.milestone_tree.insert(
                "",
                "end",
                text=row["phase"],
                values=(row["objective"], row["deliverable"], row["exit_gate"]),
            )

        self.backlog_tree.delete(*self.backlog_tree.get_children())
        for row in payload.get("experiment_backlog", []):
            self.backlog_tree.insert(
                "",
                "end",
                text=row["task_id"],
                values=(
                    row["lane"],
                    row["priority"],
                    row["target"],
                    row["deliverable"],
                    row["status"],
                ),
            )

        partner_lines = []
        for row in payload.get("partner_shortlist", [])[:10]:
            partner_lines.extend(
                [
                    f"{row['name']}｜{row['type']}｜{row['country']} {row['city']}｜匹配 {_score(row['fit_score'])}",
                    f"理由：{row['fit_reason']}",
                    f"切入：{row['outreach_angle']}",
                    f"核验：{row['caution']}",
                    f"URL：{row['url']}",
                    "",
                ]
            )
        self.partner_text.delete("1.0", "end")
        self.partner_text.insert("1.0", "\n".join(partner_lines).strip() or "暂无合作方短名单。")

        checklist_lines = []
        for row in payload.get("data_room_checklist", []):
            checklist_lines.extend(
                [
                    f"{row['item']}｜{row['status']}",
                    f"证据：{row['evidence']}",
                    f"下一步：{row['next_action']}",
                    "",
                ]
            )
        self.data_room_text.delete("1.0", "end")
        self.data_room_text.insert("1.0", "\n".join(checklist_lines).strip() or "暂无 data room 清单。")

    def _render_diligence(self, payload: Mapping[str, Any]) -> None:
        if not hasattr(self, "audit_text"):
            return
        audit = payload.get("asset_audit", {})
        paper = audit.get("paper", {})
        gene = audit.get("gene", {})
        organization = audit.get("organization", {})
        red_flags = [f"- {item}" for item in audit.get("red_flags", [])]
        next_steps = [f"- {item}" for item in audit.get("next_steps", [])]
        self.audit_text.delete("1.0", "end")
        self.audit_text.insert(
            "1.0",
            "\n".join(
                [
                    f"可信度分：{_score(audit.get('credibility_score', 0.0))}",
                    f"可信度等级：{audit.get('credibility_grade', '-')}",
                    "",
                    "论文库",
                    f"- 记录数：{paper.get('records', 0)}",
                    f"- 唯一 PMID：{paper.get('unique_pmids', 0)}",
                    f"- DOI：{paper.get('doi_count', 0)}",
                    f"- 高信号论文：{paper.get('high_signal_count', 0)}",
                    "",
                    "候选基因库",
                    f"- 记录数：{gene.get('records', 0)}",
                    f"- 检索式覆盖：{gene.get('query_coverage', 0)}",
                    f"- PMID 命中基因：{gene.get('literature_backed', 0)}",
                    f"- 高风险已标记：{gene.get('high_risk_flagged', 0)}",
                    "",
                    "公司/课题组库",
                    f"- 记录数：{organization.get('records', 0)}",
                    f"- URL 覆盖：{organization.get('url_coverage', 0)}",
                    f"- 中国机构：{organization.get('china_records', 0)}",
                    "",
                    "红旗",
                    *red_flags,
                    "",
                    "下一步",
                    *next_steps,
                ]
            ),
        )

        self.diligence_text.delete("1.0", "end")
        diligence_lines = []
        for row in payload.get("diligence_rows", []):
            diligence_lines.extend(
                [
                    row["question"],
                    row["answer"],
                    f"证据：{row['evidence']}",
                    "",
                ]
            )
        self.diligence_text.insert("1.0", "\n".join(diligence_lines).strip() or "暂无尽调问答。")

        self.provenance_tree.delete(*self.provenance_tree.get_children())
        rows = sorted(
            payload.get("gene_rankings", []),
            key=lambda row: (-float(row.get("provenance_score", 0.0)), -float(row.get("score", 0.0))),
        )
        for row in rows[:20]:
            self.provenance_tree.insert(
                "",
                "end",
                text=row["symbol"],
                values=(
                    _score(row["score"]),
                    _score(row.get("provenance_score", 0.0)),
                    row.get("literature_count", 0),
                    "动态" if row.get("evidence_basis") == "literature_adjusted" else "种子",
                    row["risk_band"],
                    row["recommendation"],
                ),
            )

    def _draw_chart(self, trials: list[Mapping[str, Any]]) -> None:
        self.chart.delete("all")
        width = max(self.chart.winfo_width(), 520)
        height = max(self.chart.winfo_height(), 260)
        left, top, right, bottom = 54, 26, 26, 48
        plot_w = width - left - right
        plot_h = height - top - bottom
        self.chart.create_rectangle(left, top, left + plot_w, top + plot_h, outline="#d8e1e6", fill="#f6f8f7")
        if not trials:
            return
        max_value = max(0.1, *(abs(float(trial["responder_lift"])) for trial in trials))
        gap = 18
        bar_w = max(34, (plot_w - gap * (len(trials) - 1)) / len(trials))
        for index, trial in enumerate(trials):
            value = float(trial["responder_lift"])
            bar_h = max(2, abs(value) / max_value * (plot_h - 24))
            x0 = left + index * (bar_w + gap)
            y0 = top + plot_h - bar_h
            x1 = x0 + bar_w
            y1 = top + plot_h
            color = "#1f8a70" if value >= 0 else "#b84e4e"
            self.chart.create_rectangle(x0, y0, x1, y1, fill=color, outline=color)
            self.chart.create_text((x0 + x1) / 2, y0 - 10, text=_percent(value), fill="#192025", font=("Helvetica", 10, "bold"))
            self.chart.create_text((x0 + x1) / 2, y1 + 18, text=str(trial["name"])[:22], fill="#53636f", font=("Helvetica", 9), width=bar_w + 16)

    def _render_knowledge_panel(
        self,
        hallmarks: list[Mapping[str, Any]],
        endpoints: list[Mapping[str, Any]],
        evidence: list[Mapping[str, Any]],
    ) -> None:
        self.hallmark_text.delete("1.0", "end")
        self.hallmark_text.insert("end", "推荐试验终点\n", "section")
        for endpoint in endpoints[:5]:
            self.hallmark_text.insert(
                "end",
                f"{endpoint['name']}  {_score(endpoint['importance'])}\n",
                "title",
            )
            self.hallmark_text.insert("end", f"{endpoint['category']} · {endpoint['description']}\n\n")
        self.hallmark_text.insert("end", "证据来源\n", "section")
        for source in evidence[:5]:
            self.hallmark_text.insert("end", f"{source['source']}（{source['year']}）  {_score(source['quality'])}\n", "title")
            self.hallmark_text.insert("end", f"{source['title']}\n\n")
        self.hallmark_text.insert("end", "12 项衰老标志\n", "section")
        for hallmark in hallmarks:
            self.hallmark_text.insert("end", f"{hallmark['name']}  {_score(hallmark['weight'])}\n", "title")
            self.hallmark_text.insert("end", f"{hallmark['id']} · {hallmark['description']}\n\n")
        self.hallmark_text.tag_configure("title", font=("Helvetica", 12, "bold"), foreground="#192025")
        self.hallmark_text.tag_configure("section", font=("Helvetica", 13, "bold"), foreground="#1f8a70")


def build_desktop_payload(options: Mapping[str, Any]) -> dict[str, Any]:
    condition = str(options.get("condition") or "衰弱预防")
    participants = _bounded_int(options.get("participants", 180), 20, 2000)
    months = _bounded_int(options.get("months", 24), 3, 120)
    seed = _bounded_int(options.get("seed", 42), 0, 999999)
    top = _bounded_int(options.get("top", 5), 1, 20)
    weights = _component_weights(options.get("weights"))

    hallmarks = load_hallmarks(ROOT / "data" / "aging_hallmarks.csv")
    candidates = load_candidate_drugs(ROOT / "data" / "candidate_drugs.csv")
    evidence_sources = load_evidence_sources(ROOT / "data" / "evidence_sources.csv")
    endpoints = load_trial_endpoints(ROOT / "data" / "trial_endpoints.csv")
    software_tools = load_software_tools(ROOT / "data" / "software_tools.csv")
    candidate_genes = load_candidate_genes()
    organizations = load_research_organizations()
    ranked = rank_candidates(candidates, hallmarks, component_weights=weights)[:top]
    factors = load_reprogramming_factors()
    with ResearchLibrary(DEFAULT_RESEARCH_DB) as research_library:
        papers_by_factor = {
            factor.factor_id: research_library.papers_for_factor(factor.factor_id, limit=200)
            for factor in factors
        }
        local_papers = research_library.list_papers(limit=100000)
        paper_count = len(local_papers)
    reprogramming_scores = rank_reprogramming_factors_with_literature(factors, papers_by_factor)
    reprogramming_rows = reprogramming_report_rows(reprogramming_scores)
    target_tissue = _target_tissue_from_condition(condition)
    reprogramming_combinations = design_reprogramming_combinations(
        reprogramming_scores,
        target_tissue=target_tissue,
        risk_profile="conservative",
    )
    combination_rows = combination_report_rows(reprogramming_combinations)
    tissue_plan_rows = tissue_plan_report_rows(
        design_tissue_reprogramming_plans(
            reprogramming_scores,
            reprogramming_combinations,
            focus_tissues=(target_tissue, "fibroblast", "retina", "muscle", "immune", "neuron"),
        )
    )
    tissue_plan_rows = _prioritize_target_tissue(tissue_plan_rows, target_tissue)
    gate_rows = safety_gate_rows([*reprogramming_scores[:8], *reprogramming_combinations])
    gap_rows = evidence_gap_rows(reprogramming_scores)
    gene_scores = rank_candidate_genes_with_literature(candidate_genes, local_papers)
    gene_rows = gene_score_report_rows(gene_scores)
    gene_portfolio = build_gene_portfolio(gene_scores)
    stress_rows = stress_test_report_rows(candidate_genes, local_papers, limit=30)
    evidence_packs = build_gene_evidence_packs(candidate_genes, local_papers, limit=20)
    method_card = scoring_method_card()
    organization_rows = organization_report_rows(organizations)
    summary = asset_summary(paper_count=paper_count, genes=candidate_genes, organizations=organizations)
    audit = audit_asset_quality(papers=local_papers, genes=candidate_genes, organizations=organizations)
    diligence_rows = investor_diligence_rows(audit=audit, gene_scores=gene_scores)
    program_milestones = build_program_milestones(
        gene_portfolio=gene_portfolio,
        evidence_packs=evidence_packs,
        audit=audit,
        tissue_plans=tissue_plan_rows,
        safety_gates=gate_rows,
    )
    experiment_backlog = build_experiment_backlog(
        gene_portfolio=gene_portfolio,
        evidence_packs=evidence_packs,
        tissue_plans=tissue_plan_rows,
        safety_gates=gate_rows,
    )
    partner_shortlist = build_partner_shortlist(organizations, target_tissue=target_tissue)
    data_room_checklist = build_data_room_checklist(
        summary=summary,
        audit=audit,
        method_card=method_card,
        gene_portfolio=gene_portfolio,
        evidence_packs=evidence_packs,
        stress_rows=stress_rows,
    )
    hallmark_names = {hallmark.hallmark_id: hallmark.name for hallmark in hallmarks}
    source_index = {source.source_id: source for source in evidence_sources}
    trials = [
        run_virtual_trial(
            cohort_size=participants,
            years=months / 12,
            treatment_effect=_score_to_treatment_effect(candidate.total_score),
            seed=seed + index,
        )
        for index, candidate in enumerate(ranked)
    ]
    candidate_rows = [
        _candidate_payload(
            candidate,
            rank=index,
            hallmark_names=hallmark_names,
            source_index=source_index,
        )
        for index, candidate in enumerate(ranked, start=1)
    ]
    trial_rows = [
        _trial_payload(condition, ranked[index].name, trial, months)
        for index, trial in enumerate(trials)
    ]
    report = render_markdown_report(
        ranked_candidates=candidate_rows,
        trial_summaries=trial_rows,
        title=f"Asclepius 模拟报告：{condition}",
        language="zh",
    )
    report += _render_research_appendix(
        candidate_rows,
        endpoints,
        evidence_sources,
        software_tools,
        reprogramming_rows,
        combination_rows,
        tissue_plan_rows,
        gate_rows,
        gap_rows,
        summary,
        gene_rows,
        organization_rows,
        audit,
        diligence_rows,
        gene_portfolio,
        stress_rows,
        evidence_packs,
        method_card,
        program_milestones,
        experiment_backlog,
        partner_shortlist,
        data_room_checklist,
    )
    diligence_report = _render_investor_diligence(
        summary=summary,
        audit=audit,
        diligence_rows=diligence_rows,
        gene_rows=gene_rows,
        gene_portfolio=gene_portfolio,
        stress_rows=stress_rows,
        evidence_packs=evidence_packs,
        organization_rows=organization_rows,
        reprogramming_rows=reprogramming_rows,
        combination_rows=combination_rows,
        program_milestones=program_milestones,
        experiment_backlog=experiment_backlog,
        partner_shortlist=partner_shortlist,
        data_room_checklist=data_room_checklist,
    )
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(report, encoding="utf-8")
    DEFAULT_DILIGENCE_OUTPUT.write_text(diligence_report, encoding="utf-8")
    return {
        "condition": condition,
        "participants": participants,
        "months": months,
        "seed": seed,
        "weights": weights,
        "hallmarks": [
            {
                "id": hallmark.hallmark_id,
                "name": hallmark.name,
                "weight": hallmark.weight,
                "description": hallmark.description,
            }
            for hallmark in hallmarks
        ],
        "endpoints": [
            {
                "id": endpoint.endpoint_id,
                "name": endpoint.name,
                "category": endpoint.category,
                "importance": endpoint.importance,
                "description": endpoint.description,
            }
            for endpoint in sorted(endpoints, key=lambda item: -item.importance)
        ],
        "evidence": [
            {
                "id": source.source_id,
                "title": source.title,
                "type": source.evidence_type,
                "source": source.source,
                "year": source.year,
                "url": source.url,
                "quality": source.quality,
                "notes": source.notes,
            }
            for source in sorted(evidence_sources, key=lambda item: -item.quality)
        ],
        "reprogramming": reprogramming_rows,
        "combinations": combination_rows,
        "tissue_plans": tissue_plan_rows,
        "safety_gates": gate_rows,
        "evidence_gaps": gap_rows,
        "asset_summary": summary,
        "asset_audit": audit,
        "diligence_rows": diligence_rows,
        "gene_rankings": gene_rows,
        "gene_portfolio": gene_portfolio,
        "stress_tests": stress_rows,
        "gene_evidence_packs": evidence_packs,
        "scoring_method": method_card,
        "program_milestones": program_milestones,
        "experiment_backlog": experiment_backlog,
        "partner_shortlist": partner_shortlist,
        "data_room_checklist": data_room_checklist,
        "organizations": organization_rows,
        "software": [
            {
                "id": tool.tool_id,
                "name": tool.name,
                "category": tool.category,
                "role": tool.role,
                "url": tool.url,
                "integration_status": tool.integration_status,
                "notes": tool.notes,
            }
            for tool in software_tools
        ],
        "candidates": candidate_rows,
        "trials": trial_rows,
        "report": report,
        "report_path": str(DEFAULT_OUTPUT),
        "diligence_report": diligence_report,
        "diligence_report_path": str(DEFAULT_DILIGENCE_OUTPUT),
    }


def main() -> int:
    app = AsclepiusDesktop()
    app.mainloop()
    return 0


def _component_weights(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return dict(DEFAULT_COMPONENT_WEIGHTS)
    weights = dict(DEFAULT_COMPONENT_WEIGHTS)
    for key in weights:
        weights[key] = max(0.0, float(value.get(key, weights[key])))
    if sum(weights.values()) <= 0:
        raise ValueError("至少需要一个评分权重大于 0")
    return weights


def _bounded_int(value: Any, lower: int, upper: int) -> int:
    number = int(value)
    if number < lower or number > upper:
        raise ValueError(f"数值必须在 {lower} 到 {upper} 之间")
    return number


def _candidate_payload(
    candidate: CandidateScore,
    *,
    rank: int,
    hallmark_names: Mapping[str, str] | None = None,
    source_index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    safety = candidate.components.get("safety", 0.0)
    evidence = candidate.components.get("translational_evidence", 0.0)
    hallmark_names = hallmark_names or {}
    source_index = source_index or {}
    source_titles = [
        source_index[source_id].title
        for source_id in getattr(candidate, "evidence_sources", ())
        if source_id in source_index
    ]
    return {
        "id": candidate.candidate_id,
        "rank": rank,
        "name": candidate.name,
        "mechanism": "、".join(
            hallmark_names.get(hallmark_id, hallmark_id)
            for hallmark_id in candidate.target_hallmarks
        ),
        "target_hallmarks": list(candidate.target_hallmarks),
        "score": candidate.total_score,
        "safety": safety,
        "evidence": f"转化证据 {evidence:.2f}",
        "recommendation": _localized_recommendation(rank, candidate.total_score, safety),
        "components": candidate.components,
        "sources": source_titles,
    }


def _trial_payload(
    condition: str,
    candidate_name: str,
    result: VirtualTrialResult,
    months: int,
) -> dict[str, Any]:
    responder_lift = result.contrasts["responder_rate_difference"]
    frailty_delta = result.contrasts["mean_frailty_index_change_difference"]
    bioage_delta = result.contrasts["mean_biological_age_delta_change_difference"]
    return {
        "name": candidate_name,
        "phase": "虚拟 IIa",
        "population": condition,
        "duration": f"{months} months",
        "primary_endpoint": "衰弱指数 + 生物年龄偏移",
        "outcome": (
            f"响应率提升 {responder_lift:+.1%}；"
            f"衰弱变化 {frailty_delta:+.3f}；"
            f"生物年龄变化 {bioage_delta:+.3f}"
        ),
        "responder_lift": responder_lift,
        "frailty_delta": frailty_delta,
        "bioage_delta": bioage_delta,
    }


def _score(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}"


def _percent(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


def _join_or_dash(values: Iterable[Any]) -> str:
    items = [str(value) for value in values if str(value)]
    return "；".join(items) if items else "-"


def _target_tissue_from_condition(condition: str) -> str:
    text = condition.lower()
    tissue_hints = (
        ("视网膜", "retina"),
        ("眼", "retina"),
        ("神经", "neuron"),
        ("脑", "neuron"),
        ("肌", "muscle"),
        ("免疫", "immune"),
        ("血液", "hematopoietic"),
        ("肝", "liver"),
        ("皮肤", "fibroblast"),
        ("成纤维", "fibroblast"),
    )
    for needle, tissue in tissue_hints:
        if needle in text:
            return tissue
    return "fibroblast"


def _prioritize_target_tissue(
    rows: list[dict[str, object]],
    target_tissue: str,
) -> list[dict[str, object]]:
    ordered = sorted(
        rows,
        key=lambda row: (str(row.get("tissue")) != target_tissue, -float(row.get("priority", 0.0)), str(row.get("tissue"))),
    )
    for rank, row in enumerate(ordered, start=1):
        row["rank"] = rank
    return ordered


def _row_to_score(row: Mapping[str, Any]) -> ReprogrammingFactorScore:
    return ReprogrammingFactorScore(
        factor_id=str(row.get("id", "")),
        name=str(row.get("name", "")),
        priority_score=float(row.get("score", 0.0)),
        safety_score=float(row.get("safety", 0.0)),
        components={str(key): float(value) for key, value in dict(row.get("components", {})).items()},
        target_tissues=tuple(str(item) for item in str(row.get("tissues", "")).split("、") if str(item)),
        modality=str(row.get("modality", "")),
        mechanism=str(row.get("mechanism", "")),
        recommendation=str(row.get("recommendation", "")),
        notes=str(row.get("notes", "")),
        evidence_sources=tuple(str(item) for item in row.get("evidence_sources", [])),
        evidence_basis=str(row.get("evidence_basis", "curated")),
        literature_count=int(row.get("literature_count", 0)),
        safety_warnings=tuple(str(item) for item in row.get("safety_warnings", [])),
    )


def _risk_block(title: str, risk_call: Mapping[str, Any]) -> str:
    rationale = "；".join(str(item) for item in risk_call.get("rationale", ()))
    return f"{title}：{risk_call.get('level', '-')}（{risk_call.get('score', '-')}）\n  {rationale}"


def _localized_recommendation(rank: int, score: float, safety: float) -> str:
    recommendation = _recommendation(rank, score, safety)
    return {
        "lead optimization": "优先优化",
        "validate in focused assays": "进入验证实验",
        "hold for mechanism review": "暂缓机制复核",
    }.get(recommendation, recommendation)


def _render_research_appendix(
    candidate_rows: list[Mapping[str, Any]],
    endpoints: list[Any],
    evidence_sources: list[Any],
    software_tools: list[Any],
    reprogramming_rows: list[Mapping[str, Any]] | None = None,
    combination_rows: list[Mapping[str, Any]] | None = None,
    tissue_plan_rows: list[Mapping[str, Any]] | None = None,
    gate_rows: list[Mapping[str, Any]] | None = None,
    gap_rows: list[Mapping[str, Any]] | None = None,
    summary: Mapping[str, Any] | None = None,
    gene_rows: list[Mapping[str, Any]] | None = None,
    organization_rows: list[Mapping[str, Any]] | None = None,
    audit: Mapping[str, Any] | None = None,
    diligence_rows: list[Mapping[str, Any]] | None = None,
    gene_portfolio: list[Mapping[str, Any]] | None = None,
    stress_rows: list[Mapping[str, Any]] | None = None,
    evidence_packs: list[Mapping[str, Any]] | None = None,
    method_card: Mapping[str, Any] | None = None,
    program_milestones: list[Mapping[str, Any]] | None = None,
    experiment_backlog: list[Mapping[str, Any]] | None = None,
    partner_shortlist: list[Mapping[str, Any]] | None = None,
    data_room_checklist: list[Mapping[str, Any]] | None = None,
) -> str:
    lines = [
        "",
        "## 研发设计补充",
        "",
        "### 推荐终点",
    ]
    for endpoint in sorted(endpoints, key=lambda item: -item.importance)[:5]:
        lines.append(
            f"- {endpoint.name}（{endpoint.category}，重要性 {endpoint.importance:.2f}）：{endpoint.description}"
        )
    lines.extend(["", "### 候选药证据锚点"])
    for candidate in candidate_rows:
        sources = candidate.get("sources") or []
        source_text = "；".join(str(source) for source in sources[:3]) if sources else "暂无证据锚点"
        lines.append(f"- {candidate['name']}：{source_text}")
    if summary:
        counts = summary.get("counts", {})
        targets = summary.get("targets", {})
        missing = summary.get("missing", {})
        lines.extend(["", "### 数据库资产完成度"])
        lines.append(
            f"- 论文：{counts.get('papers', 0)}/{targets.get('papers', 100)}，缺口 {missing.get('papers', 0)}。"
        )
        lines.append(
            f"- 候选基因：{counts.get('candidate_genes', 0)}/{targets.get('candidate_genes', 100)}，缺口 {missing.get('candidate_genes', 0)}。"
        )
        lines.append(
            f"- 公司/课题组：{counts.get('organizations', 0)}/{targets.get('organizations', 50)}，缺口 {missing.get('organizations', 0)}。"
        )
    if audit:
        lines.extend(["", "### 可信度审计"])
        lines.append(f"- 可信度分：{float(audit.get('credibility_score', 0.0)):.2f}；等级：{audit.get('credibility_grade', '-')}。")
        paper = audit.get("paper", {})
        gene_audit = audit.get("gene", {})
        lines.append(
            f"- 论文审计：唯一 PMID {paper.get('unique_pmids', 0)}，DOI {paper.get('doi_count', 0)}，高信号论文 {paper.get('high_signal_count', 0)}。"
        )
        lines.append(
            f"- 基因审计：检索式覆盖 {gene_audit.get('query_coverage', 0)}，PMID 命中基因 {gene_audit.get('literature_backed', 0)}，高风险已标记 {gene_audit.get('high_risk_flagged', 0)}。"
        )
        for flag in audit.get("red_flags", [])[:4]:
            lines.append(f"  - 红旗：{flag}")
    if gene_rows:
        lines.extend(["", "### 候选基因评分 Top 10"])
        for gene in gene_rows[:10]:
            lines.append(
                f"- {gene['symbol']}：总分 {float(gene['score']):.2f}，"
                f"年轻化 {float(gene['rejuvenation_potential']):.2f}，"
                f"风险 {float(gene['risk']):.2f}，"
                f"文献 {gene.get('literature_count', 0)} 篇，"
                f"溯源 {float(gene.get('provenance_score', 0.0)):.2f}，建议：{gene['recommendation']}。"
            )
    if diligence_rows:
        lines.extend(["", "### 投资人尽调问答"])
        for row in diligence_rows:
            lines.append(f"- Q：{row['question']}")
            lines.append(f"  - A：{row['answer']}")
            lines.append(f"  - 证据：{row['evidence']}")
    if method_card:
        lines.extend(["", "### 评分方法卡"])
        lines.append(f"- 方法版本：{method_card.get('method_version', '-')}")
        lines.append(f"- 公式：{method_card.get('formula', '-')}")
        lines.append(f"- 文献调整：{method_card.get('literature_adjustment', '-')}")
    if gene_portfolio:
        lines.extend(["", "### 基因研发组合分层"])
        for item in gene_portfolio[:15]:
            lines.append(
                f"- {item['symbol']}｜{item['bucket']}：评分 {float(item['score']):.2f}，"
                f"安全 {float(item['safety']):.2f}，溯源 {float(item['provenance']):.2f}，动作：{item['action']}。"
            )
    if stress_rows:
        lines.extend(["", "### 权重压力测试"])
        for item in stress_rows[:10]:
            lines.append(
                f"- {item['symbol']}：均值 {float(item['average_score']):.2f}，"
                f"跨度 {float(item['spread']):.2f}，稳定性：{item['stability']}，结论：{item['decision']}。"
            )
    if evidence_packs:
        lines.extend(["", "### 基因证据包摘要"])
        for pack in evidence_packs[:8]:
            lines.append(
                f"- {pack['symbol']}：论文 {pack['paper_count']}，"
                f"平均证据 {float(pack['average_evidence_score']):.2f}；{pack['summary']}"
            )
    if program_milestones:
        lines.extend(["", "### 90 天研发里程碑"])
        for item in program_milestones:
            lines.append(f"- {item['phase']}：{item['objective']}。交付物：{item['deliverable']}。")
            lines.append(f"  - 退出门槛：{item['exit_gate']}")
    if experiment_backlog:
        lines.extend(["", "### 实验/证据 Backlog"])
        for item in experiment_backlog[:12]:
            lines.append(
                f"- {item['task_id']}｜{item['priority']}｜{item['lane']}｜{item['target']}：{item['deliverable']}。"
            )
            lines.append(f"  - 成功标准：{item['success_criteria']}")
    if partner_shortlist:
        lines.extend(["", "### 合作方短名单"])
        for item in partner_shortlist[:8]:
            lines.append(
                f"- {item['name']}（{item['type']}，{item['country']}）：匹配 {float(item['fit_score']):.2f}；{item['fit_reason']}。"
            )
            lines.append(f"  - 切入：{item['outreach_angle']}")
    if data_room_checklist:
        lines.extend(["", "### Data Room 清单"])
        for item in data_room_checklist:
            lines.append(f"- {item['item']}｜{item['status']}：{item['evidence']}。下一步：{item['next_action']}。")
    if reprogramming_rows:
        lines.extend(["", "### 部分重编程因子优先级"])
        for factor in reprogramming_rows[:8]:
            lines.append(
                f"- {factor['name']}：优先级 {float(factor['score']):.2f}，"
                f"安全分 {float(factor['safety']):.2f}，"
                f"文献 {factor.get('literature_count', 0)} 篇，"
                f"评分：{'动态' if factor.get('evidence_basis') == 'literature_adjusted' else '基础'}，"
                f"建议：{factor['recommendation']}。"
            )
            for note in factor.get("process_notes", [])[:2]:
                lines.append(f"  - 过程：{note}")
            for step in factor.get("next_steps", [])[:2]:
                lines.append(f"  - 下一步：{step}")
            experiment = design_validation_experiment(_row_to_score(factor))
            lines.append(f"  - 实验草案：{experiment['objective']}")
            lines.append(f"  - Go/No-Go：{experiment['decision_gate']}")
    if combination_rows:
        lines.extend(["", "### 部分重编程组合策略"])
        for combo in combination_rows[:5]:
            lines.append(
                f"- {combo['name']}：优先级 {float(combo['score']):.2f}，"
                f"安全下限 {float(combo['safety']):.2f}，"
                f"风险档：{combo['risk_profile']}，因子：{combo['factors']}。"
            )
            lines.append(f"  - 策略：{combo['strategy']}")
            for item in combo.get("validation_plan", [])[:2]:
                lines.append(f"  - 验证：{item}")
    if tissue_plan_rows:
        lines.extend(["", "### 组织优先研发路线"])
        for plan in tissue_plan_rows[:5]:
            lines.append(
                f"- {plan['label']}：优先级 {float(plan['priority']):.2f}，"
                f"首选因子：{plan['lead_factors']}，组合：{plan['lead_combination']}。"
            )
            lines.append(f"  - 模型：{plan['model_system']}")
            lines.append(f"  - 递送：{plan['delivery_focus']}")
    if gate_rows:
        lines.extend(["", "### 安全闸门矩阵"])
        for gate in gate_rows[:6]:
            lines.append(
                f"- {gate['gate']}｜{gate['name']}：安全分 {float(gate['safety']):.2f}；"
                f"必须通过：{_join_or_dash(gate.get('must_pass', [])[:3])}。"
            )
    if gap_rows:
        lines.extend(["", "### 证据缺口与 AI 任务"])
        for gap in gap_rows[:6]:
            lines.append(
                f"- {gap['name']}：紧急度 {float(gap['urgency']):.2f}；"
                f"缺口：{_join_or_dash(gap.get('gaps', [])[:3])}。"
            )
            lines.append(f"  - 检索式：{gap['query']}")
            lines.append(f"  - AI任务：{gap['ai_task']}")
    if organization_rows:
        lines.extend(["", "### 公司/课题组地图样例"])
        for org in organization_rows[:12]:
            lines.append(f"- {org['name']}（{org['type']}，{org['country']}）：{org['focus']}。")
    lines.extend(["", "### 资料来源"])
    for source in sorted(evidence_sources, key=lambda item: -item.quality):
        lines.append(f"- {source.title}，{source.source}，{source.year}：{source.url}")
    lines.extend(["", "### 软件与数据库路线图"])
    for tool in software_tools:
        lines.append(f"- {tool.name}（{tool.category}）：{tool.role}；状态：{tool.integration_status}。")
    lines.append("")
    return "\n".join(lines)


def _render_investor_diligence(
    *,
    summary: Mapping[str, Any],
    audit: Mapping[str, Any],
    diligence_rows: list[Mapping[str, Any]],
    gene_rows: list[Mapping[str, Any]],
    gene_portfolio: list[Mapping[str, Any]],
    stress_rows: list[Mapping[str, Any]],
    evidence_packs: list[Mapping[str, Any]],
    organization_rows: list[Mapping[str, Any]],
    reprogramming_rows: list[Mapping[str, Any]],
    combination_rows: list[Mapping[str, Any]],
    program_milestones: list[Mapping[str, Any]],
    experiment_backlog: list[Mapping[str, Any]],
    partner_shortlist: list[Mapping[str, Any]],
    data_room_checklist: list[Mapping[str, Any]],
) -> str:
    counts = summary.get("counts", {})
    targets = summary.get("targets", {})
    paper = audit.get("paper", {})
    gene = audit.get("gene", {})
    organization = audit.get("organization", {})
    lines = [
        "# Asclepius 投资人尽调摘要",
        "",
        "## 一句话定位",
        "",
        "Asclepius 是一个面向部分表观遗传重编程的本地研发情报系统，把论文、候选基因、公司/课题组、基因评分、安全闸门和验证路线串成可审计工作流。",
        "",
        "## 数据资产",
        "",
        f"- 论文：{counts.get('papers', 0)}/{targets.get('papers', 100)}",
        f"- 候选基因：{counts.get('candidate_genes', 0)}/{targets.get('candidate_genes', 100)}",
        f"- 公司/课题组：{counts.get('organizations', 0)}/{targets.get('organizations', 50)}",
        f"- 可信度等级：{audit.get('credibility_grade', '-')}",
        f"- 可信度分：{float(audit.get('credibility_score', 0.0)):.2f}",
        "",
        "## 审计结果",
        "",
        f"- 唯一 PMID：{paper.get('unique_pmids', 0)}",
        f"- DOI 覆盖：{paper.get('doi_count', 0)}",
        f"- 高信号论文：{paper.get('high_signal_count', 0)}",
        f"- 基因检索式覆盖：{gene.get('query_coverage', 0)}/{gene.get('records', 0)}",
        f"- PMID 命中基因：{gene.get('literature_backed', 0)}/{gene.get('records', 0)}",
        f"- 高风险基因已标记：{gene.get('high_risk_flagged', 0)}",
        f"- 机构 URL 覆盖：{organization.get('url_coverage', 0)}/{organization.get('records', 0)}",
        "",
        "## Top 候选基因",
    ]
    for item in gene_rows[:12]:
        lines.append(
            f"- {item['symbol']}：总分 {float(item['score']):.2f}，"
            f"风险 {float(item['risk']):.2f}，文献 {item.get('literature_count', 0)}，"
            f"溯源 {float(item.get('provenance_score', 0.0)):.2f}，{item['recommendation']}"
        )
    lines.extend(["", "## 基因研发组合分层"])
    for item in gene_portfolio[:15]:
        lines.append(
            f"- {item['symbol']}｜{item['bucket']}：评分 {float(item['score']):.2f}，"
            f"安全 {float(item['safety']):.2f}，溯源 {float(item['provenance']):.2f}，动作：{item['action']}"
        )
    lines.extend(["", "## 权重压力测试"])
    for item in stress_rows[:10]:
        lines.append(
            f"- {item['symbol']}：均值 {float(item['average_score']):.2f}，跨度 {float(item['spread']):.2f}，"
            f"{item['stability']}，{item['decision']}"
        )
    lines.extend(["", "## 证据包样例"])
    for pack in evidence_packs[:8]:
        paper_bits = [
            f"PMID {paper['pmid']}({float(paper['evidence_score']):.2f})"
            for paper in pack.get("top_papers", [])[:3]
        ]
        lines.append(
            f"- {pack['symbol']}：论文 {pack['paper_count']}，平均证据 {float(pack['average_evidence_score']):.2f}，"
            f"代表证据：{'；'.join(paper_bits) if paper_bits else '暂无'}"
        )
    lines.extend(["", "## 90 天研发里程碑"])
    for item in program_milestones:
        lines.append(f"- {item['phase']}：{item['objective']}；交付物：{item['deliverable']}；门槛：{item['exit_gate']}")
    lines.extend(["", "## 实验/证据 Backlog"])
    for item in experiment_backlog[:12]:
        lines.append(
            f"- {item['task_id']}｜{item['priority']}｜{item['lane']}｜{item['target']}：{item['deliverable']}；成功标准：{item['success_criteria']}"
        )
    lines.extend(["", "## 合作方短名单"])
    for item in partner_shortlist[:8]:
        lines.append(
            f"- {item['name']}（{item['type']}，{item['country']}）：匹配 {float(item['fit_score']):.2f}；"
            f"{item['fit_reason']}；切入：{item['outreach_angle']}"
        )
    lines.extend(["", "## Data Room 清单"])
    for item in data_room_checklist:
        lines.append(f"- {item['item']}｜{item['status']}：{item['evidence']}；下一步：{item['next_action']}")
    lines.extend(["", "## Top 部分重编程因子"])
    for item in reprogramming_rows[:8]:
        lines.append(
            f"- {item['name']}：优先级 {float(item['score']):.2f}，安全 {float(item['safety']):.2f}，文献 {item.get('literature_count', 0)}"
        )
    lines.extend(["", "## 组合策略"])
    for item in combination_rows[:5]:
        lines.append(
            f"- {item['name']}：优先级 {float(item['score']):.2f}，安全下限 {float(item['safety']):.2f}，因子：{item['factors']}"
        )
    lines.extend(["", "## 投资人问答"])
    for row in diligence_rows:
        lines.append(f"- Q：{row['question']}")
        lines.append(f"  - A：{row['answer']}")
        lines.append(f"  - 证据：{row['evidence']}")
    lines.extend(["", "## 红旗披露"])
    for flag in audit.get("red_flags", []):
        lines.append(f"- {flag}")
    lines.extend(["", "## 下一步验证"])
    for step in audit.get("next_steps", []):
        lines.append(f"- {step}")
    lines.extend(
        [
            "",
            "## 边界声明",
            "",
            "本报告用于研发规划、合作沟通和尽调前材料准备，不代表真实疗效、临床安全性、监管结论或投资建议。",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
