#!/usr/bin/env python3

import argparse
import json
import math
import sys
import time
from collections import Counter

HAVE_NUMPY = False
try:
    import numpy
    HAVE_NUMPY = True
except ImportError:
    pass


"""
Implementation from erdman at https://github.com/erdman/plackett-luce/blob/master/plackett_luce.py

as given in:
MM Algorithms For Generalized Bradley–Terry Models By David R. Hunter
Section 5

Paper found at http://projecteuclid.org/download/pdf_1/euclid.aos/1079120141
Original matlab code from paper is at
http://sites.stat.psu.edu/~dhunter/code/btmatlab/
"""
def pl_python(rankings, tolerance):
    ''' Returns dictionary containing player : plackett_luce_parameter keys
    and values. This algorithm requires that the set of players be unable to be
    split into two disjoint sets where nobody from set A has beaten anyone from
    set B.  If this assumption fails (not checked), the algorithm will diverge.
    Input is a list of dictionaries, where each dictionary corresponds to an
    individual ranking and contains the player : finish for that ranking.
    The plackett_luce parameters returned are un-normalized and can be
    normalized by the calling function if desired.'''
    players = set(key for ranking in rankings for key in ranking.keys())
    ws = Counter(name for ranking in rankings for name, finish in ranking.items() if finish < max(ranking.values()))
    gammas = {player : 1.0 / len(players) for player in players}
    _gammas = {player : 0 for player in players}
    gdiff = 10
    iteration = 0
    start = time.perf_counter()
    while gdiff > tolerance:
        denoms = {player : sum(sum(0 if ranking.get(player,-1) < place else
            1 / sum(gammas[finisher] for finisher, finish in ranking.items() if finish >= place)
            for place in sorted(ranking.values())[:-1])
            for ranking in rankings) for player in players}

        _gammas = gammas
        gammas = {player : ws[player] / denoms[player] for player in players}
        pgdiff = gdiff
        gdiff = math.sqrt(sum((gamma - _gammas[player]) ** 2 for player, gamma in gammas.items()))
        iteration += 1
        now = time.perf_counter()
        print("%d %.2f seconds L2=%.2e" % (iteration, now-start, gdiff))
        if gdiff > pgdiff:
            print("Gamma difference increased, %.4e %.4e" % (gdiff, pgdiff))
        start = now
    return gammas
plackett_luce = pl_python

def pl_numpy(rankings, tolerance):
    """ Numpy implementation based directly off of the original matlab code.
    """
    players = list(set(key for ranking in rankings for key in ranking.keys()))

    ws = Counter(name for ranking in rankings for name, finish in ranking.items() if finish < max(ranking.values()))

    # matlab code is 1-based, we're using 0-based so be wary of off-by-ones
    a = numpy.array([(players.index(name) + 1, ranking_index, finish) for ranking_index, ranking in enumerate(rankings, 1) for name, finish in ranking.items()], dtype = int)
    M, N, P = numpy.max(a, axis=0)   #finding the counts of players and contests and the max rank ... I would have used len, but following orignal code
    f = numpy.zeros((P, N), dtype=int)
    r = numpy.zeros((M, N), dtype=int)
    f[a[:,2] - 1, a[:,1] - 1] = a[:,0]
    r[a[:,0] - 1, a[:,1] - 1] = a[:,2] + P * (a[:,1] - 1)

    w = numpy.array([ws[player] for player in players], dtype=int)
    pp = sum(f > 0)  # players per contest
    #~ pp += numpy.arange(-1, N*P-1, P)  # this isn't necessary

    gammas = numpy.ones((M)) / M
    gdiff = 1
    iterations = 0
    start = time.perf_counter()
    while gdiff > tolerance:
        iterations += 1
        g = (f > 0).choose(0, gammas[f - 1].squeeze())
        g = numpy.cumsum(g[::-1,:],axis=0)[::-1,:]   #reverse vertical cumsum
        g[pp - 1, numpy.arange(numpy.shape(g)[1])] = 0
        g[g > 0] = 1 / g[g > 0]
        numpy.cumsum(g,axis=0,out=g)
        r2 = (r > 0).choose(0, g.T.flat[r - 1])  #array indexing like Matlab https://stackoverflow.com/questions/20688881/numpy-assignment-and-indexing-as-matlab
        _gammas = gammas
        gammas = w / numpy.sum(r2,axis=1)
        pgdiff = gdiff
        gdiff = numpy.linalg.norm(gammas - _gammas)
        now = time.perf_counter()
        print("%d %.2f seconds L2=%.2e" % (iterations, now-start, gdiff))
        if gdiff > pgdiff:
            print("Gamma difference increased, %.4e %.4e" % (gdiff, pgdiff))
        start = now

    return {player : gamma for player, gamma in zip(players, gammas)}
if HAVE_NUMPY:
    plackett_luce = pl_numpy

def normalize_ratings(ratings):
    normalization_constant = sum(value for p, value in ratings)
    return [(p, v / normalization_constant) for p, v in ratings]

def check_games(games):
    """Check that every player does not come in 1st and does not come in last
    at least once each."""
    pc = dict()
    for game in games:
        max_rank = 0
        max_user = None
        for user, rank in game.items():
            if rank > 1:
                pc.setdefault(user, [1, 1])[1] = 0
            if rank > max_rank:
                if max_user:
                    pc.setdefault(max_user, [1, 1])[0] = 0
                max_rank = rank
                max_user = user
            elif rank < max_rank:
                pc.setdefault(user, [1, 1])[0] = 0
    missing_wl = sum(w+l for w, l in pc.values())
    if missing_wl > 0:
        winners = list()
        losers = list()
        for player, (win, loss) in pc.items():
            if not win and not loss:
                continue
            if win and loss:
                # This should never happen.
                raise Exception("Player with neither win or loss %s" % (player,))
            if win:
                losers.append(player)
            else:
                winners.append(player)
            print("Player %s has no %s" % (player, "win" if win else "loss"))
        return winners, losers
    return None, None

def filter_in_players(games, players):
    keep_players = set(players)
    filtered = list()
    for game in games:
        game_players = set(game.keys())
        if game_players & keep_players:
            filtered.append(game)
    return filtered

def filter_out_players(games, players):
    drop_players = set(players)
    filtered = list()
    for game in games:
        game_players = set(game.keys())
        if not (game_players & drop_players):
            filtered.append(game)
    return filtered

def load_games(filenames):
    games = list()
    for filename in filenames:
        print("Reading %s" % (filename,))
        with open(filename) as gfile:
            games += json.load(gfile)
    gids = set()
    uniques = list()
    for g in games:
        if g['gameID'] not in gids:
            uniques.append(g)
            gids.add(g['gameID'])
    games = uniques
    games.sort(key=lambda x: int(x['gameID']))
    print("%d games loaded." % (len(games),))
    return games

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Create Plackett-Luce ratings from game data.")
    parser.add_argument("game_files", nargs="+",
            help="Json files containing game data.")
    parser.add_argument("-a", "--anchor-player", action="store_true",
            help="Add a player with a win and loss against every other player.")
    parser.add_argument("-r", "--remove-bottom", action="store_true",
            help="Exclude the bottom, always crash, bots")
    parser.add_argument("-x", "--exclude", action="append",
            help="Exclude player")
    parser.add_argument("-t", "--tolerance", type=float, default=1e-9,
            help="Set rating convergance tolerance.")
    parser.add_argument("-d", "--display", type=int, default=40,
            help="Limit display of rating to top N (0 for all)")
    parser.add_argument("-n", "--num-games", type=int,
            help="Limit the number of games used (positive for first, negative for last")
    parser.add_argument("-o", "--out-file",
            help="If specified will write the full ratings to given filename")
    parser.add_argument("--no-numpy", action="store_true",
            help="Force use of native implementation, even if numpy is available")
    config = parser.parse_args(args)

    if config.no_numpy:
        global plackett_luce
        plackett_luce = pl_python
        print("Disabled numpy use.")

    excluded_players = []
    if config.exclude:
        excluded_players = config.exclude
        print("Excluding %s" % (excluded_players,))
    if config.remove_bottom:
        print("Removing crash bots.")
        excluded_players += 'FredericWantiez Sametine aikinogard ozadDaro cymb01 byrd106 kxmbrian sscholle patrisk jvienna ardapekis fbastos1'.split()
    games = load_games(config.game_files)
    game_results = [{"%s (%s)" % (u['username'], u['userID']): int(u['rank'])
        for u in g['users'] if u['username'] not in excluded_players}
            for g in games if sum(u['username'] not in excluded_players
                for u in g['users']) > 1]
                    #only include games with 2 or more non-excluded competitors
    if config.num_games:
        if config.num_games > 0:
            game_results = game_results[:config.num_games]
            print("Using first %d games." % (len(game_results),))
        else:
            game_results = game_results[config.num_games:]
            print("Using last %d games." % (len(game_results),))

    winners, losers = check_games(game_results)
    if winners:
        print("%d were undefeated" % (len(winners),))
    if losers:
        print("%d never won" % (len(losers),))
    if not config.anchor_player and (winners or losers):
        print("WARNING: Ratings will almost certainly not converge.\n(Maybe run with --anchor-player)")

    players = set()
    for game in game_results:
        players |= set(p for p in game.keys())
    print("%d players" % (len(players),))

    if config.anchor_player:
        # Add a fake player with one win and loss against everyone
        print("Adding anchor player.")
        fake_games = list()
        for p in players:
            fake_games.append({0: 1, p: 2})
            fake_games.append({0: 2, p: 1})
        game_results += fake_games

    ratings = plackett_luce(game_results, config.tolerance)

    if config.anchor_player:
        # remove anchor player
        del ratings[0]

    ratings = list(ratings.items())
    ratings.sort(key=lambda x: -x[1])

    if config.out_file:
        ratings = normalize_ratings(ratings)
        with open(config.out_file, 'w') as out:
            for rank, (player, rating) in enumerate(ratings, start=1):
                out.write('%d,%e,%s\n' % (rank, rating, player))

    if config.display > 0:
        ratings = ratings[:config.display]
    ratings = normalize_ratings(ratings)

    for rank, (player, rating) in enumerate(ratings, start=1):
        print("%d: %.4f - %s" % (rank, rating, player))

if __name__ == "__main__":
    main()
