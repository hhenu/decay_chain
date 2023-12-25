"""
Functionality to fetch nuclide data from the IAEA API.
URL: nds.iaea.org/relnsd/v1/data?
See: https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html
"""

import requests

from typing import Optional


BASE_URL = "http://nds.iaea.org/relnsd/v1/data?"
HEADERS = ["half_life_sec", "decay_%", "d_symbol", "d_n", "d_z",
           "p_energy"]


def _parse_response(res: str) -> dict:
    """
    :param res:
    :return:
    """
    lines = res.split("\n")
    headers, lines = lines[0].split(","), lines[1:]
    header_inds = {h: headers.index(h) for h in HEADERS}
    data = None
    for line in lines:
        line = line.split(",")
        if len(line) < 2:  # Some lines might be just '\n'
            continue
        # Filter out radiations coming from metastable states
        if line[header_inds["p_energy"]] != "0":
            continue
        # We need just one result for the half life and stuff
        data = {
            "half_life_sec": float(line[header_inds["half_life_sec"]]),
            "decay_%": float(line[header_inds["decay_%"]]),
            "d_symbol": line[header_inds["d_symbol"]],
            "d_n": line[header_inds["d_n"]],
            "d_z": line[header_inds["d_z"]],
        }
        break
    return data


def _get_decay_type_data(nuc: str, decay_type: str) -> Optional[dict]:
    """
    :param nuc:
    :param decay_type:
    :return:
    """
    url = f"{BASE_URL}fields=decay_rads&nuclides={nuc}&rad_types={decay_type}"
    res = requests.get(url=url)
    if res.status_code != 200:
        msg = f"Sending the request failed with status code {res.status_code}"
        raise ConnectionError(msg)
    # Check if the API returns just some error code
    if len(res.text.strip()) < 2:
        return None
    return _parse_response(res=res.text)


def get_data(nuc: str) -> Optional[dict]:
    """
    :param nuc:
    :return:
    """
    decay_types = ["a", "bm", "bp"]
    data = {}
    for decay_type in decay_types:
        decay_data = _get_decay_type_data(nuc=nuc, decay_type=decay_type)
        if decay_data is None:
            continue
        data[decay_type] = decay_data
    return data
