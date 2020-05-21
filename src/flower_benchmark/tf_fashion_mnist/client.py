# Copyright 2020 Adap GmbH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Flower client using TensorFlow for Fashion-MNIST image classification."""


import argparse
from logging import ERROR

import tensorflow as tf

import flower as flwr
from flower.logger import configure, log
from flower_benchmark.common import VisionClassificationClient, load_partition
from flower_benchmark.dataset import tf_fashion_mnist_partitioned
from flower_benchmark.model import orig_cnn
from flower_benchmark.tf_fashion_mnist.settings import SETTINGS, get_setting

from . import DEFAULT_SERVER_ADDRESS, SEED

tf.get_logger().setLevel("ERROR")


def parse_args() -> argparse.Namespace:
    """Parse and return commandline arguments."""
    parser = argparse.ArgumentParser(description="Flower")
    parser.add_argument(
        "--server_address",
        type=str,
        default=DEFAULT_SERVER_ADDRESS,
        help=f"Server address (IPv6, default: {DEFAULT_SERVER_ADDRESS})",
    )
    parser.add_argument(
        "--log_host", type=str, help="HTTP log handler host (no default)",
    )
    parser.add_argument(
        "--setting", type=str, choices=SETTINGS.keys(), help="Setting to run.",
    )
    parser.add_argument(
        "--index", type=int, required=True, help="Client index in settings."
    )
    return parser.parse_args()


def main() -> None:
    """Load data, create and start Fashion-MNIST client."""
    args = parse_args()

    client_setting = get_setting(args.setting).clients[args.index]

    # Configure logger
    configure(identifier=f"client:{client_setting.cid}", host=args.log_host)

    # Load model
    model = orig_cnn(input_shape=(28, 28, 1), seed=SEED)

    # Load local data partition
    xy_partitions, xy_test = tf_fashion_mnist_partitioned.load_data(
        iid_fraction=client_setting.iid_fraction,
        num_partitions=client_setting.num_clients,
    )
    xy_train, xy_test = load_partition(
        xy_partitions,
        xy_test,
        partition=client_setting.partition,
        num_clients=client_setting.num_clients,
        dry_run=client_setting.dry_run,
        seed=SEED,
    )

    # Start client
    client = VisionClassificationClient(
        client_setting.cid, model, xy_train, xy_test, client_setting.delay_factor, 10
    )
    flwr.app.start_client(args.server_address, client)


if __name__ == "__main__":
    # pylint: disable=broad-except
    try:
        main()
    except Exception as err:
        log(ERROR, "Fatal error in main")
        log(ERROR, err, exc_info=True, stack_info=True)

        # Raise the error again so the exit code is correct
        raise err