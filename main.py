"""
Program to track (or at least try to) the radioactive decay of some stuff. Given the
initial mass of radioactive material, calculates the nuclide concentrations of decay
products as a function of time.
"""

import logging

from nuclide import Nuclide
from data_fetching import DataHandler

logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s",
                    level=logging.DEBUG)


def _get_daughters(decay_data: list[dict]) -> list:
    """
    :param decay_data:
    :return:
    """
    logging.info(msg=f"Parsing daughter nuclides")
    daughters = []
    for decay in decay_data:
        sym = decay["d_symbol"]
        n = decay["d_n"]
        z = decay["d_z"]
        a = str(int(z) + int(n))
        name = sym + a
        daughters.append(name)
    logging.info(msg=f"Found daughter nuclides: {daughters}")
    return daughters


def get_nuclides(src_nuclei: str, data_handler: DataHandler) -> None:
    """
    :param src_nuclei:
    :param data_handler:
    :return:
    """
    stack = [src_nuclei]
    nuclides = []
    while stack:
        nuc = stack.pop()
        logging.info(msg=f"Found nuclide: {nuc}")
        nuc_data = data_handler.get_data(nuc=nuc)
        sym = nuc_data["symbol"]
        n = nuc_data["n"]
        z = nuc_data["z"]
        mass = nuc_data["atomic_mass"]
        halflife = nuc_data["half_life_sec"]
        if not halflife:
            halflife = None
        nuclides.append(Nuclide(sym=sym, n=n, z=z, halflife=halflife, atom_mass=mass))
        for daughter in _get_daughters(nuc_data["decays"]):
            stack.append(daughter)


def main() -> None:
    src_nuclei = "u238"
    csv_path = "livechart.csv"
    data_handler = DataHandler(input_csv_path=csv_path)
    get_nuclides(src_nuclei=src_nuclei, data_handler=data_handler)


if __name__ == "__main__":
    main()
