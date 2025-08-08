from typing import List
import flodym as fd

from remind_mfa.common.common_cfg import GeneralCfg
from remind_mfa.common.trade import TradeDefinition


class SteelMFADefinition(fd.MFADefinition):
    trades: List[TradeDefinition]


def get_definition(cfg: GeneralCfg, historic: bool, from_historic: bool) -> SteelMFADefinition:
    dimensions = [
        fd.DimensionDefinition(name="Time", dim_letter="t", dtype=int),
        fd.DimensionDefinition(name="Region", dim_letter="r", dtype=str),
        fd.DimensionDefinition(name="Intermediate", dim_letter="i", dtype=str),
        fd.DimensionDefinition(name="Good", dim_letter="g", dtype=str),
        fd.DimensionDefinition(name="Scenario", dim_letter="s", dtype=str),
    ]
    if historic or from_historic:
        dimensions += [
            fd.DimensionDefinition(name="Historic Time", dim_letter="h", dtype=int),
        ]

    if historic:
        processes = [
            "sysenv",
            "forming",
            "ip_market",
            "good_market",
            "fabrication",
            "use",
        ]
    else:
        processes = [
            fd.ProcessDefinition(id=0, name="sysenv",),
            fd.ProcessDefinition(id=1, name="bof_production", outflow_shares={"post_production": "production_yield"}),
            fd.ProcessDefinition(id=2, name="eaf_production", outflow_shares={"post_production": "production_yield"}),
            fd.ProcessDefinition(id=3, name="post_production"),
            fd.ProcessDefinition(id=4, name="forming", outflow_shares={"ip_supply": "forming_yield", "losses": "forming_losses"}),
            fd.ProcessDefinition(id=5, name="ip_trade",),
            fd.ProcessDefinition(id=6, name="ip_demand",),
            fd.ProcessDefinition(id=7, name="ip_supply",),
            fd.ProcessDefinition(id=8, name="fabrication", outflow_shares={"good_supply": "fabrication_yield", "losses": "fabrication_losses"}),
            fd.ProcessDefinition(id=9, name="good_trade",),
            fd.ProcessDefinition(id=10, name="good_demand",),
            fd.ProcessDefinition(id=11, name="good_supply",),
            fd.ProcessDefinition(id=12, name="use", outflow_shares={"eol_supply": "recovery_rate"}),
            fd.ProcessDefinition(id=13, name="obsolete",),
            fd.ProcessDefinition(id=14, name="eol_trade",),
            fd.ProcessDefinition(id=15, name="eol_demand",),
            fd.ProcessDefinition(id=16, name="eol_supply",),
            fd.ProcessDefinition(id=17, name="recycling",),
            fd.ProcessDefinition(id=18, name="scrap_market",),
            fd.ProcessDefinition(id=19, name="post_scrap_market",),
            fd.ProcessDefinition(id=20, name="excess_scrap",),
            fd.ProcessDefinition(id=21, name="losses",),
            fd.ProcessDefinition(id=22, name="extraction",),
        ]

    # fmt: off
    if historic:
        flows = [
            fd.FlowDefinition(from_process="sysenv", to_process="forming", dim_letters=("h", "r")),
            fd.FlowDefinition(from_process="forming", to_process="ip_market", dim_letters=("h", "r")),
            fd.FlowDefinition(from_process="forming", to_process="sysenv", dim_letters=("h", "r")),
            fd.FlowDefinition(from_process="ip_market", to_process="fabrication", dim_letters=("h", "r")),
            fd.FlowDefinition(from_process="ip_market", to_process="sysenv", dim_letters=("h", "r")),
            fd.FlowDefinition(from_process="sysenv", to_process="ip_market", dim_letters=("h", "r")),
            fd.FlowDefinition(from_process="fabrication", to_process="good_market", dim_letters=("h", "r", "g")),
            fd.FlowDefinition(from_process="fabrication", to_process="sysenv", dim_letters=("h", "r")),
            fd.FlowDefinition(from_process="good_market", to_process="sysenv", dim_letters=("h", "r", "g")),
            fd.FlowDefinition(from_process="sysenv", to_process="good_market", dim_letters=("h", "r", "g")),
            fd.FlowDefinition(from_process="good_market", to_process="use", dim_letters=("h", "r", "g")),
            fd.FlowDefinition(from_process="use", to_process="sysenv", dim_letters=("h", "r", "g")),
        ]
    else:
        flows = [
            fd.FlowDefinition(from_process="extraction", to_process="bof_production", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="bof_production", to_process="post_production", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="scrap_market", to_process="post_scrap_market", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="post_production", to_process="forming", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="bof_production", to_process="losses", dim_letters=("t", "r",)),
            fd.FlowDefinition(from_process="scrap_market", to_process="post_scrap_market", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="post_scrap_market", to_process="eaf_production", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="post_scrap_market", to_process="bof_production", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="eaf_production", to_process="post_production", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="eaf_production", to_process="losses", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="forming", to_process="ip_supply", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="forming", to_process="scrap_market", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="forming", to_process="losses", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="ip_supply", to_process="ip_trade", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="ip_trade", to_process="ip_demand", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="ip_supply", to_process="ip_demand", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="ip_demand", to_process="fabrication", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="fabrication", to_process="scrap_market", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="fabrication", to_process="losses", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="fabrication", to_process="good_supply", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="good_supply", to_process="good_trade", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="good_trade", to_process="good_demand", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="good_supply", to_process="good_demand", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="good_demand", to_process="use", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="use", to_process="obsolete", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="use", to_process="eol_supply", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="eol_supply", to_process="eol_trade", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="eol_trade", to_process="eol_demand", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="eol_supply", to_process="eol_demand", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="eol_demand", to_process="recycling", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="recycling", to_process="scrap_market", dim_letters=("t", "r", "g")),
            fd.FlowDefinition(from_process="post_scrap_market", to_process="excess_scrap", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="sysenv", to_process="ip_trade", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="ip_trade", to_process="sysenv", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="sysenv", to_process="good_trade", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="good_trade", to_process="sysenv", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="sysenv", to_process="eol_trade", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="eol_trade", to_process="sysenv", dim_letters=("t", "r")),
            fd.FlowDefinition(from_process="losses", to_process="sysenv", dim_letters=("t", "r",)),
            fd.FlowDefinition(from_process="sysenv", to_process="extraction", dim_letters=("t", "r")),
        ]
    # fmt: on

    if historic:
        stocks = [
            fd.StockDefinition(
                name="historic_in_use",
                process="use",
                dim_letters=("h", "r", "g"),
                subclass=fd.InflowDrivenDSM,
                lifetime_model_class=cfg.customization.lifetime_model,
                time_letter="h",
            ),
        ]
    else:
        stocks = [
            fd.StockDefinition(
                name="in_use",
                process="use",
                dim_letters=("t", "r", "g"),
                subclass=fd.FlexibleDSM,
                lifetime_model_class=cfg.customization.lifetime_model,
            ),
            fd.StockDefinition(
                name="obsolete",
                process="obsolete",
                dim_letters=("t", "r", "g"),
                subclass=fd.SimpleFlowDrivenStock,
            ),
            fd.StockDefinition(
                name="excess_scrap",
                process="excess_scrap",
                dim_letters=("t", "r"),
                subclass=fd.SimpleFlowDrivenStock,
            ),
        ]

    parameters = [
        fd.ParameterDefinition(name="forming_yield", dim_letters=("i",)),
        fd.ParameterDefinition(name="fabrication_yield", dim_letters=("g",)),
        fd.ParameterDefinition(name="recovery_rate", dim_letters=("g",)),
        fd.ParameterDefinition(name="good_to_intermediate_distribution", dim_letters=("g", "i")),
        fd.ParameterDefinition(name="population", dim_letters=("t", "r")),
        fd.ParameterDefinition(name="gdppc", dim_letters=("t", "r")),
        fd.ParameterDefinition(name="lifetime_mean", dim_letters=("r", "g")),
        fd.ParameterDefinition(name="lifetime_std", dim_letters=("r", "g")),
        fd.ParameterDefinition(name="sector_split_low", dim_letters=("g",)),
        fd.ParameterDefinition(name="sector_split_medium", dim_letters=("g",)),
        fd.ParameterDefinition(name="sector_split_high", dim_letters=("g",)),
        fd.ParameterDefinition(name="secsplit_gdppc_low", dim_letters=()),
        fd.ParameterDefinition(name="secsplit_gdppc_high", dim_letters=()),
        fd.ParameterDefinition(name="max_scrap_share_base_model", dim_letters=()),
        fd.ParameterDefinition(name="scrap_in_bof_rate", dim_letters=()),
        fd.ParameterDefinition(name="production_yield", dim_letters=()),
        fd.ParameterDefinition(name="saturation_level_factor", dim_letters=("r",)),
        fd.ParameterDefinition(name="stock_growth_speed_factor", dim_letters=("r",)),
    ]
    if historic or from_historic:
        parameters += [
            fd.ParameterDefinition(name="scrap_consumption", dim_letters=("h", "r")),
            # WSA
            fd.ParameterDefinition(name="production_by_intermediate", dim_letters=("h", "r", "i")),
            fd.ParameterDefinition(name="intermediate_imports", dim_letters=("h", "r", "i")),
            fd.ParameterDefinition(name="intermediate_exports", dim_letters=("h", "r", "i")),
            fd.ParameterDefinition(name="indirect_imports", dim_letters=("h", "r", "g")),
            fd.ParameterDefinition(name="indirect_exports", dim_letters=("h", "r", "g")),
            fd.ParameterDefinition(name="scrap_imports", dim_letters=("h", "r")),
            fd.ParameterDefinition(name="scrap_exports", dim_letters=("h", "r")),
            fd.ParameterDefinition(name="forming_losses", dim_letters=()),
            fd.ParameterDefinition(name="fabrication_losses", dim_letters=()),
        ]
    else:
        parameters += [
            fd.ParameterDefinition(name="in_use_inflow", dim_letters=("t", "r", "g")),
            fd.ParameterDefinition(name="intermediate_imports", dim_letters=("t", "r")),
            fd.ParameterDefinition(name="intermediate_exports", dim_letters=("t", "r")),
            fd.ParameterDefinition(name="indirect_imports", dim_letters=("t", "r", "g")),
            fd.ParameterDefinition(name="indirect_exports", dim_letters=("t", "r", "g")),
            fd.ParameterDefinition(name="scrap_imports", dim_letters=("t", "r", "g")),
            fd.ParameterDefinition(name="scrap_exports", dim_letters=("t", "r", "g")),
            fd.ParameterDefinition(name="fixed_in_use_outflow", dim_letters=("t", "r", "g")),
        ]

    # currently unused
    # fd.ParameterDefinition(name="external_copper_rate", dim_letters=("g",)),
    # fd.ParameterDefinition(name="cu_tolerances", dim_letters=("i",)),
    # fd.ParameterDefinition(name="production", dim_letters=("h", "r")),
    # fd.ParameterDefinition(name="pigiron_production", dim_letters=("h", "r")),
    # fd.ParameterDefinition(name="pigiron_imports", dim_letters=("h", "r")),
    # fd.ParameterDefinition(name="pigiron_exports", dim_letters=("h", "r")),
    # fd.ParameterDefinition(name="pigiron_to_cast", dim_letters=("h", "r")),
    # fd.ParameterDefinition(name="dri_production", dim_letters=("h", "r")),
    # fd.ParameterDefinition(name="dri_imports", dim_letters=("h", "r")),
    # fd.ParameterDefinition(name="dri_exports", dim_letters=("h", "r")),

    if historic:
        trades = [
            TradeDefinition(name="intermediate", dim_letters=("h", "r")),
            TradeDefinition(name="indirect", dim_letters=("h", "r", "g")),
            TradeDefinition(name="scrap", dim_letters=("h", "r")),
        ]
    else:
        trades = [
            TradeDefinition(name="intermediate", dim_letters=("t", "r"), process="ip_trade", connectors=["ip_supply", "ip_demand"]),
            TradeDefinition(name="indirect", dim_letters=("t", "r", "g"), process="good_trade", connectors=["good_supply", "good_demand"]),
            TradeDefinition(name="scrap", dim_letters=("t", "r", "g"), process="eol_trade", connectors=["eol_supply", "eol_demand"]),
        ]

    return SteelMFADefinition(
        dimensions=dimensions,
        processes=processes,
        flows=flows,
        stocks=stocks,
        parameters=parameters,
        trades=trades,
    )
