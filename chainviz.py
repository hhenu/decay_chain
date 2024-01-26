"""
Functionality to visualize the decay chain using graph viz
"""

import nuclide
import graphviz


def visualize(chain: list[nuclide.Nuclide]) -> None:
    """
    :param chain:
    :return:
    """
    dot = graphviz.Graph("Decay chain")
    for nuc in chain:
        dot.node(nuc.name)
        for daughter in nuc.daughters:
            dot.edge(nuc.name, daughter.name)

    print(dot.source)
    dot.render(directory="graphs", view=True)
