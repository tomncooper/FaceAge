import logging
import os
import sys
import time
import csv

from configparser import ConfigParser
from argparse import ArgumentParser, Namespace
from typing import Dict, Union, List, Optional

import requests

LOG: logging.Logger = logging.getLogger("FaceAge")

ALLOWED_TYPES: List[str] = ["jpg", "jpeg", "png", "gif", "bmp"]


def process_image(
    url: str, subscription_key: str, image_path: str
) -> Optional[Dict[str, Union[str, int, float]]]:

    headers: Dict[str, str] = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "content-type": "application/octet-stream",
    }

    params: Dict[str, str] = {
        "returnFaceId": "true",
        "returnFaceLandmarks": "false",
        "returnFaceAttributes": ("age,gender,emotion"),
    }

    try:
        with open(image_path, "rb") as image_file:
            result: requests.Response = requests.post(
                url, headers=headers, params=params, data=image_file
            )
            result.raise_for_status()
    except FileNotFoundError:
        LOG.error("Could not find file: %s", image_path)
        return None

    LOG.info("Processed image: %s", image_path)
    parsed_results: List[Dict[str, Union[str, int, float]]] = result.json()

    if not parsed_results:
        LOG.error("No data returned for image: %s", image_path)
        return None
    else:
        return parsed_results[0]


def get_image_list(image_directory: str) -> List[str]:

    LOG.info("Finding image files in directory: %s", image_directory)

    if not os.path.isdir(image_directory):
        err_msg: str = f"Supplied image directory: {image_directory} does not exist"
        LOG.error(err_msg)
        raise FileNotFoundError(err_msg)

    image_list: List[str] = []

    with os.scandir(image_directory) as dir_iter:
        for entry in dir_iter:
            if entry.is_file():
                ext: str = entry.name.split(".")[-1]
                if ext.lower() not in ALLOWED_TYPES:
                    LOG.warning(
                        "%s is not an allowed file type and will be " "ignored", ext
                    )
                else:
                    image_list.append(entry.path)
            else:
                LOG.warning("%s is not a file and will be ignored")

    if not image_list:
        LOG.warning("No image files found directory: %s")
    else:
        LOG.info(
            "Found %d image files in directory: %s", len(image_list), image_directory
        )

    return image_list


def process_image_directory(
    url: str, subscription_key: str, image_directory: str, sleep_secs: int = 5
) -> List[Dict[str, Union[str, float]]]:

    image_list: List[str] = get_image_list(image_directory)

    output: List[Dict[str, Union[str, float]]] = []

    for image_file in image_list:
        LOG.info("Processing image: %s", image_file)

        try:
            result: Optional[Dict[str, Union[str, float]]] = process_image(
                url, subscription_key, image_file
            )
        except requests.exceptions.RequestException as err:
            LOG.error("Request to API for image: % failed with error: %s", image_file, str(err))
            continue

        if not result:
            continue

        face_id: str = result["faceId"]

        row: Dict[str, Union[str, float]] = result["faceAttributes"]

        # Change the names of the emotion dict values to include the term
        # "emotion-" and be on the same level as all other values
        emotions: Dict[str, float] = {
            "emotion-" + k: v for k, v in row.pop("emotion").items()
        }

        row.update(emotions)

        row["faceId"] = face_id
        row["file"] = image_file.split("/")[-1]

        output.append(row)

        LOG.debug("Sleeping for %d seconds to stay inside rate limit", sleep_secs)
        time.sleep(sleep_secs)

    return output


def create_parser() -> ArgumentParser:

    parser: ArgumentParser = ArgumentParser(
        description=(
            "Script to process face images through the Microsoft "
            "Azure Cognitive Services Face detector API and obtain age "
            "ratings for each."
        )
    )

    parser.add_argument(
        "-c", "--config", required=True, help="File path to the configuration file."
    )

    parser.add_argument(
        "-i",
        "--image_dir",
        required=True,
        help="The file path to the directory of images to be processed.",
    )

    parser.add_argument(
        "-o",
        "--output_file",
        required=True,
        help="The file path to the output results file.",
    )

    parser.add_argument(
        "--debug",
        required=False,
        action="store_true",
        help="Optional flag indicating if debug information should be printed.",
    )

    return parser


def setup_log(logfile: str = None, debug: bool = False) -> logging.Logger:
    """ Sets up logging. By default this will pass the output to stdout however an
    optional output file can be specified to preserve the logs. The dubug argument will
    set the log level to DEBUG and will included line nubers and function name
    information in the log output.

    Arguments:
        logfile (str):  Optional path to the output file for logs.
        debug (bool):   Optional flag (default False) to include debug level
                        output.
    Returns:
        A logging.Logger instance configure for the top level of the system.
    """

    top_log: logging.Logger = logging.getLogger("FaceAge")

    if debug:
        top_log.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            (
                "{levelname} | {name} | "
                "function: {funcName} "
                "| line: {lineno} | {message}"
            ),
            style="{",
        )
    else:
        top_log.setLevel(logging.INFO)
        formatter = logging.Formatter(
            ("{asctime} | {name} | {levelname} " "| {message}"), style="{"
        )

    console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    top_log.addHandler(console_handler)

    if logfile:
        file_handler: logging.FileHandler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        top_log.addHandler(file_handler)

    return top_log


if __name__ == "__main__":

    PARSER: ArgumentParser = create_parser()
    ARGS: Namespace = PARSER.parse_args()

    CONFIG: ConfigParser = ConfigParser()
    CONFIG.read(ARGS.config)

    TOP_LOG: logging.Logger = setup_log(debug=ARGS.debug)

    if os.path.isfile(ARGS.output_file):
        TOP_LOG.error("Output file %s already exists")
        sys.exit(1)

    RESULTS: List[Dict[str, Union[str, float]]] = process_image_directory(
        CONFIG["Subscription"]["url"], CONFIG["Subscription"]["key"], ARGS.image_dir
    )

    with open(ARGS.output_file, "w") as csvfile:
        writer: csv.DictWriter = csv.DictWriter(
            csvfile, fieldnames=list(RESULTS[0].keys())
        )
        writer.writeheader()
        for result in RESULTS:
            writer.writerow(result)

    LOG.info("Results written to %s", ARGS.output_file)
