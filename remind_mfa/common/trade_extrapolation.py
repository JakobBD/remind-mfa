import numpy as np
import flodym as fd
from typing import Optional
import logging

from remind_mfa.common.data_extrapolations import ProportionalExtrapolation
from remind_mfa.common.data_transformations import broadcast_trailing_dimensions
from remind_mfa.common.trade import Trade


def extrapolate_trade(
    historic_trade: Trade,
    future_trade: Trade,
    future_supply: fd.FlodymArray = None,
    future_demand: fd.FlodymArray = None,
):
    """Predict future trade values by extrapolating the trade data using a given scaler.

    Args:
        historic_trade (Trade): Historic trade data.
        future_trade (Trade): Future trade data, which is written to.
        future_supply (FlodymArray): The supply values to scale the historic exports by.
            In this forward mode, the imports are scaled subsequently by supply + exports.
        future_demand (FlodymArray): The demand values to scale the historic imports by.
            In this backward mode, the exports are scaled subsequently by demand - imports.
    """

    # prepare prediction
    assert (future_supply is None) != (future_demand is None), "Exactly one of scale_imports_by or scale_exports_by must be set."
    assert (
        "h" in historic_trade.imports.dims.letters and "h" in historic_trade.exports.dims.letters
    ), "Trade data must have a historic time dimension."

    if future_supply is not None:
        scaler_first = future_supply
        scaled_first = "exports"
        scaled_second = "imports"
    else:
        scaler_first = future_demand
        scaled_first = "imports"
        scaled_second = "exports"

    historic_first = getattr(historic_trade, scaled_first)
    historic_second = getattr(historic_trade, scaled_second)
    future_first = getattr(future_trade, scaled_first)
    future_second = getattr(future_trade, scaled_second)
    # TODO: make sure future_trade dims are a subset of the union of the dims of the scaler and the historic trade

    missing_dims = scaler_first.dims.difference_with(historic_trade.imports.dims).letters[1:]

    if len(missing_dims) > 0:
        with np.errstate(divide="ignore"):
            historic_first *= (
                scaler_first[{"t": historic_first.dims["h"]}]
                .get_shares_over(missing_dims)
                .apply(np.nan_to_num)
            )
            historic_second *= (
                scaler_first[{"t": historic_second.dims["h"]}]
                .get_shares_over(missing_dims)
                .apply(np.nan_to_num)
            )

    future_first[...] = extrapolate_to_future(historic=historic_first, scale_by=scaler_first)
    future_second[...] = 0.0

    # TODO: Ensure share < 1 already in extrapolation?
    scaler_second = (scaler_first + future_trade.net_imports).maximum(0)
    future_second[...] = extrapolate_to_future(historic=historic_second, scale_by=scaler_second)

    future_trade.balance(to="hmean")

    future_first[...] = future_first.minimum(scaler_first)
    future_trade.balance(to="minimum")


def extrapolate_to_future(historic: fd.FlodymArray, scale_by: fd.FlodymArray) -> fd.FlodymArray:
    """Uses the WeightedProportionalExtrapolation, basically a linear regression
    so that the share of the historic trade in the scaler is kept constant
    """
    if not historic.dims.letters[0] == "h":
        raise ValueError("First dimension of historic_parameter must be historic time.")
    if not scale_by.dims.letters[0] == "t":
        raise ValueError("First dimension of scaler must be time.")
    if not set(scale_by.dims.letters[1:]).issubset(historic.dims.letters[1:]):
        raise ValueError("Scaler dimensions must be subset of historic_parameter dimensions.")

    all_dims = historic.dims.union_with(scale_by.dims)
    dim_letters_out = ("t",) + historic.dims.letters[1:]
    dims_out = all_dims[dim_letters_out]

    scale_by = scale_by.cast_to(dims_out)

    # calculate weights
    n_hist_points = historic.dims.shape[0]
    n_last_points = 5
    weights_1d = np.maximum(0.0, np.arange(-n_hist_points, 0) + n_last_points + 1)
    weights_1d = weights_1d / weights_1d.sum()
    weights = broadcast_trailing_dimensions(weights_1d, historic.values)

    extrapolation = ProportionalExtrapolation(
        data_to_extrapolate=historic.values,
        predictor_values=scale_by.values,
        weights=weights,
        independent_dims=tuple(range(1, dims_out.ndim)),
    )
    extrapolated = fd.FlodymArray(dims=dims_out, values=extrapolation.extrapolate()).maximum(0.0)
    last_historic = historic[historic.dims["h"].items[-1]].maximum(0.0).cast_to(dims_out)
    alpha_rel = 0.5
    alpha_abs = 1 - alpha_rel
    projected = last_historic**alpha_abs * extrapolated**alpha_rel
    projected[{"t": historic.dims["h"]}] = historic

    return projected

class CommonProcess(fd.Process):
    """
    A Process that has a trade module associated with it.
    This is used to handle processes that involve trade flows.
    """

    trade: Optional[Trade] = None
    historic_trade: Optional[Trade] = None
    connected_trade_process: Optional['CommonProcess'] = None

    def try_compute(self):
        if self.trade is not None:
            self.compute_trade()
        elif self.connected_trade_process is not None:
            self.connected_trade_process.compute_trade()
            super().try_compute()
        else:
            super().try_compute()

    def compute_trade(self):
        self.check_connections()

        domestic_demand = next(iter(self.get_demand_connector().outflows.values()))
        domestic_supply = next(iter(self.get_supply_connector().inflows.values()))
        if domestic_demand.is_set:
            future_demand = domestic_demand
            future_supply = None
        elif domestic_supply.is_set:
            future_supply = domestic_supply
            future_demand = None
        else:
            raise fd.UnderdeterminedError(self,
                message = f"Neither domestic demand nor domestic supply are set for {self.name}. "
                "Trade extrapolation will not be performed."
            )

        extrapolate_trade(
            historic_trade=self.historic_trade,
            future_trade=self.trade,
            future_demand=future_demand,
            future_supply=future_supply,
        )

        self.outflows[self.get_demand_connector().name][...] = self.trade.imports
        self.inflows[self.get_supply_connector().name][...] = self.trade.exports

        self.outflows["sysenv"][...] = self.trade.exports
        self.inflows["sysenv"][...] = self.trade.imports

    def get_supply_connector(self):
        """Returns the inflow connector, which is a TradeConnector."""
        for inflow in self.inflows.values():
            if inflow.from_process.connected_trade_process is self:
                return inflow.from_process

    def get_demand_connector(self):
        """Returns the outflow connector, which is a TradeConnector."""
        for outflow in self.outflows.values():
            if outflow.to_process.connected_trade_process is self:
                return outflow.to_process

    def check_connections(self):
        """Check whether trade and trade connectors are properly set up."""
        if self.trade is None or self.historic_trade is None:
            raise ValueError("ProcessWithTrade must have a trade and historic_trade set.")
        if len(self.inflows) != 2 or len(self.outflows) != 2:
            raise ValueError("ProcessWithTrade must have exactly two inflows and two outflows.")
        if not self.get_supply_connector() or not self.get_demand_connector():
            print(self.name)
            print("Supply connector:", self.get_supply_connector())
            print("Demand connector:", self.get_demand_connector())
            raise ValueError("ProcessWithTrade must be connected to TradeConnectors.")
        if "sysenv" not in self.inflows or "sysenv" not in self.outflows:
            raise ValueError("ProcessWithTrade must have sysenv inflow and outflow.")
        if len(self.get_supply_connector().inflows) != 1 or len(self.get_supply_connector().outflows) != 2:
            raise ValueError("Export TradeConnector must have exactly one inflow and two outflows")
        if len(self.get_demand_connector().outflows) != 1 or len(self.get_demand_connector().inflows) != 2:
            raise ValueError("Import TradeConnector must have exactly one outflow and two inflows")
        if self.shares("in") or self.shares("out"):
            raise ValueError("ProcessWithTrade cannot handle shares.")
        if self.get_supply_connector().shares("in") or self.get_supply_connector().shares("out") or self.get_demand_connector().shares("in") or self.get_demand_connector().shares("out"):
            raise ValueError("Trade connectors must not have shares.")
        if self.get_demand_connector().name not in self.get_supply_connector().outflows:
            raise ValueError("Trade connectors must be connected to each other for domestic flows")
