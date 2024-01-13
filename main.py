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


def get_nuclides(src_nuclide: str, data_handler: DataHandler) -> list[Nuclide]:
    """
    :param src_nuclide:
    :param data_handler:
    :return:
    """
    stack = [src_nuclide]
    nuclide_objs = {}
    nuclide_dict = {}
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
        if nuc not in nuclide_dict.keys():
            nuclide_objs[nuc] = Nuclide(sym=sym, n=n, z=z, halflife=halflife, atom_mass=mass)
            nuclide_dict[nuc] = {"parents": set(), "daughters": set()}
        for daughter in _get_daughters(nuc_data["decays"]):
            nuclide_dict[nuc]["daughters"].add(daughter)
            stack.append(daughter)

    # Fill the parent sets as well
    for parent, inner_dict in nuclide_dict.items():
        for daughter in inner_dict["daughters"]:
            nuclide_dict[daughter]["parents"].add(parent)

    nuclide_lst = []
    # Add the parents and daughters to the Nuclide objects
    for nuclide, inner_dict in nuclide_dict.items():
        for parent, daughter, in zip(inner_dict["parents"], inner_dict["daughters"]):
            nuclide_objs[nuclide].sources.append(nuclide_objs[daughter])
            nuclide_objs[nuclide].sinks.append(nuclide_objs[parent])
        nuclide_lst.append(nuclide_objs[nuclide])
    return nuclide_lst


def main() -> None:
    src_nuclide = "xe135"
    csv_path = "livechart.csv"
    data_handler = DataHandler(input_csv_path=csv_path)
    nuclides = get_nuclides(src_nuclide=src_nuclide, data_handler=data_handler)


if __name__ == "__main__":
    main()
