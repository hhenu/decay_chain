"""
Program to track (or at least try to) the radioactive decay of some stuff. Given the
initial mass of radioactive material, calculates the nuclide concentrations of decay
products as a function of time.
"""

# TODO: Circular import error might happen if imports are in certain order

import decay
import nuclide
import logging
import graphviz
import numpy as np
import matplotlib.pyplot as plt

from typing import Callable
from data_fetching import DataHandler

logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s",
                    level=logging.INFO)


def visualize(chain: list[nuclide.Nuclide], title: str = "Decay chain",
              direc: str = "graphs", show: bool = True, print_out: bool = False) -> None:
    """
    :param chain:
    :param title:
    :param direc:
    :param show:
    :param print_out:
    :return:
    """
    dot = graphviz.Graph(title)
    for nuc in chain:
        dot.node(nuc.name)
        for daughter in nuc.daughters:
            dot.edge(nuc.name, daughter.name)

    if print_out:
        print(dot.source)
    dot.render(directory=direc, view=show)


def _get_daughters(decay_data: list[dict]) -> list[str]:
    """
    :param decay_data:
    :return:
    """
    logging.info(msg="Parsing daughter nuclides")
    daughters = []
    for dec in decay_data:
        sym = dec["d_symbol"]
        n = dec["d_n"]
        z = dec["d_z"]
        a = str(int(z) + int(n))
        name = sym + a
        daughters.append(name)
    logging.info(msg=f"Found daughter nuclides: {daughters}")
    return daughters


def get_nuclides(src_nuclides: dict,
                 data_handler: DataHandler) -> list[nuclide.Nuclide]:
    """
    :param src_nuclides:
    :param data_handler:
    :return:
    """
    stack = list(src_nuclides.keys())
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
        decays = nuc_data["decays"]
        if not halflife:
            halflife = None
        if nuc not in nuclide_dict.keys():
            m0 = src_nuclides.get(nuc, None)
            nuclide_objs[nuc] = nuclide.Nuclide(sym=sym, n=n, z=z, halflife=halflife,
                                                atom_mass=mass, m0=m0)
        nuclide_dict[nuc] = {"parents": set(), "daughters": set(), "decays": []}
        for daughter in _get_daughters(decay_data=decays):
            nuclide_dict[nuc]["daughters"].add(daughter)
            nuclide_dict[nuc]["decays"] = decays
            stack.append(daughter)

    # Fill the parent sets as well
    for parent, inner_dict in nuclide_dict.items():
        for daughter in inner_dict["daughters"]:
            nuclide_dict[daughter]["parents"].add(parent)

    nuclide_lst = []
    # Create a list of nuclides with info about parent nuclides, daughter nuclides,
    # and source terms
    for nuc, inner_dict in nuclide_dict.items():
        nuc_obj = nuclide_objs[nuc]
        for parent in inner_dict["parents"]:
            nuc_obj.add_parent(nuc=nuclide_objs[parent])
        for daughter, dec in zip(inner_dict["daughters"], inner_dict["decays"]):
            nuc_obj.add_daughter(nuc=nuclide_objs[daughter])
            d = decay.Decay(parent=nuc_obj, daughter=nuclide_objs[daughter],
                            lamda=nuc_obj.lamda, decay_ratio=dec["decay_%"] / 100)
            nuclide_objs[daughter].add_source(src=d)
        nuclide_lst.append(nuc_obj)

    return nuclide_lst


def _dsdt(nuclides: list[nuclide.Nuclide]) -> np.ndarray:
    """
    :param nuclides:
    :return:
    """
    dsdt = [nuc.source_term() - nuc.loss_term() for nuc in nuclides]
    return np.array(dsdt)


def _eulerfw(fun: Callable, nuclides: list[nuclide.Nuclide],
             tspan: np.ndarray) -> list[nuclide.Nuclide]:
    """
    :param fun:
    :param tspan:
    :return:
    """
    dt = tspan[1] - tspan[0]
    for i, _ in enumerate(tspan[1:], start=1):
        y_vals = dt * fun(nuclides=nuclides)
        for j, nuc in enumerate(nuclides):
            nuc.n += max(float(y_vals[j]), -nuc.n)
            nuc.n_arr.append(nuc.n)
    return nuclides


def solve(nuclides: list[nuclide.Nuclide], tspan: np.ndarray) -> list[nuclide.Nuclide]:
    """
    :param nuclides:
    :param tspan:
    :return:
    """
    return _eulerfw(fun=_dsdt, nuclides=nuclides, tspan=tspan)


def plot_results(nuclides: list[nuclide.Nuclide], tspan: np.ndarray,
                 logx: bool = False) -> None:
    """
    :param nuclides:
    :param tspan:
    :param logx:
    :return:
    """
    secs_min = 60
    secs_hr = secs_min * 60
    secs_day = secs_hr * 24
    secs_yr = secs_day * 365
    end = max(tspan)
    # Format the time a bit
    if end > secs_yr:
        unit = "years"
        tspan /= secs_yr
    elif secs_day < end <= secs_yr:
        unit = "days"
        tspan /= secs_day
    elif secs_hr < end <= secs_day:
        unit = "hours"
        tspan /= secs_hr
    elif secs_min < end <= secs_hr:
        unit = "minutes"
        tspan /= secs_min
    else:
        unit = "seconds"
    for nuc in nuclides:
        plt.plot(tspan[1:], nuc.n_arr, label=nuc.name)
    if logx:
        plt.semilogx()
    plt.legend()
    plt.xlabel(f"Time [{unit}]")
    plt.ylabel("N [-]")
    plt.grid()
    plt.show()


def main() -> None:
    # Initial setup
    src_nuclides = {"i131": 1, "cs137": 1}
    csv_path = "data/livechart.csv"
    data_handler = DataHandler(input_csv_path=csv_path)
    start, end = 0, 3600 * 24 * 365 * 100  # [s]
    dt = 10000  # [s]
    tspan = np.linspace(start, end, int((end - start) / dt) + 1)

    # Get all the nuclides (source and decay products)
    nuclides = get_nuclides(src_nuclides=src_nuclides, data_handler=data_handler)

    # Visualize the chain
    visualize(chain=nuclides, show=False)

    # Solve the concentrations
    nuclides = solve(nuclides=nuclides, tspan=tspan)

    # Plot results
    plot_results(nuclides=nuclides, tspan=tspan, logx=True)


if __name__ == "__main__":
    main()
