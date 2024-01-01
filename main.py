"""
Program to track (or at least try to) the radioactive decay of some stuff. Given the
initial mass of radioactive material, calculates the nuclide concentrations of decay
products as a function of time.
"""

import logging

from nuclide import Nuclide
from data_fetching import get_data

logging.basicConfig(level=logging.DEBUG)


def _read_csv(filepath: str) -> list[str]:
    """
    :param filepath:
    :return:
    """
    if not filepath.endswith(".csv"):
        raise ValueError("File seems to not be a csv file")
    logging.info(msg=f"Reading file {filepath}")
    with open(filepath, "r") as f:
        data = f.readlines()
    logging.info(msg=f"Done reading file {filepath}")
    return data


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


def get_nuclides(src_nuclei: str, csv_path: str = None, delim: str = ",") -> None:
    """
    :param src_nuclei:
    :param csv_path:
    :param delim:
    :return:
    """
    if csv_path is not None:
        csv_data = _read_csv(filepath=csv_path)
    else:
        csv_data = None
    stack = [src_nuclei]
    nuclides = []
    while stack:
        nuc = stack.pop()
        logging.info(msg=f"Current nuclide: {nuc}")
        nuc_data = get_data(nuc=nuc, csv_data=csv_data, delim=delim)
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
    src_nuclei = "xe135"
    csv_path = "livechart.csv"
    get_nuclides(src_nuclei=src_nuclei, csv_path=None)


if __name__ == "__main__":
    main()
