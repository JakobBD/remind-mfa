from remind_mfa.steel.steel_mfa_system_future import SteelMFASystem
from remind_mfa.common.gams_model import GAMSModel


def build_gams_model(mfa: SteelMFASystem):

    g = GAMSModel()
    g.set_sets(mfa.dims)
    declare_variables(mfa, g)
    declare_parameters(g)
    define_equations(g)

def declare_variables(mfa: SteelMFASystem, g: GAMSModel):
    g.add_variable(mfa.flows[""], name="v_demand")

def declare_parameters(g: GAMSModel):
    pass

def define_equations(g: GAMSModel):
    net_utility(g)
    demand_utility(g)
    supply_cost(g)

def net_utility(g: GAMSModel):
    g.add_equation(
        name="q_net_utility",
        definition= g.v_net_utility == g.v_demand_utility - g.v_supply_cost - g.v_trade_net_cost
    )

def demand_utility(g: GAMSModel):
    """Integral over inverse demand function: U = ∫ p(q) dq
    p goes to infinity for q -> 0, so we omit the lower bound.
    Absolute value of utility is not important, only marginal utility.
    """
    g.p_eta_demand = - 0.3
    g.p_theta_demand = (g.p_eta_demand + 1) / g.p_eta_demand
    g.add_equation(
        name="q_demand_utility",
        definition= g.v_demand_utility == (1 / g.p_theta_demand) * g.v_demand ** g.p_theta_demand
    )

def supply_cost(g: GAMSModel):
    """= price_prim * quantity_prim + cost_sec
    """

def cost_sec(g: GAMSModel):
    """= price_recl * quantity_sec + cost_scrap
    """

def price_recl(g: GAMSModel):
    """= f(max_scrap_share)
    """
    # Pre trade seems more like the better choice, as we don't track prim/sec for trade.
    # Open problem: Turkey exports lots of secondary steel.
    # Unless we track the quality of the traded steel, the equation fails both if we define the sec share for supply or demand, i.e. pre or post trade.

def max_scrap_share(g: GAMSModel):
    """quantity_sec <= max_scrap_share * (quantity_prim+quantity_sec)
    """

def raw_trade_net_cost(g: GAMSModel):
    """= import_price * imports - export_price * exports
    """

def cost_scrap(g: GAMSModel):
    """= price_recov * quantity_scrap + scrap_trade_net_cost
    """

def price_recov(g: GAMSModel):
    """= f(recov_rate)
    """

def recov(g: GAMSModel):
    """= quantity_scrap = quantity_eol * recov_rate
    """

def scrap_trade_net_cost(g: GAMSModel):
    """= import_price * imports - export_price * exports
    """

def raw_trade_balance(g: GAMSModel):
    """Sum(r, imports) = Sum(r, exports)
    """

def scrap_trade_balance(g: GAMSModel):
    """Sum(r, imports) = Sum(r, exports)
    """

def trade_pool(g: GAMSModel):
    """imports = total_demand - domestic_supply
    exports = total_supply - domestic_demand
    """

def rho(sigma):
    return (sigma - 1) / sigma


"""
TRADE

local_supply_cost = ...
local_supply = quan_domestic + exports

U_pool = CES(quan_supply(r))
U_demand = CES(quan_import, quan_domestic)

price_demand = U_demand / (quan_import + quan_domestic)

"""