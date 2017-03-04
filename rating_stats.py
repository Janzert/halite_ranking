#!/usr/bin/env python3

import argparse
import json
import math
import sys
from collections import defaultdict

import trueskill
import matplotlib.pyplot as plot
import utility

def phi(x):
    """Cumulative distribution function for the standard normal distribution
    Taken from python math module documentation"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def ts_winp(a, b, env=None):
    """Win probability of player a over b given their trueskill ratings.
    Formula found at https://github.com/sublee/trueskill/issues/1#issuecomment-244699989"""
    if not env:
        env = trueskill.global_env()
    epsilon = trueskill.calc_draw_margin(env.draw_probability, 2)
    denom = math.sqrt(a.sigma**2 + b.sigma**2 + (2 * env.beta**2))
    return phi((a.mu - b.mu - epsilon) / denom)

def wl_winp(a, b):
    ciq = math.sqrt(a.sigma**2 + b.sigma**2 + (2 * (25/6)**2))
    return 1 / (1 + math.exp((b.mu - a.mu) / ciq))

def pl_winp(a, b):
    """Win probability of player a over b given their PL ratings."""
    return a / (a + b)

def ratings_rmse(game_results, ratings, winp_func, subjects=None):
    sum_errors = 0
    num_missed = 0
    num_predictions = 0
    for game in game_results:
        gameranks = sorted(game.items(), key=lambda x: x[1])
        for pix, (player, prank) in enumerate(gameranks[:-1]):
            for opp, orank in gameranks[pix+1:]:
                if subjects and player not in subjects and opp not in subjects:
                    continue
                if player not in ratings or opp not in ratings:
                    num_missed += 1
                    continue
                winp = winp_func(ratings[player], ratings[opp])
                winr = 1 if prank < orank else 0
                sum_errors += (winp - winr)**2
                num_predictions += 1
    if num_missed:
        print("Could not make a prediction for %d pairs." % (
            num_missed,))
        print("With %d predictions made." % (num_predictions,))
    return math.sqrt(sum_errors / num_predictions)

def ts_order(a, b):
    return (a.mu - (a.sigma * 3)) > (b.mu - (b.sigma * 3))

def pl_order(a, b):
    return a > b

def ratings_order_error(game_results, ratings, rank_order, subjects=None):
    num_wrong = 0
    num_missed = 0
    num_predictions = 0
    for game in game_results:
        gameranks = sorted(game.items(), key=lambda x: x[1])
        for pix, (player, prank) in enumerate(gameranks[:-1]):
            for opp, orank in gameranks[pix+1:]:
                if subjects and player not in subjects and opp not in subjects:
                    continue
                if player not in ratings or opp not in ratings:
                    num_missed += 1
                    continue
                better = rank_order(ratings[player], ratings[opp])
                worse = rank_order(ratings[opp], ratings[player])
                # if player rating is indecisive, count as wrong prediction
                # see Weng and Lin 2011 Section 6
                if (better == worse) or (better != (prank < orank)):
                    num_wrong += 1
                num_predictions += 1
    if num_missed:
        print("Could not make a prediction for %d pairs." % (
            num_missed,))
        print("With %d predictions made." % (num_predictions,))
    return num_wrong / num_predictions

def best_scores(game_results):
    player_wins = defaultdict(lambda: defaultdict(int))
    for game in game_results:
        for player, prank in game.items():
            for opp, orank in game.items():
                if player == opp:
                    continue
                if prank < orank:
                    player_wins[player][opp] += 1
    ratings = {p: p for g in game_results for p in g}

    def pwin(a, b):
        if player_wins[a][b] == 0:
            return 0
        if player_wins[b][a] == 0:
            return 1
        return player_wins[a][b] / (player_wins[a][b] + player_wins[b][a])

    def rank_order(a, b):
        return player_wins[a][b] > player_wins[b][a]

    rmse = ratings_rmse(game_results, ratings, pwin)
    print("True probability RMSE %f" % (rmse,))
    order_ratio = ratings_order_error(game_results, ratings, rank_order)
    print("True probability incorrectly ordered %f%% results" % (order_ratio * 100,))

def load_ts_ratings(filename):
    ratings = dict()
    with open(filename) as rfile:
        for line in rfile:
            rank, player, score, mu, sigma = line.split(",")
            rating = trueskill.Rating(mu=float(mu), sigma=float(sigma))
            ratings[player.strip()] = rating
    return ratings

def load_pl_ratings(filename):
    ratings = dict()
    with open(filename) as rfile:
        for line in rfile:
            rank, player, rating = line.split(",")
            ratings[player.strip()] = float(rating)
    return ratings

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Gather various performance statistics from ratings.")
    parser.add_argument("game_files", nargs="+",
            help="Json files containing game data.")
    parser.add_argument("-n", "--num-games", type=int,
            help="Limit the number of games used (positive for first, negative for last")
    parser.add_argument("--remove-suspect", action="store_true",
            help="Filter out suspect games based on workerID.")
    parser.add_argument("--no-error", action="store_true",
            help="Filter out games that had bot errors.")
    parser.add_argument("-r", "--ratings", required=True,
            help="File with ratings of players.")
    parser.add_argument("--subjects",
            help="File with players to include.")
    parser.add_argument("--subjects-num", type=int,
            help="Only use first n subjects.")
    parser.add_argument("--calc-best", action="store_true",
            help="Calculate best possible rates using true win percentages.")
    parser.add_argument("--type", choices=["ts", "wl"],
            help="Type of ratings, ts=trueskill or wl=Weng-Lin.")
    config = parser.parse_args(args)

    with open(config.ratings) as rfile:
        line = rfile.readline()
        fnum = len(line.split(","))
        if fnum == 3:
            load_ratings = load_pl_ratings
            winp = pl_winp
            rank_order = pl_order
            print("Detected plackett-luce ratings.")
        elif fnum == 5:
            load_ratings = load_ts_ratings
            if not config.type:
                print("Rating type not given, use --type argument.")
                return
            if config.type == "ts":
                winp = ts_winp
                rank_order = ts_order
                print("Detected trueskill ratings.")
            elif config.type == "wl":
                winp = wl_winp
                rank_order = ts_order
                print("Detected Weng-Lin ratings.")

    ratings = load_ratings(config.ratings)
    print("Loaded ratings for %d players." % (len(ratings)))

    if config.subjects:
        with open(config.subjects) as sfile:
            slines = sfile.readlines()
            if len(slines[0].split(",")) > 1:
                slines = [l.split(",")[1] for l in slines]
            if config.subjects_num:
                if config.subjects_num > 0:
                    slines = slines[:config.subjects_num]
                else:
                    slines = slines[config.subjects_num:]
            subjects = frozenset(l.strip() for l in slines)
            print("Restricting stats to %d players" % (len(subjects),))
    else:
        subjects = None

    games = utility.load_games(config.game_files)
    if config.no_error:
        games = utility.filter_error_games(games)
        print("Filtered out error games, leaving %d" % (len(games),))
    if config.remove_suspect:
        start_num = len(games)
        games = utility.filter_suspect_games(games)
        print("Filtered out %d suspect games, leaving %d" % (
            start_num - len(games), len(games)))

    game_results = [{"%s (%s)" % (u['username'], u['userID']): int(u['rank'])
        for u in g['users']}
            for g in games]
    if config.num_games:
        if config.num_games > 0:
            game_results = game_results[:config.num_games]
            print("Using first %d games." % (len(game_results),))
        else:
            game_results = game_results[config.num_games:]
            print("Using last %d games." % (len(game_results),))

    trueskill.setup(draw_probability = 0.)
    rmse = ratings_rmse(game_results, ratings, winp, subjects)
    print("Given ratings RMSE %f" % (rmse,))
    ordering_ratio = ratings_order_error(game_results, ratings, rank_order, subjects)
    print("Given ratings incorrectly ordered %.2f%% results" % (
        ordering_ratio * 100,))

    if config.calc_best:
        best_scores(game_results)

if __name__ == "__main__":
    main()
