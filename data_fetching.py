"""
Functionality to fetch nuclide data from the IAEA API.
URL: nds.iaea.org/relnsd/v1/data?
See: https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html
"""

import os
import logging
import requests

from nuc_table import fetch
from requests import Response

# Some constants/config params
BASE_URL = "http://nds.iaea.org/relnsd/v1/data?"
CSV_HEADERS = ["z", "n", "symbol", "atomic_mass", "half_life_sec", "decay_1",
               "decay_1_%", "decay_2", "decay_2_%", "decay_3", "decay_3_%"]

# Currently upported decay types
CSV_DECAY_MODES = ["a", "b-", "ec+b+"]  # These are used in the csv file


def _send_request(url: str) -> Response:
    """
    Sends a get request to the specified url
    :param url:
    :return:
    """
    logging.info(msg=f"Sending request to {url}")
    res = None
    try:
        res = requests.get(url=url, timeout=10)
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(msg=f"HTTP error: {err}")
    except requests.exceptions.ConnectionError as err:
        logging.error(msg=f"Connection error: {err}")
    except requests.exceptions.Timeout as err:
        logging.error(msg=f"Request timed out: {err}")
    except requests.exceptions.RequestException as err:
        logging.error(msg=f"Request failed due to {err}")
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


def _save_csv(data: str, filepath: str) -> None:
    """
    :param data:
    :param filepath:
    :return:
    """
    if not filepath.endswith(".csv"):
        raise ValueError(f"Filepath must point to a csv file. Now got {filepath}")
    logging.info(msg=f"Writing csv file {filepath}")
    with open(file=filepath, mode="w") as f:
        f.write(data)
    logging.info(msg=f"Generated csv file {filepath}")


def _read_csv(filepath: str) -> list[str]:
    """
    :param filepath:
    :return:
    """
    if not filepath.endswith(".csv"):
        raise ValueError(f"Filepath must point to a csv file. Now got {filepath}")
    logging.info(msg=f"Reading file {filepath}")
    with open(filepath, "r") as f:
        data = f.readlines()
    logging.info(msg=f"Done reading file {filepath}")
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
    Formats the decay data retrieved from the csv file to maybe a bit more
    convenient form
    :param data:
    :return:
    """
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
            logging.info(msg=f"Unsupported decay mode {mode}, ignoring it for now.")
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
    logging.info(msg=f"Fetching data for {nuc} from the csv")
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


def get_data(nuc: str, csv_path: str = None, delim: str = ",") -> dict:
    """
    :param nuc:
    :param csv_path:
    :param delim:
    :return:
    """
    if csv_path is None:
        output_path = "nuclide_data.csv"
        if not os.path.exists(path=output_path):
            logging.info(msg=f"No csv path provided, fetching data from the API.")
            url = f"{BASE_URL}fields=ground_states&nuclides=all"
            res = _send_request(url=url)
            _save_csv(data=res.text, filepath=output_path)
        else:
            logging.info(msg=f"csv file already created, no need to send the request again.")
        csv_path = output_path
    csv_data = _read_csv(filepath=csv_path)
    return _fetch_from_csv(nuc=nuc, data=csv_data, delim=delim)
