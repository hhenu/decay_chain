"""
Functionality to fetch nuclide data from the IAEA API.
URL: nds.iaea.org/relnsd/v1/data?
See: https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html
"""

import requests

from typing import Optional
from requests import Response

# Some constants/config params
BASE_URL = "http://nds.iaea.org/relnsd/v1/data?"
DECAY_HEADERS = ["decay_%", "d_symbol", "d_n", "d_z",
                 "p_energy"]
NUC_HEADERS = ["z", "n", "symbol", "atomic_mass", "half_life_sec"]


def _send_request(url: str) -> Response:
    """
    :param url:
    :return:
    """
    res = None
    try:
        res = requests.get(url=url, timeout=10)
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error: {err}")
    except requests.exceptions.ConnectionError as err:
        print(f"Connection error: {err}")
    except requests.exceptions.Timeout as err:
        print(f"Request timed out: {err}")
    except requests.exceptions.RequestException as err:
        print(f"Request failed due to {err}")
    return res


def _parse_decay_data(res: str) -> dict:
    """
    :param res:
    :return:
    """
    # TODO: check if res.splitlines() works too
    lines = res.split("\n")
    headers, lines = lines[0].split(","), lines[1:]
    header_inds = {h: headers.index(h) for h in DECAY_HEADERS}
    data = None
    for line in lines:
        line = line.split(",")
        if len(line) < 2:  # Some lines might be just '\n'
            continue
        # Filter out radiations coming from metastable states
        if line[header_inds["p_energy"]] != "0":
            continue
        # TODO: Refactor this to a separate function
        # TODO: Make z and n return int instead of float
        data = {}
        for h in DECAY_HEADERS:
            if h == "p_energy":
                continue
            value = line[header_inds[h]]
            if value.isnumeric():
                value = int(value)
            try:
                value = float(value)
            except ValueError:
                pass
            data[h] = value
        break
    return data


def _parse_nuclide_data(res: str) -> dict:
    """
    :param res:
    :return:
    """
    res = res.splitlines()
    # The response might have a third empty line, hence we take only first two
    headers, dataline = res[0].split(","), res[1].split(",")
    header_inds = {h: headers.index(h) for h in NUC_HEADERS}
    data = {}
    for h in NUC_HEADERS:
        value = dataline[header_inds[h]]
        if value.isnumeric():
            value = int(value)
        try:
            value = float(value)
        except ValueError:
            pass
        data[h] = value
    return data


def _get_nuclide_data(nuc: str) -> Optional[dict]:
    """
    :param nuc:
    :return:
    """
    url = f"{BASE_URL}fields=ground_states&nuclides={nuc}"
    res = _send_request(url=url)
    # Check if the API returns just some error code
    if len(res.text.strip()) < 2:
        return None
    return _parse_nuclide_data(res=res.text)


def _get_decay_type_data(nuc: str, decay_type: str) -> Optional[dict]:
    """
    :param nuc:
    :param decay_type:
    :return:
    """
    url = f"{BASE_URL}fields=decay_rads&nuclides={nuc}&rad_types={decay_type}"
    res = _send_request(url=url)
    # Check if the API returns just some error code
    if len(res.text.strip()) < 2:
        return None
    return _parse_decay_data(res=res.text)


def _get_decay_data(nuc: str) -> list[dict]:
    """
    :param nuc:
    :return:
    """
    decay_types = ["a", "bm", "bp"]
    data = []
    for decay_type in decay_types:
        decay_data = _get_decay_type_data(nuc=nuc, decay_type=decay_type)
        if decay_data is None:
            continue
        data.append(decay_data)
    return data


def _fetch_from_csv(nuc: str, data: list[str]) -> dict:
    """
    :param nuc:
    :param data:
    :return:
    """


def get_data(nuc: str, csv_data: list[str] = None) -> dict:
    """
    :param nuc:
    :param csv_data:
    :return:
    """
    if csv_data is None:
        nuc_data = _get_nuclide_data(nuc=nuc)
        decays = _get_decay_data(nuc=nuc)
        nuc_data["decays"] = decays
        return nuc_data
    return _fetch_from_csv(nuc=nuc, data=csv_data)
