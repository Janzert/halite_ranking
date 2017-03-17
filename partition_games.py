#!/usr/bin/env python3

import argparse
import json
import math
import os
import random
import sys

from utility import load_games

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Split games into multiple sets.")
    parser.add_argument("game_files", nargs="+",
            help="Json files containing game data.")
    parser.add_argument("-o", "--out-dir", required=True,
            help="Directory name for output files.")
    parser.add_argument("-n", "--num-parts", type=int, default=10,
            help="Number of parts to split games into.")
    config = parser.parse_args(args)

    games = load_games(config.game_files)
    random.shuffle(games)

    num_parts = config.num_parts
    parts = list()
    end_game = 0
    for i in range(num_parts):
        start_game = end_game
        end_game = start_game + (len(games) // num_parts)
        if i < len(games) % num_parts:
            end_game += 1
        parts.append(games[start_game:end_game])

    for p in parts:
        p.sort(key=lambda x: x['gameID'])

    pn_width = int(math.ceil(math.log10(num_parts)))
    os.makedirs(config.out_dir)
    for i, p in enumerate(parts):
        pname = "part-%0*d.json" % (pn_width, i)
        ppath = os.path.join(config.out_dir, pname)
        with open(ppath, 'w') as pfile:
            json.dump(p, pfile, indent=2)
        print("Wrote %d games to %s" % (len(p), ppath))

if __name__ == "__main__":
    main()
