import asyncio
from abc import ABC


class GameState(ABC):
    def handle(self, game):
        pass

    def add_player(self, game, player):
        pass

    def remove_player(self, game, player):
        pass

    def place_bet(self, game, player, amount):
        pass

    def deal(self, game):
        pass

    def offer_insurance(self, game):
        pass

    def player_action(self, game, player, action):
        pass

    def dealer_action(self, game):
        pass

    def calculate_winner(self, game):
        pass

    def end_round(self, game):
        pass


class SimulationStats:
    def __init__(self):
        self.games_played = 0
        self.player_wins = 0
        self.dealer_wins = 0
        self.draws = 0

    def update(self, game):
        self.games_played += 1

        game.io_interface.output("Updating statistics...")
        player_win = any(player.winner == "player" for player in game.players)
        dealer_win = any(player.winner == "dealer" for player in game.players)
        draw = any(player.winner == "draw" for player in game.players)

        if player_win:
            self.player_wins += 1
        if dealer_win:
            self.dealer_wins += 1
        if draw:
            self.draws += 1

        # Reset the winners for next game
        for player in game.players:
            player.winner = None

    def report(self):
        return {
            "games_played": self.games_played,
            "player_wins": self.player_wins,
            "dealer_wins": self.dealer_wins,
            "draws": self.draws,
        }


class WaitingForPlayersState(GameState):
    async def handle(self, game):
        while len(game.players) < game.minimum_players:
            await asyncio.sleep(1)
        game.set_state(PlacingBetsState())

    def add_player(self, game, player):
        game.players.append(player)
        game.io_interface.output(f"{player.name} has joined the game.")

    def __str__(self):
        return "WaitingForPlayersState"


class PlacingBetsState(GameState):
    def handle(self, game):
        for player in game.players:
            self.place_bet(game, player, 10)
        game.set_state(DealingState())

    def place_bet(self, game, player, amount):
        player.place_bet(amount)
        game.io_interface.output(f"{player.name} has placed a bet of {amount}.")

    def __str__(self):
        return "PlacingBetsState"


class DealingState(GameState):
    def handle(self, game):
        game.deck.reset()
        self.deal(game)
        self.check_blackjack(game)
        game.set_state(OfferInsuranceState())

    def deal(self, game):
        game.deck.shuffle()
        for _ in range(2):
            for player in game.players + [game.dealer]:
                card = game.deck.deal()
                player.add_card(card)
                if player != game.dealer:
                    game.io_interface.output(f"Dealt {card} to {player.name}.")

    def check_blackjack(self, game):
        for player in game.players:
            if player.current_hand.value() == 21:
                game.io_interface.output(f"{player.name} got a blackjack!")
                player.payout(player.bet * 1.5)  # Blackjacks typically pay 3:2
                player.blackjack = True
                player.winner = "player"

        # Check for dealer's blackjack
        if game.dealer.current_hand.value() == 21:
            game.io_interface.output(f"Dealer got a blackjack!")
            dealer_win = True
            for player in game.players:
                if player.blackjack:  # If the player also has a blackjack, it's a draw
                    game.stats.draws += 1
                    dealer_win = False
                else:  # If the player doesn't have a blackjack, dealer wins
                    player.winner = "dealer"
            if dealer_win:
                game.dealer.winner = "dealer"

    def __str__(self):
        return "DealingState"


class OfferInsuranceState(GameState):
    def handle(self, game):
        for player in game.players:
            self.offer_insurance(game, player)
        game.io_interface.output(
            "Dealer's face up card is: " + str(game.dealer.current_hand.cards[0])
        )
        game.set_state(PlayersTurnState())

    def offer_insurance(self, game, player):
        if game.dealer.has_ace():
            game.io_interface.output("Dealer has an Ace!")
            player.buy_insurance(10)
            game.io_interface.output(f"{player.name} has bought insurance.")

    def __str__(self):
        return "OfferInsuranceState"


class PlayersTurnState(GameState):
    def handle(self, game):
        for player in game.players:
            while not player.is_done():
                game.io_interface.output(f"{player.name}'s turn.")
                action = player.decide_action()

                if action == "hit":
                    self.player_action(game, player, action)

                    if player.is_busted():
                        game.io_interface.output(f"{player.name} has busted.")
                        player.stand()
                        break

                    if player.current_hand.value() == 21:
                        game.io_interface.output(f"{player.name} has a blackjack.")
                        player.stand()
                        break

                elif action == "stand":
                    self.player_action(game, player, action)
                    break  # Exit the loop and move to the next player

        game.set_state(DealersTurnState())

    def player_action(self, game, player, action):
        if action == "hit":
            card = game.deck.deal()
            player.add_card(card)
            game.io_interface.output(f"{player.name} hits and gets {card}.")

        elif action == "stand":
            player.stand()
            game.io_interface.output(f"{player.name} stands.")

    def __str__(self):
        return "PlayersTurnState"


class DealersTurnState(GameState):
    def handle(self, game):
        while game.dealer.should_hit():
            self.dealer_action(game)
        game.io_interface.output("Dealer stands.")
        game.set_state(EndRoundState())

    def dealer_action(self, game):
        card = game.deck.deal()
        game.dealer.add_card(card)
        game.io_interface.output(f"Dealer hits and gets {card}.")

    def __str__(self):
        return "DealersTurnState"


class EndRoundState(GameState):
    def handle(self, game):
        self.calculate_winner(game)
        game.stats.update(game)

    def calculate_winner(self, game):
        dealer_hand_value = game.dealer.current_hand.value()
        dealer_cards = ", ".join(str(card) for card in game.dealer.current_hand.cards)
        game.io_interface.output(f"Dealer's final cards: {dealer_cards}")
        game.io_interface.output(f"Dealer's final hand value: {dealer_hand_value}")

        for player in game.players:
            player_hand_value = player.current_hand.value()
            player_cards = ", ".join(str(card) for card in player.current_hand.cards)
            game.io_interface.output(f"{player.name}'s final cards: {player_cards}")
            game.io_interface.output(
                f"{player.name}'s final hand value: {player_hand_value}"
            )

            if player_hand_value > 21:
                game.io_interface.output(f"{player.name} busts. Dealer wins!")
                player.winner = "dealer"
            elif dealer_hand_value > 21 or player_hand_value > dealer_hand_value:
                game.io_interface.output(f"{player.name} wins the round!")
                player.payout(player.bet * 2)
                player.winner = "player"
            elif player_hand_value < dealer_hand_value:
                game.io_interface.output(f"Dealer wins against {player.name}!")
                player.winner = "dealer"
            else:
                game.io_interface.output(f"{player.name} and Dealer tie! It's a push.")
                player.payout(player.bet)
                player.winner = "draw"

        game.set_state(PlacingBetsState())

    def __str__(self):
        return "EndRoundState"
