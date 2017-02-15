#!/usr/bin/env python3

import json
import sys
from collections import Counter


# Taken from https://github.com/erdman/plackett-luce/blob/master/plackett_luce.py
def plackett_luce(rankings):
    ''' Returns dictionary containing player : plackett_luce_parameter keys
    and values. This algorithm requires that every player avoids coming in
    last place at least once and that every player fails to win at least once.
    If this assumption fails (not checked), the algorithm will diverge.
    Input is a list of dictionaries, where each dictionary corresponds to an
    individual ranking and contains the player : finish for that ranking.
    The plackett_luce parameters returned are un-normalized and can be
    normalized by the calling function if desired.'''
    players = set(key for ranking in rankings for key in ranking.keys())
    ws = Counter(name for ranking in rankings for name, finish in ranking.items() if finish < len(ranking))
    gammas = {player : 1.0 / len(players) for player in players}
    _gammas = {player : 0 for player in players}
    gdiff = 10
    pgdiff = 100
    iteration = 0
    while gdiff > 1e-9:
        denoms = {player : sum(sum(0 if player not in ranking or ranking[player] < place else 1 / sum(gammas[finisher] for finisher in ranking if ranking[finisher] >= place) for place in range(1,len(ranking))) for ranking in rankings) for player in players}
        _gammas = gammas
        gammas = {player : ws[player] / denoms[player] for player in players}
        pgdiff = gdiff
        gdiff = sum((gamma - _gammas[player]) ** 2 for player, gamma in gammas.items())
        iteration += 1
        print("\r%d gd=%.2e" % (iteration, gdiff,), end="")
        if gdiff > pgdiff:
            print()
            print("Gamma difference increased, %.4e %.4e" % (gdiff, pgdiff))
    print()
    return gammas

def normalize_ratings(ratings):
    normalization_constant = sum(value for p, value in ratings)
    return [(p, v / normalization_constant) for p, v in ratings]

def check_games(games):
    """Check that every player does not come in 1st and does not come in last
    at least once each."""
    pc = dict()
    for game in game_results:
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
        for player, (win, loss) in pc.items():
            if not win and not loss:
                continue
            if win and loss:
                # This should never happen.
                raise Exception("Player with neither win or loss %s" % (player,))
            print("Player %s has no %s" % (player, "win" if win else "loss"))
            print("%d %d" % (win, loss))
        return False
    return True

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

def main(args=sys.argv):
    games = load_games(args[1:])
    game_results = [{u['username']: int(u['rank']) for u in g['users']}
            for g in games]
    if not check_games:
        return
    ratings = plackett_luce(game_results)
    ratings = list(ratings.items()).sort(key=lambda x: -x[1])
    ratings = normalize_ratings(ratings[:40])

    for rank, (player, rating) in enumerate(ratings, start=1):
        print("%d: %s (%.4f)" % (rank, player, rating))

if __name__ == "__main__":
    main()
