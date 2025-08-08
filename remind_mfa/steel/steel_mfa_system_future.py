import flodym as fd
import numpy as np
from enum import Enum

from remind_mfa.common.trade import TradeSet
from remind_mfa.common.trade_extrapolation import extrapolate_trade
from remind_mfa.common.price_driven_trade import PriceDrivenTrade
from remind_mfa.common.common_mfa_system import CommonMFASystem



class SteelMFASystem(CommonMFASystem):

    def compute(self, stock: fd.FlodymArray, historic_trade: TradeSet):
        """
        Perform all computations for the MFA system.
        """
        # TODO: delete post-production

        for name, trade in self.trade_set.markets.items():
            process = trade.process
            process.historic_trade = historic_trade.markets[name]

        self.stocks["in_use"].stock[...] = stock
        self.stocks["in_use"].lifetime_model.set_prms(
            mean=self.parameters["lifetime_mean"],
            std=self.parameters["lifetime_std"],
        )

        self.compute_all_possible()

        total_production = (
            self.flows["post_production => forming"] / self.parameters["production_yield"]
        )

        self.flows["post_scrap_market => excess_scrap"][...] = (
            self.flows["scrap_market => post_scrap_market"]
            - (
                total_production
                * self.parameters["max_scrap_share_base_model"]
            )
        ).maximum(
            0.
        )

        total_scrap = (
            self.flows["scrap_market => post_scrap_market"]
            - self.flows["post_scrap_market => excess_scrap"]
        )

        self.flows["bof_production => post_production"][...] = (
            total_production
        ).minimum(
            (total_production - total_scrap)
            / (1. - self.parameters["scrap_in_bof_rate"])
        )

        self.compute_all_possible()

    def compute_price_elastic_trade(self):
        price = fd.FlodymArray(dims=self.dims["t", "r"])
        price[...] = 500.0
        # price.values[131:201,2] = np.minimum(800., np.linspace(500, 2000, 70))
        model = PriceDrivenTrade(dims=self.trade_set["intermediate"].exports.dims)
        model.calibrate(
            demand=self.flows["ip_market => fabrication"][2022],
            price=price[2022],
            imports_target=self.trade_set["intermediate"].imports[2022],
            exports_target=self.trade_set["intermediate"].exports[2022],
        )
        price, demand, supply, imports, exports = model.compute_price_driven_trade(
            price_0=price,
            demand_0=self.flows["ip_market => fabrication"],
            supply_0=self.flows["forming => ip_market"],
        )

        self.flows["ip_market => fabrication"][...] = demand
        self.flows["forming => ip_market"][...] = supply
        self.trade_set["intermediate"].imports[...] = imports
        self.trade_set["intermediate"].exports[...] = exports
        self.trade_set["intermediate"].balance()

        self.flows["imports => ip_market"][...] = self.trade_set["intermediate"].imports
        self.flows["ip_market => exports"][...] = self.trade_set["intermediate"].exports
