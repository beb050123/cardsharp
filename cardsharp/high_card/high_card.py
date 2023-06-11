import argparse
import asyncio
import random
import time

from cardsharp.common.actor import SimplePlayer
from cardsharp.common.deck import Deck
from cardsharp.common.io_interface import DummyIOInterface, IOInterface
from cardsharp.common.state import GameState


class HighCardGameState(GameState):
    def __init__(self, player_names):
        self.rounds_played = 0
        self.wins = {name: 0 for name in player_names}
        self.current_streak = {name: 0 for name in player_names}
        self.max_streak = {name: 0 for name in player_names}

    def get_state(self):
        return {
            "rounds_played": self.rounds_played,
            "wins": self.wins,
            "current_streak": self.current_streak,
            "max_streak": self.max_streak,
        }

    def update_state(self, new_state):
        self.rounds_played = new_state.get("rounds_played", self.rounds_played)
        self.wins = new_state.get("wins", self.wins)
        self.current_streak = new_state.get("current_streak", self.current_streak)
        self.max_streak = new_state.get("max_streak", self.max_streak)

    def display_stats(self):
        print(f"Rounds Played: {self.rounds_played}")
        for player, wins in self.wins.items():
            win_percentage = (wins / self.rounds_played) * 100
            print(f"{player} won {wins} times ({win_percentage:.2f}%).")
            print(f"{player}'s longest win streak: {self.max_streak[player]}")


class HighCardGame:
    def __init__(
        self, *players, io_interface: IOInterface, game_state: HighCardGameState
    ):
        self.players = players
        self.deck = Deck()
        self.io_interface = io_interface
        self.game_state = game_state

    async def play_round(self):
        self.deck.reset()
        high_card = None
        winner = None
        player_list = list(self.players)
        random.shuffle(player_list)

        for player in player_list:
            player.reset_hands()
            drawn_card = self.deck.deal()
            player.hands[0].add_card(drawn_card)
            await self.io_interface.send_message(f"{player.name} drew {drawn_card}")

            if not high_card or drawn_card.rank > high_card.rank:
                high_card = drawn_card
                winner = player

        if winner:
            self.game_state.update_state(
                {
                    "rounds_played": self.game_state.rounds_played + 1,
                    "wins": {
                        **self.game_state.wins,
                        winner.name: self.game_state.wins.get(winner.name, 0) + 1,
                    },
                    "current_streak": {
                        **{
                            name: 0
                            for name in self.game_state.current_streak.keys()
                            if name != winner.name
                        },
                        winner.name: self.game_state.current_streak.get(winner.name, 0)
                        + 1,
                    },
                    "max_streak": {
                        **{
                            name: self.game_state.max_streak.get(name, 0)
                            for name in self.game_state.max_streak.keys()
                            if name != winner.name
                        },
                        winner.name: max(
                            self.game_state.max_streak.get(winner.name, 0),
                            self.game_state.current_streak.get(winner.name, 0) + 1,
                        ),
                    },
                }
            )
        return winner


def parse_args():
    parser = argparse.ArgumentParser(description="Play a simulation of High Card.")
    parser.add_argument(
        "-r",
        "--rounds",
        type=int,
        default=1000,
        help="number of rounds to play (default: 1000)",
    )
    parser.add_argument(
        "-p", "--players", type=int, default=2, help="number of players (default: 2)"
    )
    parser.add_argument(
        "-n",
        "--names",
        nargs="+",
        default=["Alice", "Bob"],
        help="names of the players (default: Alice Bob)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    io_interface = DummyIOInterface()
    players = [SimplePlayer(name, io_interface) for name in args.names[: args.players]]
    game_state = HighCardGameState(args.names[: args.players])
    game = HighCardGame(*players, io_interface=io_interface, game_state=game_state)

    for _ in range(args.rounds):
        await game.play_round()

    game_state.display_stats()


if __name__ == "__main__":
    asyncio.run(main())
