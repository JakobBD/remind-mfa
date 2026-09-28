import csv
import os
import pathlib

from dotenv import load_dotenv
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import _utils
from _constants import MATERIAL_ORDER, figure_output_path, get_material_config

load_dotenv()

LINE_WIDTH_SCALE = 1.5
LINE_WIDTH_DEFAULT = 2 * LINE_WIDTH_SCALE
LINE_WIDTH_STACK = 0.5 * LINE_WIDTH_SCALE
LINE_WIDTH_VLINE = 1.2 * LINE_WIDTH_SCALE
LEFT_Y_TITLE_X = 0
LEFT_Y_TITLE_XSHIFT = -30
MAXIMUM_LEGENDTEXT_BRIGHTNESS = 0.4
LEGEND_FONT_SIZE = 14
REGION_MAPPING_PATH = pathlib.Path(__file__).resolve().with_name("regionmapping.csv")


def _load_country_to_h12_region_map() -> dict:
    region_map = {}
    with REGION_MAPPING_PATH.open(newline="", encoding="utf-8") as file_handle:
        reader = csv.reader(file_handle, delimiter=";")
        next(reader, None)
        for row in reader:
            if len(row) < 4:
                continue
            country_code = row[2].strip()
            region_code = row[3].strip()
            if country_code:
                region_map[country_code] = region_code
    return region_map


COUNTRY_TO_H12_REGION = _load_country_to_h12_region_map()


def _configure_browser_path():
    browser_path = os.getenv("BROWSER_PATH")
    if not browser_path:
        return
    browser_path_obj = pathlib.Path(browser_path)
    if browser_path_obj.is_dir():
        chrome_executable = browser_path_obj / "chrome.exe"
        if chrome_executable.exists():
            os.environ["BROWSER_PATH"] = str(chrome_executable)


_configure_browser_path()


def _legend_name(label: str, color: str) -> str:
    return _utils.legend_name(label, color, MAXIMUM_LEGENDTEXT_BRIGHTNESS)


def _get_region_color(region: str, region_colors: dict, aggregate_regions: bool) -> str:
    return _utils.get_region_color(region, region_colors, aggregate_regions=aggregate_regions)


def _aggregate_region_timeseries_with_map(
    df, time_col: str, region_col: str, value_col: str, region_map: dict
):
    aggregated = df.copy()
    aggregated[region_col] = aggregated[region_col].map(
        lambda region: region_map.get(str(region), str(region))
    )
    group_cols = [time_col, region_col]
    return aggregated.groupby(group_cols, as_index=False)[value_col].sum().sort_values(group_cols)


def _aggregate_weighted_region_timeseries(
    values_df,
    weights_df,
    value_time_col: str,
    value_region_col: str,
    value_col: str,
    weight_time_col: str,
    weight_region_col: str,
    weight_col: str,
    aggregate_regions: bool,
    region_map: dict | None = None,
):
    weight_value_col = f"{weight_col}_weight"
    aggregated = values_df.merge(
        weights_df[
            [weight_time_col, weight_region_col, weight_col]
        ].rename(columns={weight_col: weight_value_col}),
        left_on=[value_time_col, value_region_col],
        right_on=[weight_time_col, weight_region_col],
    )
    if region_map is not None:
        aggregated[value_region_col] = aggregated[value_region_col].map(
            lambda region: region_map.get(str(region), str(region))
        )
    aggregated[value_region_col] = aggregated[value_region_col].map(
        lambda region: _utils.map_region(region, aggregate_regions=aggregate_regions)
    )
    aggregated["_weighted_value"] = aggregated[value_col] * aggregated[weight_value_col]
    result = (
        aggregated.groupby([value_time_col, value_region_col], as_index=False)[
            ["_weighted_value", weight_value_col]
        ]
        .sum()
        .sort_values([value_time_col, value_region_col])
    )
    result[value_col] = result["_weighted_value"] / result[weight_value_col]
    return result[[value_time_col, value_region_col, value_col]]


def _attach_axis_values(
    df,
    axis_df,
    df_time_col: str,
    df_region_col: str | None,
    axis_time_col: str,
    axis_region_col: str | None,
    axis_value_col: str,
    output_col: str,
):
    axis_values = axis_df.rename(columns={axis_value_col: output_col})
    left_on = [df_time_col]
    right_on = [axis_time_col]
    if df_region_col is not None and axis_region_col is not None:
        left_on.append(df_region_col)
        right_on.append(axis_region_col)
    return df.merge(axis_values, left_on=left_on, right_on=right_on)


def _write_png(fig: go.Figure, output_path: pathlib.Path):
    png_bytes = fig.to_image(
        format="png",
        width=fig.layout.width,
        height=fig.layout.height,
        scale=3,
    )
    output_path.write_bytes(png_bytes)


def _load_run_data(config, aggregate_regions: bool, mfa_regions: str):
    model = _utils.load_model(config.material, region_mapping=mfa_regions)
    mfa = model.future_mfa

    flow = (mfa.flows[config.production_flow_name].sum_to(("t", "r")) / 1e6).to_df().reset_index()
    time_col_flow = _utils.get_column_name(flow, "Time")
    region_col_flow = _utils.get_column_name(flow, "Region")
    value_col_flow = _utils.get_column_name(flow, "value")

    if mfa_regions == "iso249":
        flow = _aggregate_region_timeseries_with_map(
            flow,
            time_col_flow,
            region_col_flow,
            value_col_flow,
            COUNTRY_TO_H12_REGION,
        )

    flow = _utils.aggregate_region_timeseries(
        flow,
        time_col_flow,
        region_col_flow,
        value_col_flow,
        aggregate_regions=aggregate_regions,
    )

    stock = mfa.stocks["in_use"].stock
    if config.stock_index is not None:
        stock = stock[config.stock_index]
    stock = stock.sum_to(("t", "r")).to_df().reset_index()
    population = mfa.parameters["population"].sum_to(("t", "r")).to_df().reset_index()
    gdppc = model.parameters["gdppc"].sum_to(("t", "r")).to_df().reset_index()

    time_col_stock = _utils.get_column_name(stock, "Time")
    region_col_stock = _utils.get_column_name(stock, "Region")
    value_col_stock = _utils.get_column_name(stock, "value")
    time_col_pop = _utils.get_column_name(population, "Time")
    region_col_pop = _utils.get_column_name(population, "Region")
    value_col_pop = _utils.get_column_name(population, "value")
    time_col_gdppc = _utils.get_column_name(gdppc, "Time")
    region_col_gdppc = _utils.get_column_name(gdppc, "Region")
    value_col_gdppc = _utils.get_column_name(gdppc, "value")

    if mfa_regions == "iso249":
        stock = _aggregate_region_timeseries_with_map(
            stock,
            time_col_stock,
            region_col_stock,
            value_col_stock,
            COUNTRY_TO_H12_REGION,
        )
        population = _aggregate_region_timeseries_with_map(
            population,
            time_col_pop,
            region_col_pop,
            value_col_pop,
            COUNTRY_TO_H12_REGION,
        )

    gdppc = _aggregate_weighted_region_timeseries(
        gdppc,
        population,
        time_col_gdppc,
        region_col_gdppc,
        value_col_gdppc,
        time_col_pop,
        region_col_pop,
        value_col_pop,
        aggregate_regions=aggregate_regions,
        region_map=COUNTRY_TO_H12_REGION if mfa_regions == "iso249" else None,
    )

    stock = _utils.aggregate_region_timeseries(
        stock,
        time_col_stock,
        region_col_stock,
        value_col_stock,
        aggregate_regions=aggregate_regions,
    )
    population = _utils.aggregate_region_timeseries(
        population,
        time_col_pop,
        region_col_pop,
        value_col_pop,
        aggregate_regions=aggregate_regions,
    )

    stock_pc = stock.merge(
        population,
        left_on=[time_col_stock, region_col_stock],
        right_on=[time_col_pop, region_col_pop],
        suffixes=("_stock", "_population"),
    )
    stock_pc[value_col_stock] = (
        stock_pc[f"{value_col_stock}_stock"] / stock_pc[f"{value_col_pop}_population"]
    )
    stock_pc = stock_pc[[time_col_stock, region_col_stock, value_col_stock]]

    production_pc = flow.merge(
        population,
        left_on=[time_col_flow, region_col_flow],
        right_on=[time_col_pop, region_col_pop],
        suffixes=("_production", "_population"),
    )
    production_pc[value_col_flow] = (
        production_pc[f"{value_col_flow}_production"]
        / production_pc[f"{value_col_pop}_population"]
        * 1e6
    )
    production_pc = production_pc[[time_col_flow, region_col_flow, value_col_flow]]

    global_avg = stock.groupby(time_col_stock, as_index=False)[value_col_stock].sum()
    global_population = population.groupby(time_col_pop, as_index=False)[value_col_pop].sum()
    global_avg = global_avg.merge(
        global_population,
        left_on=time_col_stock,
        right_on=time_col_pop,
        suffixes=("_stock", "_population"),
    )
    global_avg[value_col_stock] = (
        global_avg[f"{value_col_stock}_stock"] / global_avg[f"{value_col_pop}_population"]
    )

    global_production = flow.groupby(time_col_flow, as_index=False)[value_col_flow].sum()
    global_production = global_production.merge(
        global_population,
        left_on=time_col_flow,
        right_on=time_col_pop,
        suffixes=("_production", "_population"),
    )
    global_production[value_col_flow] = (
        global_production[f"{value_col_flow}_production"]
        / global_production[f"{value_col_pop}_population"]
        * 1e6
    )

    gdppc_with_population = gdppc.merge(
        population,
        left_on=[time_col_gdppc, region_col_gdppc],
        right_on=[time_col_pop, region_col_pop],
        suffixes=("_gdppc", "_population"),
    )
    gdppc_with_population["_weighted_gdppc"] = (
        gdppc_with_population[f"{value_col_gdppc}_gdppc"]
        * gdppc_with_population[f"{value_col_pop}_population"]
    )
    global_gdppc = (
        gdppc_with_population.groupby(time_col_gdppc, as_index=False)[
            ["_weighted_gdppc", f"{value_col_pop}_population"]
        ]
        .sum()
        .sort_values(time_col_gdppc)
    )
    global_gdppc[value_col_gdppc] = (
        global_gdppc["_weighted_gdppc"] / global_gdppc[f"{value_col_pop}_population"]
    )
    global_gdppc = global_gdppc[[time_col_gdppc, value_col_gdppc]]

    stock_pc = _attach_axis_values(
        stock_pc,
        gdppc,
        time_col_stock,
        region_col_stock,
        time_col_gdppc,
        region_col_gdppc,
        value_col_gdppc,
        "gdppc",
    )
    production_pc = _attach_axis_values(
        production_pc,
        gdppc,
        time_col_flow,
        region_col_flow,
        time_col_gdppc,
        region_col_gdppc,
        value_col_gdppc,
        "gdppc",
    )

    flow_total = flow.groupby(time_col_flow, as_index=False)[value_col_flow].sum()
    flow_gt = flow.copy()
    flow_gt[value_col_flow] = flow_gt[value_col_flow] / 1000
    flow_total_gt = flow_total.copy()
    flow_total_gt[value_col_flow] = flow_total_gt[value_col_flow] / 1000
    flow_gt = _attach_axis_values(
        flow_gt,
        gdppc,
        time_col_flow,
        region_col_flow,
        time_col_gdppc,
        region_col_gdppc,
        value_col_gdppc,
        "gdppc",
    )
    global_avg = _attach_axis_values(
        global_avg,
        global_gdppc,
        time_col_stock,
        None,
        time_col_gdppc,
        None,
        value_col_gdppc,
        "gdppc",
    )
    global_production = _attach_axis_values(
        global_production,
        global_gdppc,
        time_col_flow,
        None,
        time_col_gdppc,
        None,
        value_col_gdppc,
        "gdppc",
    )
    flow_total_gt = _attach_axis_values(
        flow_total_gt,
        global_gdppc,
        time_col_flow,
        None,
        time_col_gdppc,
        None,
        value_col_gdppc,
        "gdppc",
    )

    return {
        "config": config,
        "stock_pc": stock_pc,
        "production_pc": production_pc,
        "flow_gt": flow_gt,
        "global_avg": global_avg,
        "global_production": global_production,
        "flow_total_gt": flow_total_gt,
        "time_col_stock": time_col_stock,
        "region_col_stock": region_col_stock,
        "value_col_stock": value_col_stock,
        "time_col_flow": time_col_flow,
        "region_col_flow": region_col_flow,
        "value_col_flow": value_col_flow,
        "gdppc_col": "gdppc",
    }


def main(
    use_h12: bool = False,
    mfa_regions: str = "h12",
    show: bool = True,
    over_gdppc: bool = False,
):
    aggregate_regions = not use_h12
    run_configs = [get_material_config(material) for material in MATERIAL_ORDER]

    fig = make_subplots(
        rows=3,
        cols=len(run_configs),
        shared_xaxes=False,
        horizontal_spacing=0.08,
    )

    seen_regions = set()
    region_colors = {}
    x_axis_title = "GDP per capita" if over_gdppc else "Year"

    for col, config in enumerate(run_configs, start=1):
        run_data = _load_run_data(
            config, aggregate_regions=aggregate_regions, mfa_regions=mfa_regions
        )

        stock_regions = _utils.ordered_regions(
            run_data["stock_pc"][run_data["region_col_stock"]].unique(),
            reverse=True,
            aggregate_regions=aggregate_regions,
        )
        for region_code in stock_regions:
            region_df = run_data["stock_pc"][
                run_data["stock_pc"][run_data["region_col_stock"]] == region_code
            ].sort_values(
                run_data["gdppc_col"] if over_gdppc else run_data["time_col_stock"]
            )
            legend_label = _utils.get_region_label(region_code, aggregate_regions=aggregate_regions)
            show_legend = region_code not in seen_regions
            region_color = _get_region_color(
                region_code, region_colors, aggregate_regions=aggregate_regions
            )

            fig.add_trace(
                go.Scatter(
                    x=region_df[run_data["gdppc_col"] if over_gdppc else run_data["time_col_stock"]],
                    y=region_df[run_data["value_col_stock"]],
                    mode="lines",
                    name=_legend_name(legend_label, region_color),
                    legendgroup=region_code,
                    showlegend=show_legend,
                    line={"color": region_color, "width": LINE_WIDTH_DEFAULT},
                ),
                row=1,
                col=col,
            )
            seen_regions.add(region_code)

        fig.add_trace(
            go.Scatter(
                x=run_data["global_avg"][
                    run_data["gdppc_col"] if over_gdppc else run_data["time_col_stock"]
                ],
                y=run_data["global_avg"][run_data["value_col_stock"]],
                mode="lines",
                name=_legend_name("World", "black"),
                legendgroup="world",
                showlegend=(col == 1),
                line={"color": "black", "width": LINE_WIDTH_DEFAULT, "dash": "dot"},
            ),
            row=1,
            col=col,
        )

        production_regions = _utils.ordered_regions(
            run_data["production_pc"][run_data["region_col_flow"]].unique(),
            reverse=False,
            aggregate_regions=aggregate_regions,
        )
        for region_code in production_regions:
            region_df = run_data["production_pc"][
                run_data["production_pc"][run_data["region_col_flow"]] == region_code
            ].sort_values(run_data["gdppc_col"] if over_gdppc else run_data["time_col_flow"])
            legend_label = _utils.get_region_label(region_code, aggregate_regions=aggregate_regions)
            show_legend = region_code not in seen_regions
            region_color = _get_region_color(
                region_code, region_colors, aggregate_regions=aggregate_regions
            )

            fig.add_trace(
                go.Scatter(
                    x=region_df[run_data["gdppc_col"] if over_gdppc else run_data["time_col_flow"]],
                    y=region_df[run_data["value_col_flow"]],
                    mode="lines",
                    name=_legend_name(legend_label, region_color),
                    legendgroup=region_code,
                    showlegend=show_legend,
                    line={"color": region_color, "width": LINE_WIDTH_DEFAULT},
                ),
                row=2,
                col=col,
            )
            seen_regions.add(region_code)

        fig.add_trace(
            go.Scatter(
                x=run_data["global_production"][
                    run_data["gdppc_col"] if over_gdppc else run_data["time_col_flow"]
                ],
                y=run_data["global_production"][run_data["value_col_flow"]],
                mode="lines",
                name=_legend_name("World", "black"),
                legendgroup="world",
                showlegend=False,
                line={"color": "black", "width": LINE_WIDTH_DEFAULT, "dash": "dot"},
            ),
            row=2,
            col=col,
        )

        flow_regions = _utils.ordered_regions(
            run_data["flow_gt"][run_data["region_col_flow"]].unique(),
            reverse=True,
            aggregate_regions=aggregate_regions,
        )
        for region_code in flow_regions:
            region_df = run_data["flow_gt"][
                run_data["flow_gt"][run_data["region_col_flow"]] == region_code
            ].sort_values(run_data["gdppc_col"] if over_gdppc else run_data["time_col_flow"])
            legend_label = _utils.get_region_label(region_code, aggregate_regions=aggregate_regions)
            region_color = _get_region_color(
                region_code, region_colors, aggregate_regions=aggregate_regions
            )
            fig.add_trace(
                go.Scatter(
                    x=region_df[run_data["gdppc_col"] if over_gdppc else run_data["time_col_flow"]],
                    y=region_df[run_data["value_col_flow"]],
                    mode="lines",
                    name=legend_label,
                    legendgroup=region_code,
                    showlegend=False,
                    line={"color": region_color, "width": LINE_WIDTH_STACK},
                    stackgroup=None if over_gdppc else f"flow_col_{col}",
                    fillcolor=None if over_gdppc else region_color,
                ),
                row=3,
                col=col,
            )

        fig.add_trace(
            go.Scatter(
                x=run_data["flow_total_gt"][
                    run_data["gdppc_col"] if over_gdppc else run_data["time_col_flow"]
                ],
                y=run_data["flow_total_gt"][run_data["value_col_flow"]],
                mode="lines",
                name="World",
                legendgroup="world",
                showlegend=False,
                line={"color": "black", "width": LINE_WIDTH_DEFAULT, "dash": "dot"},
            ),
            row=3,
            col=col,
        )

        if not over_gdppc:
            for metric_row in range(1, 4):
                fig.add_vline(
                    x=config.last_historical_year,
                    line_dash="dash",
                    line_color="black",
                    line_width=LINE_WIDTH_VLINE,
                    row=metric_row,
                    col=col,
                )
        for metric_row in range(1, 4):
            fig.update_xaxes(
                title_text=x_axis_title,
                title_standoff=4,
                row=metric_row,
                col=col,
            )
            if not over_gdppc:
                fig.update_xaxes(range=[1950, 2100], row=metric_row, col=col)

    for col, config in enumerate(run_configs, start=1):
        col_domain = fig.get_subplot(1, col).xaxis.domain
        fig.add_annotation(
            x=(col_domain[0] + col_domain[1]) / 2,
            y=1.05,
            xref="paper",
            yref="paper",
            text=f"<b>{config.panel_label}</b>",
            showarrow=False,
            xanchor="center",
            font={"size": 16},
        )

    left_y_labels = [
        "<b>In-use stock per capita (t)</b>",
        "<b>Production per capita (t)</b>",
        "<b>Production (Gt)</b>",
    ]
    for row, label in enumerate(left_y_labels, start=1):
        row_domain = fig.get_subplot(row, 1).yaxis.domain
        fig.add_annotation(
            x=LEFT_Y_TITLE_X,
            xshift=LEFT_Y_TITLE_XSHIFT,
            y=(row_domain[0] + row_domain[1]) / 2,
            xref="paper",
            yref="paper",
            text=label,
            showarrow=False,
            textangle=-90,
            xanchor="right",
            yanchor="middle",
            font={"size": 16},
        )

    fig.update_layout(
        height=300 * len(run_configs) + 100,
        width=900 if aggregate_regions else 1050,
        template="plotly_white",
        legend={
            "orientation": "h",
            "x": 0.5,
            "xanchor": "center",
            "y": 1.08,
            "yanchor": "bottom",
            "font": {"size": LEGEND_FONT_SIZE},
            "bordercolor": "black",
            "borderwidth": 1,
        },
        margin={"t": 130, "b": 60, "l": 80, "r": 50},
    )

    country_suffix = "_countries" if mfa_regions == "iso249" else ""
    output_path = figure_output_path(
        f"figure_8_{_utils.region_mode_suffix(use_h12)}{country_suffix}_gdppc.png"
    )
    _write_png(fig, output_path)
    if show:
        fig.show()
    return fig


if __name__ == "__main__":
    main(use_h12=False, mfa_regions="h12", show=False, over_gdppc=True)
