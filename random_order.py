#!/usr/bin/env python3

import argparse
import json
import random
import statistics
import sys

import utility
import trueskill
from ts_ranking import ts_ratings
from rating_stats import ratings_order_error, ts_order
from wl_ranking import wl_bt_ratings, wl_pl_ratings

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Test ratings from randomly ordered game data.")
    parser.add_argument("game_files", nargs="+",
            help="Json files containing game data.")
    parser.add_argument("-t", "--test-games", action="append",
            help="Json files containing game data to test ratings against.")
    parser.add_argument("-n", "--num-trials", type=int, default=100,
            help="Number of trials to run.")
    config = parser.parse_args(args)

    games = utility.load_games(config.game_files)
    game_results = [{"%s (%s)" % (u['username'], u['userID']): int(u['rank'])
        for u in g['users']}
            for g in games]

    if len(config.test_games) > 0:
        test_games = utility.load_games(config.test_games)
        test_results = [{"%s (%s)" % (u['username'], u['userID']): int(u['rank'])
            for u in g['users']}
                for g in test_games]
    else:
        test_games = list(games)

    rating_errors = list()
    for i in range(config.num_trials):
        random.shuffle(game_results)
        #ratings = ts_ratings(game_results)
        ratings = wl_pl_ratings(game_results)

        ordering_ratio = ratings_order_error(test_results, ratings, ts_order)
        rating_errors.append(ordering_ratio)

        error_avg = statistics.mean(rating_errors)
        error_min = min(rating_errors)
        error_max = max(rating_errors)
        if i != 0:
            error_stdev = statistics.stdev(rating_errors)
        else:
            error_stdev = 0
        print("%d: %.2f%% Min: %.2f%% Avg: %.2f%% (%.2f%%) Max: %.2f%%" % (
            i+1, ordering_ratio*100, error_min*100, error_avg*100,
            error_stdev*100, error_max*100))

if __name__ == "__main__":
    main()
