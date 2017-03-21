#!/usr/bin/env python3

import argparse
import json
import os
import statistics
import sys
from collections import defaultdict

import trueskill

import utility
from pl_ranking import plackett_luce
from ts_ranking import ts_ratings
from wl_ranking import wl_bt_ratings, wl_pl_ratings

def pl_rate(game_results):
    return plackett_luce(game_results, tolerance=1e-09)

def ts_rate(game_results):
    return ts_ratings(game_results)

def ts_t0_rate(game_results):
    stau = trueskill.global_env().tau
    trueskill.global_env().tau = 0
    ratings = ts_ratings(game_results)
    trueskill.global_env().tau = stau
    return ratings

def wl_bt_rate(game_results):
    return wl_bt_ratings(game_results)

def wl_pl_rate(game_results):
    return wl_pl_ratings(game_results)

def rank_order(ratings, a, b):
    return ratings[a] > ratings[b]

def ms_rank_order(ratings, a, b):
    ar = ratings[a]
    br = ratings[b]
    return (ar.mu - (ar.sigma * 3)) > (br.mu - (br.sigma * 3))

def check_predictions(test_results, ratings, order):
    num_wrong = 0
    num_predictions = 0
    for game in test_results:
        gameranks = sorted(game.items(), key=lambda x: x[1])
        for pix, (player, prank) in enumerate(gameranks[:-1]):
            for opp, orank in gameranks[pix+1:]:
                better = order(ratings, player, opp)
                worse = order(ratings, opp, player)
                if (better == worse) or (better != (prank < orank)):
                    num_wrong += 1
                num_predictions += 1
    return num_wrong / num_predictions

def load_parts(game_dir):
    parts = list()
    for gfile in os.listdir(game_dir):
        if not gfile.endswith(".json"):
            continue
        gpath = os.path.join(game_dir, gfile)
        parts.append(utility.load_games([gpath]))

    max_part = max(len(p) for p in parts)
    min_part = min(len(p) for p in parts)
    if max_part - min_part > 1:
        print("WARNING: Partition size varies by %d games," % (max_part - min_part))
    num_games = sum(len(p) for p in parts)
    print("Loaded %d games in %d parts" % (num_games, len(parts)))
    return parts

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Cross validate ratings on a set of partitioned games.")
    parser.add_argument("game_dir",
            help="Directory containing game files.")
    config = parser.parse_args(args)

    game_parts = load_parts(config.game_dir)

    systems = [
            ("plackett-luce", {
                "rate": pl_rate,
                "order": rank_order,
                }),
            ("trueskill-default", {
                "rate": ts_rate,
                "order": ms_rank_order,
                }),
            ("trueskill-t0", {
                "rate": ts_t0_rate,
                "order": ms_rank_order,
                }),
            ("weng-lin-bt", {
                "rate": wl_bt_rate,
                "order": ms_rank_order,
                }),
            ("weng-lin-pl", {
                "rate": wl_pl_rate,
                "order": ms_rank_order,
                }),
            ]

    error_rates = defaultdict(list)
    for pnum, test in enumerate(game_parts, start=1):
        test_results = [{"%s (%s)" % (u['username'], u['userID']): int(u['rank'])
            for u in g['users']} for g in test]
        train = [g for p in game_parts if p != test for g in p]
        train.sort(key=lambda x: x['gameID'])
        train_results = [{"%s (%s)" % (u['username'], u['userID']): int(u['rank'])
            for u in g['users']} for g in train]
        for system, funcs in systems:
            ratings = funcs['rate'](train_results)
            error_rates[system].append(
                    check_predictions(test_results, ratings, funcs['order']))
            print("Finished %d parts for %-17s %.2f error" % (
                pnum, system, error_rates[system][-1] * 100))
    for system, funcs in systems:
        error = statistics.mean(error_rates[system])
        error_sd = statistics.stdev(error_rates[system])
        print("Prediction error for %-17s %.2f%% (%.2f%%)" % (
            system, error * 100, error_sd * 100))

if __name__ == "__main__":
    main()
