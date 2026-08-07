import flodym as fd
import numpy as np
import pandas as pd

import plotly.graph_objects as go
from typing import TYPE_CHECKING
import flodym.export as fde
import plotly.express as px
import flochart as flc
from matplotlib import pyplot as plt

from remind_mfa.common.common_visualization import CommonVisualizer

if TYPE_CHECKING:
    from remind_mfa.plastics.plastics_model import PlasticsModel


class PlasticsVisualizer(CommonVisualizer):

    def visualize_custom(self, model: "PlasticsModel"):
        if self.cfg.use_stock.do_visualize:
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.stocks["in_use"].stock,
                name="Stock",
                linecolor_dim="Good",
                regional=False,
            )

        if self.cfg.consumption.do_visualize:
            self.compare_demand(mfa=model.future_mfa)
            self.visualize_material_splits(mfa=model.future_mfa)

        if self.cfg.extrapolation.do_visualize:
            self.visualize_extrapolation(model=model, subplot_dim="Good", linecolor_dim="Region")
            self.visualize_extrapolation(model=model, subplot_dim="Region", linecolor_dim="Good")
            self.visualize_extrapolation_functions(model=model, stock_handler=model.stock_handler)

        if self.cfg.flows.do_visualize:
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["polymerization => primary_market"],
                name="Primary production",
                linecolor_dim="Material",
            )
            self.visualize_fdarr(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["polymerization => primary_market"],
                name="Primary production",
                linecolor_dim="Material",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["primary_market => fabrication"],
                name="Primary plastics demand",
                linecolor_dim="Material",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["fabrication => good_market"],
                name="Fabrication",
                linecolor_dim="Material",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.stocks["in_use"].inflow,
                name="Demand",
                linecolor_dim="Material",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["reclmech => primary_market"],
                name="Mechanically recycled",
                linecolor_dim="Material",
            )
            self.visualize_fdarr(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["reclchem => HVC_input"],
                name="Chemically recycled",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["eol => collected"],
                name="Collected",
                linecolor_dim="Material",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["collected => reclmech"],
                name="Sorted to mechanical recycling",
                linecolor_dim="Material",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["collected => landfill"],
                name="Landfilled",
                linecolor_dim="Material",
            )
            self.visualize_fdarr_stacked(
                mfa=model.future_mfa,
                flow=model.future_mfa.flows["collected => incineration"],
                name="Incinerated",
                linecolor_dim="Material",
            )
        self.stop_and_show()

    def visualize_consumption(self, mfa: fd.MFASystem):
        per_capita = self.cfg.consumption.per_capita
        demand = mfa.stocks["in_use"].inflow.sum_over(("m", "e"))
        self.visualize_fdarr_stacked(
            mfa=mfa,
            flow=demand,
            name="Plastic consumption",
            linecolor_dim="Good",
            per_capita=per_capita,
            regional=True,
        )

    def compare_demand(self, mfa: fd.MFASystem):
        df = pd.read_csv("data/plastics/input/validation.csv", sep=";")

        # Convert year to numeric
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        # Convert Mt to t
        df["value"] = df["value"] * 1000 * 1000

        # Plotly line plot
        fig = px.line(df, x="year", y="value", color="source", markers=True)

        ap = self.plotter_class(
            array=mfa.stocks["in_use"].inflow.sum_over(("r", "m", "e", "g")),
            intra_line_dim="Time",
            title="Demand [t]",
            line_label="REMIND-MFA",
            fig=fig,
        )
        ap.plot()
        self.plot_and_save_figure(ap, "demand_validation.png", do_plot=False)

    def visualize_use_stock(self, mfa: fd.MFASystem, subplots_by_good=False):
        subplot_dim = "Good" if subplots_by_good else None
        super().visualize_use_stock(mfa, stock=mfa.stocks["in_use"].stock, subplot_dim=subplot_dim)

    def visualize_trade(self, mfa: fd.MFASystem, linecolor_dims=True):
        if linecolor_dims is True:
            linecolor_dims = {
                "primary": "Material",
                "final": "Material",
                "waste": "Material",
            }
        else:
            linecolor_dims = {
                "primary": None,
                "final": None,
                "waste": None,
            }
        super().visualize_trade(mfa, linecolor_dims=linecolor_dims)

    def visualize_sankey(self, mfa: fd.MFASystem):
        # Define colors for each stage
        colors = dict(
            production_color = "#EDC948",
            use_color = "#9EC3D5",
            eol_color = "#499894",
            recycle_color = "#86BCB6",
            emission_color = "#E15759",
            trade_color = "#D37295",
        )

        # Initialize default flow color mapping
        flow_color_dict = {"default": colors["production_color"]}

        # Assign colors to 'use' flows
        flow_color_dict.update(
            {
                fn: colors["use_color"]
                for fn, f in mfa.flows.items()
                if f.from_process.name == "use" or f.to_process.name == "use"
            }
        )

        # Assign colors to end-of-life flows
        flow_color_dict.update(
            {
                fn: colors["eol_color"]
                for fn, f in mfa.flows.items()
                if f.from_process.name in ("eol", "collected")
            }
        )

        # Assign colors to emission flows
        flow_color_dict.update(
            {
                fn: colors["emission_color"]
                for fn, f in mfa.flows.items()
                if f.to_process.name
                in ("atmosphere", "mismanaged", "uncontrolled", "emission", "losses")
            }
        )

        # Assign colors to recycling flows
        flow_color_dict.update(
            {
                fn: colors["recycle_color"]
                for fn, f in mfa.flows.items()
                if f.from_process.name in ("reclmech", "reclchem")
                or f.to_process.name in ("reclmech", "reclchem")
            }
        )

        # Assign colors to trade flows
        flow_color_dict.update(
            {
                fn: colors["trade_color"]
                for fn, f in mfa.flows.items()
                if f.from_process.name in ("imports", "exports")
                or f.to_process.name in ("imports", "exports")
            }
        )

        # Update Sankey layout configuration
        self.cfg.sankey.plotter_args.update(
            {
                "valueformat": ".2s",  # scientific notation, two significant digits
                "node_pad": 15,  # padding between nodes
                "node_thickness": 20,  # node thickness
                "arrangement": "snap",  # reduce crossings by snapping nodes
                "flow_color_dict": flow_color_dict,
                "node_color_dict": {"default": "gray", "use": "black"},
            }
        )

        # Prepare display names and generate the Sankey diagram
        # display_names_fmt = {k: f"<b>{v}</b>" for k, v in self.display_names.dct.items()}
        display_names_fmt = self.display_names.dct
        plotter = fde.PlotlySankeyPlotter(
            mfa=mfa, display_names=display_names_fmt, **self.cfg.sankey.plotter_args
        )
        # fig = plotter.plot()
        links = plotter._get_links_dict()
        nodes = plotter._get_nodes_dict()

        # TODO: Make engine configurable via config file
        engine = "flochart"

        if engine == "flochart":
            self.plot_sankey_flochart(nodes=nodes, links=links, colors=colors)
        elif engine == "plotly":
            self.plot_sankey_plotly(nodes=nodes, links=links, colors=colors)


    def plot_sankey_flochart(self, nodes: dict, links: dict, colors: dict):
        nodesxy = [
            ( 0, 0),  # 'Feedstock<br>(fossil)',
            ( 0, 0),  # 'Feedstock<br>(biomass)',
            ( 0, 0),  # 'Feedstock<br>(DACCU)',
            ( 0, 0),  # 'Feedstock<br>(CCU)',
            ( 1, 0),  # 'High value chemicals input',
            ( 1, 1),  # 'C4 input',
            ( 2, 0),  # 'Polymerization',
            ( 3, 0),  # 'Primary<br>market',
            ( 4, 0),  # 'Fabrication',
            ( 5, 0),  # 'Good market',
            ( 6, 0),  # 'Use phase',
            ( 7, 0),  # 'EoL',
            ( 0, 0),  # 'Waste market',
            ( 9, 0),  # 'Mechanical<br>recycling',
            ( 9, 1),  # 'Chemical<br>recycling',
            (10, 2),  # 'Incineration',
            ( 0, 0),  # 'Landfilled',
            ( 8, 0),  # 'Collected',
            ( 8, 2),  # 'Uncollected',
            ( 9, 2),  # 'Uncontrolled',
            (11, 0),  # 'Emissions',
            ( 0, 0),  # 'Captured',
            (12, 0),  # 'Atmosphere',
            ( 1, 2),  # 'Other reactants',
            ( 0, 0),  # 'Losses',
        ]

        def to_node_def(i):
            return flc.NodeDefinition(
                name = str(i),
                x = nodesxy[i][0],
                y = nodesxy[i][1],
                min_size_x= 0.2,
            )
        node_defs = [to_node_def(i) for i in range(len(nodes["label"]))]

        def to_flow_def(i):
            return flc.FlowDefinition(
                name = f"{links["source"][i]} => {links["target"][i]}",
                source = str(links["source"][i]),
                target = str(links["target"][i]),
                value = links["value"][i] / 5e8,
                color = links["color"][i],
            )

        flow_defs = [to_flow_def(i) for i in range(len(links["source"]))]

        sys_def = flc.SystemDefinition(
            fig_size=(10, 7),
        )

        system = flc.System(
            definition=sys_def,
            node_definitions=node_defs,
            flow_definitions=flow_defs,
        )
        fig = system.draw()
        plt.show()



    def plot_sankey_plotly(self, nodes: dict, links: dict, colors: dict):
        fig = go.Figure(
            go.Sankey(
                arrangement="snap",
                link=links,
                node=nodes,
            )
        )
        # Add legend entries
        legend_entries = [
            (colors["production_color"], "Production"),
            (colors["use_color"], "Use"),
            (colors["eol_color"], "End-of-Life"),
            (colors["recycle_color"], "Recycling"),
            (colors["emission_color"], "Losses"),
            (colors["trade_color"], "Trade"),
        ]
        for color, label in legend_entries:
            fig.add_trace(
                go.Scatter(
                    mode="markers",
                    x=[None],
                    y=[None],
                    marker=dict(size=10, color=color, symbol="square"),
                    name=label,
                )
            )

        # Final layout adjustments and display
        fig.update_layout(
            font_size=10, showlegend=True, plot_bgcolor="rgba(0,0,0,0)", font_color="black"
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)

        self._show_and_save_plotly(fig, name="sankey")

    def visualize_material_splits(self, mfa: fd.MFASystem):

        material_shares = mfa.parameters["material_shares_use_inflow"][
            {"t": 2019}
        ]  # material shares are kept constant over time, so we can just take the value for one year
        material_shares = material_shares.cumsum(dim_letter="m")

        ap_sector_splits = self.plotter_class(
            array=material_shares,
            intra_line_dim="Region",
            subplot_dim="Good",
            linecolor_dim="Material",
            xlabel="Year",
            ylabel="Material Splits [%]",
            display_names=self.display_names.dct,
            title=f"Product demand material splits",
            chart_type="area",
        )

        self.plot_and_save_figure(ap_sector_splits, f"material_splits.png")

    def visualize_extrapolation(
        self,
        model: "PlasticsModel",
        subplot_dim: str = "Region",
        linecolor_dim: str = None,
        show_extrapolation: bool = True,
        show_future: bool = True,
    ):
        super().visualize_extrapolation(
            model=model,
            subplot_dim=subplot_dim,
            linecolor_dim=linecolor_dim,
            show_extrapolation=show_extrapolation,
            show_future=show_future,
        )
