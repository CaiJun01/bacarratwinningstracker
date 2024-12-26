import random


class AppSession:
    def __init__(self):
        self.session_active = False
        self.round_count = 0
        self.players = []
        self.leader = None
        self.bets = {}
        self.balances = {}

    def start_session(self):
        if self.session_active:
            print("A session is already active.")
            return

        print("Starting a new session...")
        self.session_active = True
        self.round_count = 0

        while True:
            add_player = (
                input("Do you want to add a player to the session? (yes/no): ")
                .strip()
                .lower()
            )
            if add_player == "yes":
                player_name = input("Enter player name: ").strip()
                self.players.append(player_name)
                self.balances[player_name] = 0
                print(f"Player '{player_name}' added.")
            elif add_player == "no":
                break
            else:
                print("Invalid input. Please enter 'yes' or 'no'.")

        while not self.leader:
            leader_name = input("Enter the name of the leader: ").strip()
            if leader_name in self.players:
                self.leader = leader_name
                print(f"Player '{self.leader}' is set as the leader.")
            else:
                print("Invalid name. Please choose a player from the list.")

        print(f"Session started with players: {', '.join(self.players)}")
        print(f"Leader: {self.leader}")
        self.session_loop()

    def session_loop(self):
        while self.session_active:
            self.round_count += 1
            print(f"\nRound {self.round_count}")
            self.perform_round()

            continue_round = (
                input("Do you want to continue to the next round? (yes/no): ")
                .strip()
                .lower()
            )
            if continue_round != "yes":
                self.end_session()

    def perform_round(self):
        self.bets = {}
        for player in self.players:
            if player != self.leader:
                while True:
                    try:
                        bet = float(
                            input(f"{player}, enter your bet amount for this round: ")
                        )
                        if bet < 0:
                            print("Bet amount cannot be negative. Please try again.")
                        else:
                            self.bets[player] = bet
                            break
                    except ValueError:
                        print("Invalid input. Please enter a numeric value.")

        # Generate random numbers for players
        player_numbers = {}
        for player in self.players:
            player_numbers[player] = random.randint(1, 10)

        print("\nPlayer numbers:")
        for player, number in player_numbers.items():
            print(f"{player}: {number}")

        # Compare leader's number to other players
        leader_number = player_numbers[self.leader]
        for player, bet in self.bets.items():
            player_number = player_numbers[player]
            if leader_number > player_number:
                self.balances[self.leader] += bet
                self.balances[player] -= bet
                print(f"{self.leader} wins against {player}. {self.leader} gains {bet}, {player} loses {bet}.")
            elif leader_number < player_number:
                self.balances[self.leader] -= bet
                self.balances[player] += bet
                print(f"{player} wins against {self.leader}. {player} gains {bet}, {self.leader} loses {bet}.")
            else:
                print(f"{self.leader} and {player} tie. No balance changes.")

        print(f"\nUpdated balances: {self.balances}")

    def end_session(self):
        print("Ending the session...")
        print(f"Total rounds completed: {self.round_count}")
        self.session_active = False


# Example usage
if __name__ == "__main__":
    app = AppSession()
    while True:
        action = (
            input("Enter 'start' to begin a session, or 'exit' to quit the app: ")
            .strip()
            .lower()
        )
        if action == "start":
            app.start_session()
        elif action == "exit":
            print("Exiting the app. Goodbye!")
            break
        else:
            print("Invalid input. Please enter 'start' or 'exit'.")
