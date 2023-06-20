# Matchmaker

This game was made as a project for my CPSC559 course in uni, along with 4 other team members

Run the game with:

> python server.py

> python game.py

Additionally, there are several flags:
* -d (debug) will expedite setup, using the existing server and automatically joining a room
* -s (silent) will not touch the room cache, allowing multiple games to run on the same computer without conflicts.
* -n (newGame) will delete the room cache if it is present.

To skip all the setup (it will automatically create a room or connect to the first available one)

To play the game, click and drag on a circle of your own color (look for the color with the black bar at the bottom) to choose its path.
If a player is absent, their box will become grey, and an AI will take over and control their circles.
Players can disconnect whenever, and the game will restructure to keep everything working.
