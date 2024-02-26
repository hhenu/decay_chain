"""
File for a Nuclide object
"""

from __future__ import annotations

import decay
import numpy as np

# Some constants
N_A = 6.02214076e23  # Avogadro constant [1/mol] (from wikipedia)
LN2 = np.log(2)


class Nuclide:
    def __init__(self, sym: str, z: str, n: str, atom_mass: int | float,
                 halflife: int | float = None, m0: int | float = None) -> None:
        """
        :param sym: The name/symbol of the element e.g. H, He, C, etc.
        :param z: The amount of protons in the nuclide
        :param n: The amount of neutrons in the nuclide
        :param halflife: Half life of the nuclide [s]
        :param atom_mass: Atomic mass [amu] == g/mol
        :param m0: Initial mass [kg] (optional). This should only be given for
        the source nuclide(s) as an initial condition of sorts.
        """
        self.sym = sym.lower()
        self.z = z
        self.n = n
        self.a = str(z + n)
        self.name = self.sym + self.a
        self.atomic_mass = atom_mass
        self.halflife = halflife
        if halflife is not None:
            self.lamda = LN2 / halflife  # Decay constant [1/s]
        else:
            self.lamda = 0
        self.m0 = m0
        if self.m0 is not None:
            self.n = self.calc_n0()
        else:
            self.n = 0
        self.parents = []
        self.daughters = []
        self._sources = []
        self.n_arr = []

    def calc_n0(self) -> float:
        """
        The number of nuclides at the start
        :return:
        """
        return N_A * self.m0 / self.atomic_mass

    def add_parent(self, nuc: Nuclide) -> None:
        """
        :param nuc:
        :return:
        """
        self.parents.append(nuc)

    def add_daughter(self, nuc: Nuclide) -> None:
        """
        :param nuc:
        :return:
        """
        self.daughters.append(nuc)

    def add_source(self, src: decay.Decay) -> None:
        """
        :param src:
        :return:
        """
        self._sources.append(src)

    def source_term(self) -> float:
        """
        :return:
        """
        return sum(dec.calculate() for dec in self._sources)

    def loss_term(self) -> float:
        """
        :return:
        """
        return self.lamda * self.n

    def __eq__(self, other: Nuclide) -> bool:
        """
        :param other:
        :return:
        """
        return self.name == other.name

    def __repr__(self) -> str:
        """
        :return:
        """
        return f"{self.__class__.__name__}({self.name})"

    def __str__(self) -> str:
        """
        :return:
        """
        return self.__repr__()
