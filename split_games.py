#!/usr/bin/env python3

import argparse
import json
import random
import sys

from utility import load_games

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Split games into separate training and test sets.")
    parser.add_argument("game_files", nargs="+",
            help="Json files containing game data.")
    parser.add_argument("-n", "--num-games", type=int,
            help="Limit the number of games used (positive for first, negative for last")
    parser.add_argument("-o", "--out-file", required=True,
            help="Name of the output files will be test-<name>.json and training-<name>.json.")
    parser.add_argument("-p", "--test-percentage", type=float, default=10,
            help="Percentage of games to use for testing. (Default 10%)")
    config = parser.parse_args(args)

    games = load_games(config.game_files)
    test_size = int(len(games) * (config.test_percentage / 100))
    test_ix = set(random.sample(range(len(games)), test_size))
    training_games = list()
    test_games = list()
    for gix, game in enumerate(games):
        if gix in test_ix:
            test_games.append(game)
        else:
            training_games.append(game)
    print("%d training and %d test games selected." % (len(training_games),
        len(test_games)))
    with open("training-%s.json" % (config.out_file,), 'w') as trfile:
        json.dump(training_games, trfile)
    with open("test-%s.json" % (config.out_file,), 'w') as testfile:
        json.dump(test_games, testfile)

if __name__ == "__main__":
    main()
