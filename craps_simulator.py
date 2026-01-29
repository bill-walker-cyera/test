#!/usr/bin/env python3
"""
Basic craps simulator (CLI).

This focuses on the core game logic without any GUI. It can simulate a single
game with roll-by-roll output or many games with summary statistics.
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Roll:
    die1: int
    die2: int
    total: int


@dataclass(frozen=True)
class GameResult:
    win: bool
    point: Optional[int]
    roll_count: int
    rolls: Optional[List[Roll]]


def roll_dice(rng: random.Random) -> Roll:
    die1 = rng.randint(1, 6)
    die2 = rng.randint(1, 6)
    return Roll(die1=die1, die2=die2, total=die1 + die2)


def play_game(rng: random.Random, record_rolls: bool) -> GameResult:
    rolls: Optional[List[Roll]] = [] if record_rolls else None
    roll_count = 0
    point: Optional[int] = None

    while True:
        roll = roll_dice(rng)
        roll_count += 1
        if rolls is not None:
            rolls.append(roll)

        if point is None:
            if roll.total in (7, 11):
                return GameResult(True, None, roll_count, rolls)
            if roll.total in (2, 3, 12):
                return GameResult(False, None, roll_count, rolls)
            point = roll.total
        else:
            if roll.total == point:
                return GameResult(True, point, roll_count, rolls)
            if roll.total == 7:
                return GameResult(False, point, roll_count, rolls)


def format_roll(roll: Roll) -> str:
    return f"{roll.die1}+{roll.die2}={roll.total}"


def print_game(result: GameResult, game_index: int) -> None:
    header = f"Game {game_index}:" if game_index > 0 else "Game:"
    print(header)

    if result.rolls:
        come_out = result.rolls[0]
        print(f"  Come-out roll: {format_roll(come_out)}")
        if result.point is None:
            print("  No point established.")
        else:
            print(f"  Point established: {result.point}")
            for idx, roll in enumerate(result.rolls[1:], start=2):
                print(f"  Roll {idx}: {format_roll(roll)}")
    else:
        print("  Rolls not recorded.")

    outcome = "WIN" if result.win else "LOSS"
    print(f"  Result: {outcome}")
    print(f"  Total rolls: {result.roll_count}")


def summarize_results(wins: int, losses: int, total_rolls: int) -> None:
    games = wins + losses
    if games == 0:
        print("No games simulated.")
        return

    win_rate = wins / games * 100
    avg_rolls = total_rolls / games
    print("\nSummary")
    print("-------")
    print(f"Games: {games}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win rate: {win_rate:.2f}%")
    print(f"Average rolls per game: {avg_rolls:.2f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Basic craps simulator")
    parser.add_argument(
        "--games",
        type=int,
        default=1,
        help="Number of games to simulate (default: 1)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible results",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show roll-by-roll output for each game",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show summary statistics",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.games < 1:
        raise SystemExit("--games must be at least 1")

    rng = random.Random(args.seed)

    wins = 0
    losses = 0
    total_rolls = 0

    record_rolls = args.verbose or (args.games == 1 and not args.quiet)

    for game_index in range(1, args.games + 1):
        result = play_game(rng, record_rolls=record_rolls)
        total_rolls += result.roll_count
        if result.win:
            wins += 1
        else:
            losses += 1

        if record_rolls and not args.quiet:
            print_game(result, game_index)
            if game_index < args.games:
                print()

    if not args.quiet:
        summarize_results(wins, losses, total_rolls)


if __name__ == "__main__":
    main()
