"""
Zoldyck Assassination Contract Board - Main Runner & Report Generator
Includes dummy JSON data (5 cities, 10 contracts) for immediate testing.
"""

import json
import sys
import io
from models import Contract, Player, WorldMap
from optimizer import BeamSearchOptimizer


# ============================================================
# DUMMY TEST DATA - 5 Cities, 10 Contracts
# ============================================================

DUMMY_MAP_DATA = {
    "cities": ["A", "B", "C", "D", "E"],
    "edges": [
        {"from": "A", "to": "B", "days": 2},
        {"from": "A", "to": "C", "days": 3},
        {"from": "A", "to": "D", "days": 5},
        {"from": "A", "to": "E", "days": 4},
        {"from": "B", "to": "C", "days": 2},
        {"from": "B", "to": "D", "days": 3},
        {"from": "B", "to": "E", "days": 4},
        {"from": "C", "to": "D", "days": 2},
        {"from": "C", "to": "E", "days": 3},
        {"from": "D", "to": "E", "days": 2}
    ]
}

DUMMY_CONTRACTS = [
    # --- Phase 1: Low difficulty, skill farming ---
    {
        "contract_id": "C001", "city": "A", "difficulty": 1,
        "gold_reward": 50, "rep_reward": 2.0, "deadline": 30,
        "execution_time": 3, "required_skill": "stealth",
        "required_skill_level": 0, "is_trap": False
    },
    {
        "contract_id": "C002", "city": "A", "difficulty": 1,
        "gold_reward": 60, "rep_reward": 2.5, "deadline": 40,
        "execution_time": 2, "required_skill": "combat",
        "required_skill_level": 0, "is_trap": False
    },
    {
        "contract_id": "C003", "city": "B", "difficulty": 2,
        "gold_reward": 80, "rep_reward": 3.0, "deadline": 50,
        "execution_time": 4, "required_skill": "poison",
        "required_skill_level": 1, "is_trap": False
    },
    {
        "contract_id": "C004", "city": "B", "difficulty": 1,
        "gold_reward": 45, "rep_reward": 1.5, "deadline": 35,
        "execution_time": 2, "required_skill": "intel",
        "required_skill_level": 0, "is_trap": False
    },
    {
        "contract_id": "C005", "city": "C", "difficulty": 2,
        "gold_reward": 90, "rep_reward": 3.0, "deadline": 60,
        "execution_time": 5, "required_skill": "acrobatics",
        "required_skill_level": 1, "is_trap": True  # TRAP!
    },
    # --- Phase 2: High reward, higher difficulty ---
    {
        "contract_id": "C006", "city": "C", "difficulty": 4,
        "gold_reward": 300, "rep_reward": 8.0, "deadline": 120,
        "execution_time": 8, "required_skill": "stealth",
        "required_skill_level": 3, "is_trap": False
    },
    {
        "contract_id": "C007", "city": "D", "difficulty": 5,
        "gold_reward": 500, "rep_reward": 10.0, "deadline": 150,
        "execution_time": 10, "required_skill": "combat",
        "required_skill_level": 4, "is_trap": False
    },
    {
        "contract_id": "C008", "city": "D", "difficulty": 3,
        "gold_reward": 200, "rep_reward": 5.0, "deadline": 100,
        "execution_time": 6, "required_skill": "poison",
        "required_skill_level": 2, "is_trap": True  # TRAP!
    },
    {
        "contract_id": "C009", "city": "E", "difficulty": 4,
        "gold_reward": 350, "rep_reward": 7.0, "deadline": 140,
        "execution_time": 7, "required_skill": "intel",
        "required_skill_level": 3, "is_trap": False
    },
    {
        "contract_id": "C010", "city": "E", "difficulty": 5,
        "gold_reward": 600, "rep_reward": 12.0, "deadline": 180,
        "execution_time": 12, "required_skill": "acrobatics",
        "required_skill_level": 5, "is_trap": False
    }
]


# ============================================================
# REPORT GENERATORS
# ============================================================

def generate_optimal_path_report(player: Player) -> str:
    """Generate the day-by-day Optimal Path Report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  OPTIMAL PATH REPORT - Zoldyck Assassination Contract Board")
    lines.append("=" * 70)
    lines.append(f"  Total Days Used: {player.current_day - 1} / {Player.MAX_DAYS}")
    lines.append(f"  Final Gold:       {player.gold}")
    lines.append(f"  Final Reputation: {player.reputation:.2f}")
    lines.append(f"  Contracts Done:   {len(player.completed_ids)}")
    lines.append(f"  Contracts Failed: {len(player.failed_ids)}")
    lines.append(f"  Contracts Abandoned: {len(player.abandoned_ids)}")
    lines.append(f"  Final Skills:     {player.skills}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("  DAY-BY-DAY ACTION LOG:")
    lines.append("-" * 70)
    lines.append(f"  {'Day':>4} | {'Loc':>4} | {'Action':<16} | "
                 f"{'Gold':>6} | {'Rep':>6} | Details")
    lines.append("-" * 70)

    for entry in player.action_log:
        lines.append(
            f"  {entry['day']:>4} | {entry['location']:>4} | "
            f"{entry['action']:<16} | {entry['gold']:>6} | "
            f"{entry['reputation']:>6.1f} | {entry['details']}"
        )

    lines.append("-" * 70)
    return "\n".join(lines)


def generate_skill_progression_log(player: Player) -> str:
    """Generate the Skill Progression Log."""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  SKILL PROGRESSION LOG")
    lines.append("=" * 60)
    lines.append(f"  {'Day':>4} | {'Skill':<12} | {'Old':>3} -> {'New':>3} | Contract")
    lines.append("-" * 60)

    for entry in player.skill_log:
        lines.append(
            f"  {entry['day']:>4} | {entry['skill']:<12} | "
            f"{entry['old_level']:>3} -> {entry['new_level']:>3} | "
            f"{entry['from_contract']}"
        )

    lines.append("-" * 60)
    lines.append("")
    lines.append("  FINAL SKILL LEVELS:")
    for skill, level in player.skills.items():
        bar = "#" * level + "." * (10 - level)
        lines.append(f"    {skill:<12} [{bar}] {level}/10")
    lines.append("")
    return "\n".join(lines)


def generate_summary(player: Player) -> str:
    """Generate summary statistics."""
    lines = []
    lines.append("=" * 60)
    lines.append("  MISSION SUMMARY STATISTICS")
    lines.append("=" * 60)
    total_skill = sum(player.skills.values())
    days_used = max(1, player.current_day - 1)
    lines.append(f"  Total Gold Earned:       {player.gold}")
    lines.append(f"  Final Reputation:        {player.reputation:.2f}%")
    lines.append(f"  Total Skill Points:      {total_skill}")
    lines.append(f"  Contracts Completed:     {len(player.completed_ids)}")
    lines.append(f"  Contracts Failed:        {len(player.failed_ids)}")
    lines.append(f"  Contracts Abandoned:     {len(player.abandoned_ids)}")
    lines.append(f"  Days Used:               {days_used}")
    lines.append(f"  Gold/Day Efficiency:     {player.gold / days_used:.2f}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def run_from_json(map_json: dict, contracts_json: list,
                  beam_width: int = 6, look_ahead: int = 2,
                  seed: int = 42) -> Player:
    """Run the optimizer from JSON input data."""
    world_map = WorldMap.from_json(map_json, contracts_json)
    player = Player()
    player.location = map_json["cities"][0]

    optimizer = BeamSearchOptimizer(
        world_map, beam_width=beam_width,
        look_ahead=look_ahead, seed=seed
    )
    return optimizer.optimize(player)


def main():
    # Force UTF-8 on Windows
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n" + "=" * 60)
    print("  THE ZOLDYCK ASSASSINATION CONTRACT BOARD")
    print("  Optimization Engine v1.0")
    print("=" * 60 + "\n")

    # Run optimization
    result = run_from_json(
        DUMMY_MAP_DATA, DUMMY_CONTRACTS,
        beam_width=6, look_ahead=2, seed=42
    )

    # Generate and display reports
    path_report = generate_optimal_path_report(result)
    skill_report = generate_skill_progression_log(result)
    summary = generate_summary(result)

    print("\n" + path_report)
    print(skill_report)
    print(summary)

    # Save to files
    with open("optimal_path_report.txt", "w", encoding="utf-8") as f:
        f.write(path_report)
    with open("skill_progression_log.txt", "w", encoding="utf-8") as f:
        f.write(skill_report)
    with open("summary_stats.txt", "w", encoding="utf-8") as f:
        f.write(summary)

    world_map = WorldMap.from_json(DUMMY_MAP_DATA, DUMMY_CONTRACTS)
    with open("world_config.json", "w", encoding="utf-8") as f:
        json.dump(world_map.to_json(), f, indent=2)

    print("\n  Reports saved: optimal_path_report.txt, "
          "skill_progression_log.txt, summary_stats.txt, world_config.json\n")

    return result


if __name__ == "__main__":
    main()
