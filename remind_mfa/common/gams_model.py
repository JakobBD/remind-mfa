import gamspy as gp
import flodym as fd


class GAMSModel():

    def __init__(self):
        self.c = gp.Container()
        self.variables = {}

    def set_sets(self, dims: fd.DimensionSet):
        for dim in dims:
            self = self.c.addSet(
                name=dim.letter,
                description=dim.name,
                records=dim.items)

    def add_prm(self, array: fd.FlodymArray, name: str = None):
        if name is None:
            name = array.name
        self.variables[name] = array
        self.c.addParameter(
            name=name,
            domain=array.dims.letters,
            records=array.values,
        )

    def add_variable(self, array: fd.FlodymArray, name: str = None):
        if name is None:
            name = array.name
        self.c.addVariable(
            name=name,
            domain=array.dims.letters,
        )

    def add_equation(self, name: str, definition: gp.Expression = None):
        self.c.addEquation(
            name=name,
            definition=definition,
        )

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.c.getSymbols(name)

    def transfer_all_variables(self):
        for name in self.variables:
            self.transfer_variable(name)

    def transfer_variable(self, name: str):
        array = self.variables[name]
        var = self.c.getVariables(name)
        values_df = var.records
        array[...] = values_df # TODO
