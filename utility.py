import json

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

def filter_suspect_games(games):
    worker_cutoff = 160
    filtered = list()
    for game in games:
        if game['workerID'] is None or int(game['workerID']) > worker_cutoff:
            hadError = False
            for user in game['users']:
                if user["errorLogName"] is not None:
                    hadError = True
                    break
            if hadError:
                continue
        filtered.append(game)
    return filtered

def filter_error_games(games):
    filtered = list()
    for game in games:
        hadError = False
        for user in game['users']:
            if user['errorLogName'] is not None:
                hadError = True
                break
        if hadError:
            continue
        filtered.append(game)
    return filtered
