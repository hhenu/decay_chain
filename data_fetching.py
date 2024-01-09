"""
Functionality to fetch nuclide data from the IAEA API.
URL: nds.iaea.org/relnsd/v1/data?
See: https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html
"""

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


class DataHandler:
    def __init__(self, input_csv_path: str = None, output_csv_path: str = None,
                 delim: str = ",") -> None:
        """
        :param output_csv_path:
        :param input_csv_path:
        :param delim:
        """
        if output_csv_path is None:
            self.output_csv_path = "nuclide_data.csv"
        else:
            self.output_csv_path = output_csv_path
        if input_csv_path is None:
            self.data = self._fetch_from_api()
        else:
            self.data = self._read_csv(csv_path=input_csv_path)
        self.delim = delim

    def _fetch_from_api(self) -> list[str]:
        """
        :return:
        """
        logging.info(msg=f"No input csv path provided, fetching data from the API.")
        url = f"{BASE_URL}fields=ground_states&nuclides=all"
        res = _send_request(url=url)
        self._save_csv(data=res.text)
        return self._read_csv(csv_path=self.output_csv_path)

    @staticmethod
    def _convert_value(value: str) -> str | int | float:
        """
        Converts the given value to either int or float if possible, otherwise
        the value stays as a string
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

    @staticmethod
    def _read_csv(csv_path: str) -> list[str]:
        """
        :param csv_path:
        :return:
        """
        if not csv_path.endswith(".csv"):
            raise ValueError(f"Filepath must point to a csv file. Now got {csv_path}")
        logging.info(msg=f"Reading file {csv_path}")
        with open(csv_path, "r") as f:
            data = f.readlines()
        logging.info(msg=f"Done reading file {csv_path}")
        return data

    def _save_csv(self, data: str) -> None:
        """
        :param data:
        :return:
        """
        filepath = self.output_csv_path
        if not filepath.endswith(".csv"):
            raise ValueError(f"Filepath must point to a csv file. Now got "
                             f"{filepath}")
        logging.info(msg=f"Writing csv file {filepath}")
        with open(file=filepath, mode="w") as f:
            f.write(data)
        logging.info(msg=f"Generated csv file {filepath}")

    @staticmethod
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

    @staticmethod
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

    def _format_decays(self, data: dict, nuc: str) -> dict:
        """
        Formats the decay data retrieved from the csv file to maybe a bit more
        convenient form
        :param data:
        :param nuc:
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
                logging.info(msg=f"Unsupported decay mode {mode} for {nuc}, "
                                 f"ignoring it")
                continue
            sym, z, n = self._find_daughter(parent_z=data["z"],
                                            parent_n=data["n"], mode=mode)
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

    def _fetch_from_csv(self, nuc: str, delim: str = ",") -> dict:
        """
        :param nuc:
        :return:
        """
        logging.info(msg=f"Fetching data for {nuc} from the csv")
        sym_n, a_n = self._split_nuclide_name(nuc=nuc)
        headers, data = self.data[0].split(delim), self.data[3:]  # Skip neutrons
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
                data_dict[h] = self._convert_value(value=value)
            break
        else:
            # If the for loop finishes without breaking, we didn't find any data
            raise ValueError(f"No data found for nuclide {nuc}")
        data_dict = self._format_decays(data=data_dict, nuc=nuc)
        return data_dict

    def get_data(self, nuc: str,) -> dict:
        """
        :param nuc:
        :return:
        """
        return self._fetch_from_csv(nuc=nuc)
