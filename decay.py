"""
File for a decay object, meant to represent a radioactive decay event or some shit
"""

import nuclide


class Decay:
    def __init__(self, parent: nuclide.Nuclide, daughter: nuclide.Nuclide,
                 lamda: int | float, decay_ratio: float) -> None:
        """
        :param parent:
        :param daughter:
        :param lamda:
        :param decay_ratio:
        """
        self.parent = parent
        self.daughter = daughter
        self.lamda = lamda
        if not (0 <= decay_ratio <= 1):
            raise ValueError(f"decay_ratio must be between 0 and 1, now got {decay_ratio}.")
        self.decay_ratio = decay_ratio
        self.lamda_eff = lamda * decay_ratio  # "Effective" decay coefficient [1/s]

    def calculate(self) -> int | float:
        """
        :return:
        """
        return self.lamda_eff * self.parent.n

    def __repr__(self) -> str:
        """
        :return:
        """
        return f"{self.__class__.__name__}({self.parent} -> {self.daughter})"

    def __str__(self) -> str:
        """
        :return:
        """
        return self.__repr__()
