% A Quick Rating System Comparison.
% Brian (Janzert) Haskin

This is a quick look at the performance of a few different rating systems using data from the Halite programming competition. There is no particular reason for the systems chosen other than being ones that handle multiplayer games and for which I could get or write an implementation. This did happen to nicely give two systems to compare against Trueskill (the system used during the contest). One is another incremental, locally updated, system like Trueskill and the other is a global update system.

Review of Halite data
=====================
[Halite](https://halite.io/) is a programming competition where games are played in a free-for-all format between 2 to 6 players. The data looked at here is from the finals of the first competition. During the finals all submissions were closed and games were played continuously between the bots. The finals finished with 95562 games involving 1592 players.

At the start of the finals all ratings were reset. So the first games had mostly large differences in skill levels. As the Trueskill ratings used in the competition converged the skill of opponents became much closer in later games.

At various stages throughout the finals the lower ranked players were removed from seeding games. Until about 400 players were left actively playing. Because of this the number of games a player participated in varies between 73 and 563 games.

Rating systems
==============

I look at 3 different systems and 5 varients of those systems total. These are Trueskill, a bayesian approximation system by Ruby Weng and Chih-Jen Lin, and the Plackett-Luce model with a minorization-maximization algorithm.

Trueskill was initially published in "[TrueSkill(TM): A Bayesian Skill Rating System](https://www.microsoft.com/en-us/research/publication/trueskilltm-a-bayesian-skill-rating-system/)" (2007) by Herbrich et al. after being developed at Microsoft for use in ranking and matchmaking on Xbox Live. It builds off of the Glicko system which introduced the idea of using a mean and variance to represent a player's skill level. Trueskill generalized the Glicko system to an arbitrary number of teams per game and players per team. Trueskill has since then become one of the better known rating systems and is often used as the standard against which new systems are compared. It has also been reimplemented several times in a number of different programming languages. Trueskill was used for ranking during the Halite competition with a python Trueskill implementation that can be found at [trueskill.org](http://trueskill.org). The same implementation was used here.

Ruby Weng and Chih-Jen Lin published "[A Bayesian Approximation Method for Online Ranking](http://www.csie.ntu.edu.tw/~cjlin/papers/online_ranking/online_journal.pdf)" in 2011, in which they develop a framework to derive simple update rules implementing a number of different models. Here I look at their Bradley-Terry full pair, and Plackett-Luce model update rules. These are referred to as Weng-Lin BT-FP and Weng-Lin PL below. The implementation used was written by myself in python and verified with the original C++ code used in the paper.

Plackett-Luce is a generalization of the [Bradley-Terry model](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model) in order to handle games with more than two players. Unlike the first two systems looked at here it is a globally updated ranking system. Meaning that the system looks at all game results and all the players as a complete unit instead of doing incremental rating updates on each result separately. A minorization–maximization (MM) algorithm for finding this is given by David Hunter in "[MM Algorithms For Generalized Bradley-Terry Models](http://sites.stat.psu.edu/~dhunter/papers/bt.pdf)". The implementation used here was written in python by Travis Erdman.

Prediction error
================

The most common way to compare different rating systems is to look at how well they predict game outcomes. I will be following the specific details first used by Heibrich, et.al. and fully described by Weng and Lin. The metric used is prediction error rate, or how often the ratings mispredict one player beating another.

The full set of games was broken up into a training and a test set. With 10% of the games randomly chosen to be in the test set. Giving 86006 training games and 9556 games used to test.

Trueskill was tested both with default settings and with $\tau$ set to zero.
The Trueskill $\tau$ parameter is used to maintain a level of volatility in the
ratings so that players with changing skill levels don't get 'stuck' at
a particular rating level. With player bots not changing over the course of the
finals they maintain a fixed skill throughout.

| Rating System      | Training Error | Test Error |
|--------------------|---------------:|-----------:|
| Plackett-Luce      | 41.44% | 43.87% |
| Trueskill          | 41.70% | 44.72% |
| Trueskill $\tau$=0 | 41.33% | 44.24% |
| Weng-Lin BT-FP     | 42.19% | 44.56% |
| Weng-Lin PL        | 43.34% | 45.81% |

Subset training
===============

One method to improve the accuracy of ratings is to remove noise from the results. Results that for whatever reason do not reflect the true strength of the participants. In Halite a primary suspect for such noise in the results are from bots having an error or timeout in a game.

Taking all games with bot errors in them out of the training set removes 4276 games, leaving 81730 games. The test set contains 469 games with errors. The test set is kept complete, with all games left in.

In a few cases this leaves a player with no games for training and no rating to make a prediction from. This occurs for around 1.3% of predictions and are not counted one way or the other below.

| Rating System      | Training Error | Test Error |
|--------------------|---------------:|-----------:|
| Plackett-Luce      | 41.82% | 43.80%
| Trueskill          | 41.63% | 44.91%
| Trueskill $\tau$=0 | 41.30% | 44.18%
| Weng-Lin BT-FP     | 41.98% | 44.69%
| Weng-Lin PL        | 43.11% | 45.76%

As you can see when comparing to the last table the removal only makes a small difference. In some cases helping and in others hurting the result.

During the finals it was found that a number of the servers playing games had a much higher error rate than the others. They had error rates from 24-59%, whereas the other servers ranged from 2-9%. These servers were then removed from the pool playing games. The last game being the 22020th game of the finals. Unfortunately for the first 18178 games the server the game was played on was not recorded. So for most of the period we cannot separate games from the suspect workers and the good workers. Instead below I've removed any game with an error from an unknown worker and also from any known worker with a high error rate.

This removes 2040 games from the training set leaving 83966. The test set has 219 suspect games. As above no games are removed from the test set when testing.

| Rating System      | Training Error | Test Error |
|--------------------|---------------:|-----------:|
| Plackett-Luce      | 41.44% | 43.53%
| Trueskill          | 41.88% | 44.98%
| Trueskill $\tau$=0 | 41.58% | 44.50%
| Weng-Lin BT-FP     | 42.28% | 44.78%
| Weng-Lin PL        | 43.39% | 45.83%

Interestingly this is worse for both incrementally updated systems but better for the global Plackett-Luce system.

Effect of game order
====================

Because of the global update the results of the Plackett-Luce MM algorithm are game order independent. But the other 2 systems having incremental local updates can give different ratings from the same game results in a different order. In fact the chronologic order used so far is probably close to ideal for these systems. Since the early games will have the widest spread of skills and end with games very close. For the same reason reversing the order will probably be close to the worst case. Besides the reverse order I also tested randomly shuffling the games. This was done 100 times with the mean and standard deviation of the error reported below.

| Ratings            | Training order | Test error |
|--------------------|----------------|:-----------|
| Trueskill          | Chronologic | 44.72%
|                    | Random      | 47.71% (0.26%)
|                    | Reverse     | 48.59%
| Trueskill $\tau$=0 | Chronologic | 44.24%
|                    | Random      | 47.39% (0.25%)
|                    | Reverse     | 49.62%
| Weng-Lin BT-FP     | Chronologic | 44.69%
|                    | Random      | 46.80% (0.26%)
|                    | Reverse     | 47.48%
| Weng-Lin PL        | Chronologic | 45.81%
|                    | Random      | 47.09% (0.24%)
|                    | Reverse     | 47.26%

Processing time
===============

One important aspect for practical use that isn't reflected in the above discussion is the time needed to create the ratings. This varies significantly between the systems. Trueskill takes about 1 minute to process all of the training games. The Weng-Lin implementation is quite a bit faster taking only 2.5 seconds for the Brandley-Terry updates and 3 seconds with Plackett-Luce. Also both systems being incrementally updated are very fast to add another game into the results. For most applications either system is fast enough.

On the other hand the Plackett-Luce MM algorithm takes about 3 hours to converge the ratings using the training set. This is using a numpy implementation that is 40 times faster than a plain python implementation. While the other two systems are in plain python. Also we can simulate the situation of updating current ratings with the results of a new game. This is simply done by converging on the training set minus the last game then adding the last game. This takes 16 minutes to update the ratings with that final result. Much too slow in a competition where 20 or more games were played every minute.

Skill distribution
==================

An aspect of player skills that may not be immediately obvious is how the difference in skill from one player to the next varies through the rankings. The skill differences at the extremes, the very top and very bottom players, are fairly large. But much of the middle ranks are very close in skill. This can be seen looking at the prediction error differences for specific groups of players. Here using Trueskill with default settings trained on the full training subset above. Only predictions that involve at least one player in the group are used.

| Players | Test error |
|---------|-----------:|
| All         | 44.72%
| Top 10      | 30.32%
| Top 100     | 42.48%
| Middle 1392 | 45.00%
| Bottom 100  | 38.41%
| Bottom 10   | 24.59%

The middle 1392 excludes the top and bottom 100 players.

Closing thoughts
================

Trueskill is probably the most widely known and implemented rating system for games involving more than 2 players. It is also very competitive in rating and processing performance, especially if the configuration parameters are adjusted to fit the game. The Weng-Lin framework is significantly easier to implement and somewhat faster to calculate ratings with, while still maintaining comparable accuracy in the results. Finally the Plackett-Luce system gives the most accurate ratings here, but can be quite computationally expensive to calculate.

Thanks to [Travis Erdman](https://github.com/erdman) for his implmentation of the Plackett-Luce MM algorithm.

Thanks also to [Two Sigma](https://www.twosigma.com/), especially [Michael Truell](https://github.com/truell20) and [Ben Spector](https://github.com/Sydriax) for
creating and running the Halite competition.

All of the data and code used can be found on [github](https://github.com/Janzert/halite_ranking). A few of my other projects can be found at [janzert.com](http://janzert.com).
