# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Paper-styled plotting helpers for the benchkit ICPE'26 artifact.

This module reproduces the visual style of the figures in the paper so that the
experiment scripts can regenerate paper-exact plots *on the fly*, at the end of
each campaign, instead of relying on the framework's default
``campaign.generate_graph()`` styling (which the AE reviewers noted differs from
the paper in markers, line width, and typography).

It ports the seaborn configuration and per-figure plot recipes from the original
paper notebooks (``charts.ipynb``, ``overhead.ipynb``, ``taskset.ipynb`` in the
internal results repo) and builds on benchkit's own chart utilities:

    - benchkit.charts.printedcharts.export_figure  -> reproducible PDF metadata
    - benchkit.charts.dataframes.get_dataframe      -> CSV -> DataFrame (";" sep,
                                                       "#" comments, derives
                                                       ``throughput``)

Typical use at the end of an experiment's ``run()``::

    from lib.plots import set_paper_style, combine_panel_dfs, lineplot_by_bench

    set_paper_style()                       # apply the paper theme once
    df = combine_panel_dfs(zip(panels, campaigns))
    lineplot_by_bench(df, hue="lock", out_path=out_dir / "figure3_locks.pdf")

Paper fonts: ``set_paper_style(use_latex=False)`` by default, so figures render
without a full LaTeX toolchain (AE reviewers ran on stock machines). Pass
``use_latex=True`` -- wired to the experiments' ``--paper-fonts`` flag -- for the
exact paper typography.

NOTE: this module is imported lazily by the experiment scripts
(``from lib.plots import ...``); it is intentionally NOT re-exported from
``lib/__init__.py`` so that non-plotting scripts do not pull in matplotlib.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from benchkit.charts.dataframes import get_dataframe
from benchkit.charts.printedcharts import export_figure

# --- Shared paper style (ported verbatim from the paper notebooks) ----------

_CONTEXT = "talk"
_STYLE = "whitegrid"
_PALETTE = "colorblind"

# Fixed date embedded in the exported PDFs so figure bytes are reproducible
# (identical to the paper notebooks' export_fig()).
_FIG_YEAR, _FIG_MONTH, _FIG_DAY = 2024, 12, 10


def set_paper_style(
    *,
    width: float = 8.0,
    height: float = 6.0,
    font_scale: float = 1.15,
    use_latex: bool = False,
) -> None:
    """Apply the paper's seaborn theme (talk / whitegrid / colorblind palette).

    Args:
        width, height: default figure size in inches.
        font_scale: seaborn font scaling (1.15 in the paper).
        use_latex: render text via LaTeX for exact paper typography. Default
            False to avoid requiring a LaTeX install; the experiments expose
            ``--paper-fonts`` to enable it.
    """
    sns.set_theme(
        context=_CONTEXT,
        style=_STYLE,
        palette=_PALETTE,
        font_scale=font_scale,
        rc={
            "figure.figsize": (width, height),
            # Embed TrueType (editable, ACM-friendly). Do NOT set pdf.use14corefonts:
            # it forces the base-14 "Helvetica" core font, which is not an installed
            # TTF on Linux and triggers endless findfont fallback warnings.
            "pdf.fonttype": 42,
            "text.usetex": use_latex,
        },
    )


def export_fig(plot, path: Path | str) -> Path:
    """Export a seaborn/matplotlib figure to PDF with reproducible metadata.

    Wraps benchkit's ``export_figure`` (handles FacetGrid/catplot objects, which
    expose ``.figure``) and ensures the parent directory exists.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    export_figure(
        plot=plot,
        path=str(path),
        creation_year=_FIG_YEAR,
        creation_month=_FIG_MONTH,
        creation_day=_FIG_DAY,
    )
    print(f"[INFO] Paper figure generated: {path}")
    return path


# --- DataFrame helpers ------------------------------------------------------


def load_campaign_df(campaign) -> pd.DataFrame:
    """Load a finished campaign's result CSV into a DataFrame.

    Call after ``campaign.run()``. Uses benchkit's own parser so derived columns
    (notably ``throughput``) are present.
    """
    return get_dataframe(campaign.csv_output_abs_path())


def combine_panel_dfs(panels_and_campaigns: Iterable[Tuple]) -> pd.DataFrame:
    """Concatenate per-panel campaign results into one DataFrame.

    The paper's locks/schedulers figures (Figures 3 and 4) are 5-panel
    FacetGrids over a ``benchmark`` column, but the artifact runs one campaign
    per panel. This stitches them back together, tagging each row with its
    ``Panel.name`` so the builders can facet over it.

    Args:
        panels_and_campaigns: iterable of ``(Panel, Campaign)`` pairs.
    """
    frames = []
    for panel, campaign in panels_and_campaigns:
        df = load_campaign_df(campaign)
        df["benchmark"] = panel.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# --- Figure builders --------------------------------------------------------


def lineplot_by_bench(
    df: pd.DataFrame,
    *,
    hue: str,
    x: str = "nb_threads",
    y: str = "throughput",
    facet_col: str = "benchmark",
    legend_ncol: int = 8,
    out_path: Optional[Path] = None,
):
    """Multi-panel throughput-vs-threads line plot (Figures 3 and 4).

    One facet per benchmark, one marked line per ``hue`` value (lock or
    scheduler) -- reproduces the paper's FacetGrid + ``lineplot(marker="o")``.

    Note: ``hue`` should be a display-ready column. To get the paper's legend
    labels, map the raw ``lock``/``scheduler`` column through ``PRETTY_LOCKS`` /
    ``PRETTY_SCHEDULERS`` before calling (or pass the raw column and relabel).
    """
    g = sns.FacetGrid(
        df,
        col=facet_col,
        col_order=sorted(df[facet_col].unique()),
        margin_titles=True,
        height=4,
        aspect=1.2,
        sharey=False,
    )
    g.map_dataframe(
        sns.lineplot,
        x=x,
        y=y,
        hue=hue,
        style=hue,
        marker="o",
        markers=True,
        dashes=False,
    )
    g.set_axis_labels("Number of Threads", "Throughput")
    g.set_titles(col_template="{col_name}")
    g.add_legend(ncol=legend_ncol, loc="upper center", bbox_to_anchor=(0.3, 1.12))
    g.tight_layout()
    if out_path is not None:
        export_fig(g, out_path)
    return g


def stripplot_by_category(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    order: Optional[list] = None,
    facet_col: Optional[str] = None,
    ylabel: str = "",
    title: Optional[str] = None,
    rotate_xticks: int = 25,
    out_path: Optional[Path] = None,
):
    """Per-run strip plot across categories (Figure 2 left; Figure 7 overhead).

    Shows the raw per-run scatter for each category on ``x`` (e.g. CPU placement
    or run type), one point per run. Pass ``facet_col`` (e.g. ``nb_threads``) for
    the faceted overhead figure.
    """
    kwargs = dict(
        data=df.reset_index(drop=True),
        x=x,
        y=y,
        hue=x,
        kind="strip",
        dodge=True,
        height=4,
        aspect=0.9,
        sharey=False,
        legend=False,
    )
    if order is not None:
        kwargs["order"] = order
    if facet_col is not None:
        kwargs["col"] = facet_col
        kwargs["col_order"] = sorted(df[facet_col].unique())
    g = sns.catplot(**kwargs)
    g.set_axis_labels("", ylabel)
    if title is not None and facet_col is None:
        g.axes.flatten()[0].set_title(title)
    for ax in g.axes.flatten():
        ax.set_xticklabels(ax.get_xticklabels(), rotation=rotate_xticks, ha="right")
    plt.tight_layout()
    if out_path is not None:
        export_fig(g, out_path)
    return g


def barplot_by_category(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    aspect: float = 1.4,
    rotate_xticks: int = 45,
    out_path: Optional[Path] = None,
):
    """Single-colour per-category bar plot (Figure 2 right: per-CPU heater).

    Matches the paper: all bars share one colour (no per-category hue), with
    rotated x tick labels. Pass a wider ``aspect`` when there are many categories
    (e.g. the 24-CPU heater sweep).
    """
    g = sns.catplot(
        data=df,
        x=x,
        y=y,
        kind="bar",
        color=sns.color_palette()[0],
        height=4,
        aspect=aspect,
        legend=False,
    )
    g.set_axis_labels(
        xlabel if xlabel is not None else x,
        ylabel if ylabel is not None else y,
    )
    if title is not None:
        g.axes.flatten()[0].set_title(title)
    for ax in g.axes.flatten():
        ax.set_xticklabels(ax.get_xticklabels(), rotation=rotate_xticks, ha="right")
    plt.tight_layout()
    if out_path is not None:
        export_fig(g, out_path)
    return g


def perfstat_barplot(
    df: pd.DataFrame,
    *,
    group_col: str = "scheduler",
    out_path: Optional[Path] = None,
):
    """Per-metric bar grid for the perf-stat study (Figure 5).

    Melts throughput + the ``perf-stat/*`` counter columns into long form and
    draws one bar panel per metric, one bar per ``group_col`` value. Drops the
    rate/coverage/unit and ``cpu_atom`` variants of the perf-stat columns, as in
    the paper notebook.
    """
    df = df.copy()
    if "throughput" in df.columns:
        df["Throughput"] = df["throughput"]
    metric_cols = ["Throughput"] + [
        c
        for c in df.columns
        if c.startswith("perf-stat/")
        and not (c.endswith(".rt") or c.endswith(".cov") or c.endswith(".unit") or "cpu_atom" in c)
    ]
    long = df.melt(
        id_vars=[group_col],
        value_vars=metric_cols,
        var_name="metric",
        value_name="value",
    )
    g = sns.catplot(
        data=long,
        x=group_col,
        y="value",
        hue=group_col,
        col="metric",
        kind="bar",
        col_wrap=5,
        height=4,
        aspect=1.2,
        sharey=False,
        legend=False,
    )
    g.set_titles("{col_name}")
    g.set_axis_labels(group_col.capitalize(), "Value")
    for ax in g.axes.flat:
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")
    plt.tight_layout()
    if out_path is not None:
        export_fig(g, out_path)
    return g


def flamegraph_svg_to_pdf(svg_path: Path | str, pdf_path: Path | str) -> Path:
    """Convert a flame-graph SVG to PDF (Figure 6), as in the paper pipeline."""
    import cairosvg

    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
    print(f"[INFO] Paper figure generated: {pdf_path}")
    return pdf_path
