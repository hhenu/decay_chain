"""
File for a Nuclide object
"""

import numpy as np

# Some constants
N_A = 6.02214076e23  # Avogadro constant [1/mol] (from wikipedia)
LN2 = np.log(2)


class Nuclide:
    def __init__(self, sym: str, z: str, n: str, m0: int | float, halflife: int | float) -> None:
        """
        :param sym: The name/symbol of the element e.g. H, He, C, etc.
        :param z: The amount of protons in the nuclide
        :param n: The amount of neutrons in the nuclide
        :param m0: Initial mass [kg]
        :param halflife: Half life of the nuclide [s]
        """
        self.sym = sym.lower()
        self.z = z
        self.n = n
        self.a = str(int(z) + int(n))
        self.name = self.sym + self.a
        self.m = m0
        self.mol_mass = int(self.a)  # Assume that mass number == molar mass
        self.halflife = halflife
        self.lamda = LN2 / halflife  # Decay constant [1/s]

    def n0(self) -> float:
        """
        The number of nuclides at the start
        :return:
        """
        return N_A * self.m / self.mol_mass
