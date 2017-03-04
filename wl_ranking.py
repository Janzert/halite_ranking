#!/usr/bin/env python3

import argparse
import json
import math
import sys
from collections import Counter, namedtuple

import utility

MU = 25.
SIGMA = MU / 3
BETA = SIGMA / 2

Rating = namedtuple("Rating", ("mu", "sigma"))

"""
Rating system from the paper "A Bayesian Approximation Method for Online Ranking"
by Ruby Weng and Chih-Jen Lin
paper and original code found at
http://www.csie.ntu.edu.tw/~cjlin/papers/online_ranking/
"""

def wl_bt_ratings(game_results, last_ratings=dict()):
    """Weng-Lin Bradley-Terry Full Pair update rule ratings"""
    players = list(set(p for game in game_results for p in game))
    first = Rating(MU, SIGMA)
    mu = {p: last_ratings.get(p, first).mu for p in players}
    sigma = {p: last_ratings.get(p, first).sigma for p in players}
    for gnum, game in enumerate(game_results, start=1):
        omega = dict()
        delta = dict()
        for player, prank in game.items():
            omega[player] = 0.
            delta[player] = 0.
            for opp, orank in game.items():
                if opp == player:
                    continue
                ciq = math.sqrt(sigma[player]**2 + sigma[opp]**2 + (2*BETA**2))
                piq = 1. / (1. + math.exp((mu[opp] - mu[player]) / ciq))
                s = 0
                if orank > prank:
                    s = 1
                elif orank == prank:
                    s = 0.5

                omega[player] += (sigma[player]**2 / ciq) * (s - piq)
                gamma = sigma[player] / ciq
                delta[player] += gamma * (sigma[player]**2 / ciq) / ciq * piq * (1 - piq)
        for player in game:
            mu[player] += omega[player]
            sigma[player] *= math.sqrt(max(1 - delta[player], 0.0001))
        if gnum % 10000 == 0:
            print("\rRated %d games" % (gnum,), end="")
    if gnum >= 10000:
        print("\r", end="")
    if gnum > 5000:
        print("Rated %d games" % (gnum,))
    return {player: Rating(mu[player], sigma[player]) for player in players}

def wl_pl_ratings(game_results, last_ratings=dict()):
    """Weng-Lin Plackett-Luce update rule ratings"""
    players = list(set(p for game in game_results for p in game))
    first = Rating(MU, SIGMA)
    mu = {p: last_ratings.get(p, first).mu for p in players}
    sigma = {p: last_ratings.get(p, first).sigma for p in players}
    for gnum, game in enumerate(game_results, start=1):
        c = math.sqrt(sum(sigma[p]**2 + BETA**2 for p in game))
        Aq = Counter(r for r in game.values())
        if Aq.most_common()[0][0] != 1:
            print("Found tied ranks")
        sumCq = {q: sum(math.exp(mu[i] / c) for i in game if game[i] >= game[q])
                for q in game}
        omega = dict()
        delta = dict()
        for player, prank in game.items():
            omega[player] = 0.
            delta[player] = 0.
            gamma = sigma[player] / c
            for opp, orank in game.items():
                if orank > prank:
                    continue
                PiCq = math.exp(mu[player] / c) / sumCq[opp]
                if player == opp:
                    mf = 1 - PiCq
                else:
                    mf = 0 - PiCq
                omega[player] += mf * (sigma[player]**2 / (c * Aq[orank]))
                etaq = (gamma * sigma[player]**2) / (c**2 * Aq[orank])
                etaq *= PiCq * (1 - PiCq)
                delta[player] += etaq
        for player in game:
            mu[player] += omega[player]
            sigma[player] *= math.sqrt(max(1 - delta[player], 0.0001))
        if gnum % 10000 == 0:
            print("\rRated %d games" % (gnum,), end="")
    if gnum >= 10000:
        print("\r", end="")
    if gnum > 5000:
        print("Rated %d games" % (gnum,))
    return {player: Rating(mu[player], sigma[player]) for player in players}

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Create Weng-Lin ratings from game data.")
    parser.add_argument("game_files", nargs="+",
            help="Json files containing game data.")
    parser.add_argument("-d", "--display", type=int, default=40,
            help="Limit display of rating to top N (0 for all)")
    parser.add_argument("-n", "--num-games", type=int,
            help="Limit the number of games used (positive for first, negative for last")
    parser.add_argument("--remove-suspect", action="store_true",
            help="Filter out suspect games based on workerID.")
    parser.add_argument("--no-error", action="store_true",
            help="Filter out games that had bot errors.")
    parser.add_argument("-o", "--out-file",
            help="If specified will write the full ratings to given filename")
    parser.add_argument("--plackett-luce", action="store_true",
            help="Use Plackett-Luce update rule.")
    config = parser.parse_args(args)

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

    wl_ratings = wl_bt_ratings
    if config.plackett_luce:
        wl_ratings = wl_pl_ratings

    ratings = wl_ratings(game_results)

    ratings = sorted(ratings.items(), key=lambda x: -(x[1].mu - (x[1].sigma*3)))

    if config.out_file:
        with open(config.out_file, 'w') as out:
            for rank, (player, rating) in enumerate(ratings, start=1):
                score = rating.mu - (rating.sigma * 3)
                out.write('%d,%s,%f,%r,%r\n' % (rank, player, score,
                    rating.mu, rating.sigma))

    if config.display > 0:
        ratings = ratings[:config.display]

    rwidth = math.floor(math.log10(len(ratings))) + 1
    pwidth = max(len(r[0]) for r in ratings)
    for rank, (player, rating) in enumerate(ratings, start=1):
        score = rating.mu - (rating.sigma * 3)
        print("%*d: %*s %.2f (%.2f, %.2f)" % (rwidth, rank, pwidth, player,
            score, rating.mu, rating.sigma))

if __name__ == "__main__":
    main()
