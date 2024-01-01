"""
Functionality to fetch nuclide data from the IAEA API.
URL: nds.iaea.org/relnsd/v1/data?
See: https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html
"""

import requests

from nuc_table import fetch
from typing import Optional
from requests import Response

# Some constants/config params
BASE_URL = "http://nds.iaea.org/relnsd/v1/data?"

DECAY_HEADERS = ["decay_%", "d_symbol", "d_n", "d_z",
                 "p_energy"]
NUC_HEADERS = ["z", "n", "symbol", "atomic_mass", "half_life_sec"]
CSV_HEADERS = ["z", "n", "symbol", "atomic_mass", "half_life_sec", "decay_1", "decay_1_%", "decay_2",
               "decay_2_%", "decay_3", "decay_3_%"]

# Currently upported decay types
CSV_DECAY_MODES = ["a", "b-", "ec+b+"]  # These are used in the csv file
API_DECAY_MODES = ["a", "bm", "bp"]  # These are used by the decay_rads API


def _send_request(url: str) -> Response:
    """
    Sends a get request to the specified url
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


def _parse_value_type(value: str) -> str | int | float:
    """
    Converts the given value to either to int or float
    :param value:
    :return:
    """
    # Try to create a float
    try:
        value = float(value)
    except ValueError:
        pass
    # See if the value is now a float and whether the decimal part is zero
    try:
        if value.is_integer():
            value = int(value)
    except AttributeError:
        pass
    return value


def _parse_decay_data(res: str) -> dict:
    """
    Parses decay data from the response
    :param res:
    :return:
    """
    lines = res.splitlines()
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
        data = {}
        for h in DECAY_HEADERS:
            if h == "p_energy":
                continue
            value = line[header_inds[h]]
            data[h] = _parse_value_type(value=value)
        break
    return data


def _parse_nuclide_data(res: str) -> dict:
    """
    Parses nuclide data from the response
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
        data[h] = _parse_value_type(value=value)
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
    Gets data for the specified decay type
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
    data = []
    for decay_type in API_DECAY_MODES:
        decay_data = _get_decay_type_data(nuc=nuc, decay_type=decay_type)
        if decay_data is None:
            continue
        data.append(decay_data)
    return data


def _split_nuclide_name(nuc: str) -> tuple[str, str]:
    """
    Splits the nuclide name to symbol and mass number, e.g.
    he4 -> (he, 4)
    :param nuc:
    :return:
    """
    sym, a = "", ""
    for ch in nuc:
        if not (ch.isnumeric() or ch == "-"):
            sym += ch
        else:
            a += ch

    return sym, a


def _find_daughter(parent_z: str, parent_n: str, mode: str) -> tuple[str, str, str]:
    """
    :param parent_z:
    :param parent_n:
    :param mode:
    :return:
    """
    # Alpha decay
    if mode == "a":
        z = str(int(parent_z) - 2)
        n = str(int(parent_n) - 2)
        return fetch(z=z), z, n
    # Beta minus decay
    elif mode == "b-":
        z = str(int(parent_z) + 1)
        n = str(int(parent_n) - 1)
        return fetch(z=z), z, n
    # Beta plus decay (electron capture + proton emission)
    elif mode == "ec+b+":
        z = str(int(parent_z) - 1)
        n = str(int(parent_n) + 1)
        return fetch(z=z), z, n
    raise NotImplementedError(f"Unknown decay mode ({mode}) detected.")


def _format_decays(data: dict) -> dict:
    """
    Formats the decay data retrieved from the csv file to the same format that
    the decay_rads API endpoint returns
    :param data:
    :return:
    """
    # [{'decay_%': 35.94, 'd_symbol': 'Tl', 'd_n': 127.0, 'd_z': 81.0},
    #  {'decay_%': 64.06, 'd_symbol': 'Po', 'd_n': 128.0, 'd_z': 84.0}]
    headers_to_keep = ["z", "n", "symbol", "atomic_mass", "half_life_sec"]
    decays = []
    for i in range(1, 4):
        mode_header = f"decay_{i}"
        percentage_header = f"decay_{i}_%"
        if not data[mode_header] or not data[percentage_header]:
            break
        mode = data[mode_header].lower()
        percentage = data[percentage_header]
        if mode not in CSV_DECAY_MODES:
            print(f"Unsupported decay mode {mode}, ignoring it for now.")
            continue
        sym, z, n = _find_daughter(parent_z=data["z"], parent_n=data["n"], mode=mode)
        decays.append({"decay_%": percentage,
                       "d_symbol": sym,
                       "d_n": n,
                       "d_z": z})

    new_data = {}
    for k, v in data.items():
        if k in headers_to_keep:
            new_data[k] = data[k]

    new_data["decays"] = decays
    return new_data


def _fetch_from_csv(nuc: str, data: list[str], delim: str = ",") -> dict:
    """
    :param nuc:
    :param data:
    :return:
    """
    sym_n, a_n = _split_nuclide_name(nuc=nuc)
    headers, data = data[0].split(delim), data[3:]
    # Find the row of the correct nuclide
    header_inds = {h: headers.index(h) for h in CSV_HEADERS}
    data_dict = {}
    for line in data[:-1]:  # To skip the empty last line
        line = line.strip().split(delim)
        z = line[header_inds["z"]]
        n = line[header_inds["n"]]
        sym = line[header_inds["symbol"]]
        a = str(int(z) + int(n))
        if not (a == a_n and sym.lower() == sym_n):
            continue
        for h in CSV_HEADERS:
            value = line[header_inds[h]]
            data_dict[h] = _parse_value_type(value=value)
        break
    else:
        # If the for loop finishes without breaking, we didn't find any data
        raise ValueError(f"No data found for nuclide {nuc}")
    data_dict = _format_decays(data=data_dict)
    return data_dict


def get_data(nuc: str, csv_data: list[str] = None, delim: str = ",") -> dict:
    """
    :param nuc:
    :param csv_data:
    :param delim:
    :return:
    """
    if csv_data is None:
        nuc_data = _get_nuclide_data(nuc=nuc)
        decays = _get_decay_data(nuc=nuc)
        nuc_data["decays"] = decays
        return nuc_data
    return _fetch_from_csv(nuc=nuc, data=csv_data, delim=delim)
