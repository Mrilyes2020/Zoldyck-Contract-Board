"""
Zoldyck Assassination Contract Board - Optimizer Engine
Beam Search with Greedy Look-Ahead, phased heuristics, and risk management.
"""

import math
import random
from typing import List, Tuple
from models import Contract, Player, WorldMap


class ScoringHeuristic:
    """Phased scoring: skill farming (Phase 1) vs profit max (Phase 2)."""

    PHASE1_END = 50

    @classmethod
    def phase(cls, day: int) -> int:
        return 1 if day <= cls.PHASE1_END else 2

    @classmethod
    def score_contract(cls, contract: Contract, player: Player,
                       world_map: WorldMap, travel_days: int) -> float:
        """Score a single contract considering travel + execution cost."""
        phase = cls.phase(player.current_day)
        exec_time = contract.buffered_execution_time()
        total_time = travel_days + exec_time
        finish_day = player.current_day + total_time

        # Hard feasibility checks
        if finish_day > contract.deadline:
            return -1000.0
        if finish_day > Player.MAX_DAYS:
            return -1000.0

        score = 0.0

        if phase == 1:
            # === PHASE 1: SKILL FARMING ===
            ease_bonus = max(0, 5 - contract.difficulty) * 3.0

            # Diversity: boost skills we haven't leveled
            current_skill = player.skills.get(contract.required_skill, 0)
            diversity_bonus = 4.0 if current_skill == 0 else (2.0 if current_skill < 2 else 0.5)

            # Time efficiency
            efficiency = (contract.gold_reward * 0.3 + ease_bonus * 5) / max(1, total_time)

            # Cluster bonus: prefer nearby
            cluster_bonus = max(0, 5 - travel_days) * 1.0

            score = ease_bonus + diversity_bonus + cluster_bonus + efficiency

            # Penalize if we lack skill
            skill_gap = contract.required_skill_level - current_skill
            if contract.is_trap:
                skill_gap += 1
            if skill_gap > 0:
                score -= skill_gap * 4.0

        else:
            # === PHASE 2: PROFIT MAXIMIZATION ===
            effective_gold = contract.gold_reward * player.effective_reward_multiplier
            rep_bonus = contract.rep_reward * 1.5

            profit_efficiency = effective_gold / max(1, total_time)

            # Deadline urgency
            days_left = contract.deadline - player.current_day
            urgency = 10.0 / max(1, days_left) if days_left > 0 else 0

            score = profit_efficiency * 2.0 + rep_bonus + urgency

            # Skill check
            current_skill = player.skills.get(contract.required_skill, 0)
            effective_req = contract.required_skill_level + (1 if contract.is_trap else 0)
            skill_surplus = current_skill - effective_req
            if skill_surplus >= 0:
                score += skill_surplus * 0.5
            else:
                score -= abs(skill_surplus) * 3.0

        # Trap penalty
        if contract.is_trap:
            score -= 5.0

        return score


class TrapHandler:
    """Handles trap detection and abandon-vs-fail decision logic."""

    @staticmethod
    def should_abandon(contract: Contract, player: Player) -> bool:
        if not contract.is_trap:
            return False

        effective_req = contract.required_skill_level + 1
        current_skill = player.skills.get(contract.required_skill, 0)

        if current_skill < effective_req - 1:
            abandon_cost = 1.0
            fail_cost = player.reputation * Player.FAIL_PENALTY_RATE
            gap = effective_req - current_skill
            failure_prob = min(0.95, 0.3 + gap * 0.2)
            expected_fail_cost = failure_prob * fail_cost
            if expected_fail_cost > abandon_cost * 1.5:
                return True

        return False


class BeamSearchOptimizer:
    """
    Beam Search with greedy look-ahead.
    At each step, generates candidate next-actions, simulates them,
    scores the resulting states, and keeps the top beam_width states.
    """

    def __init__(self, world_map: WorldMap, beam_width: int = 6,
                 look_ahead: int = 2, seed: int = 42):
        self.world_map = world_map
        self.beam_width = beam_width
        self.look_ahead = look_ahead
        self.rng = random.Random(seed)

    def _get_candidate_actions(self, player: Player) -> List[dict]:
        """Generate all possible next-step actions."""
        actions = []

        # Collect contracts from ALL cities (travel + execute)
        for city in self.world_map.cities:
            travel = self.world_map.get_distance(player.location, city)
            available = self.world_map.get_available_at_city(city, player)

            for contract in available:
                if not player.can_accept(contract.contract_id):
                    continue
                score = ScoringHeuristic.score_contract(
                    contract, player, self.world_map, travel)
                if score > -500:
                    actions.append({
                        "type": "go_and_execute",
                        "contract_id": contract.contract_id,
                        "city": city,
                        "travel_days": travel,
                        "score": score
                    })

        if not actions:
            actions.append({"type": "idle", "score": -100})

        return sorted(actions, key=lambda a: a["score"], reverse=True)

    def _simulate_action(self, player: Player, action: dict) -> Player:
        """Execute an action on a cloned player, return new state."""
        p = player.clone()

        if action["type"] == "go_and_execute":
            cid = action["contract_id"]
            city = action["city"]
            travel = action["travel_days"]
            contract = self.world_map.get_contract(cid)

            # Travel
            if travel > 0:
                p.log_action("TRAVEL", f"Traveling to {city} ({travel} days)")
                p.advance_day(travel)
                p.location = city

            # Accept
            p.active_contract_ids.append(cid)

            # Trap check
            if contract.is_trap and TrapHandler.should_abandon(contract, p):
                p.abandon_contract(cid)
                p.log_action("ABANDON_TRAP",
                            f"Abandoned trap {cid} (-1 rep)")
                p.advance_day(1)
                return p

            # Execute with buffered time (deterministic planning)
            exec_time = contract.buffered_execution_time()
            p.advance_day(exec_time)

            if p.current_day <= contract.deadline and p.current_day <= Player.MAX_DAYS:
                p.complete_contract(contract)
                p.log_action("COMPLETE",
                            f"Completed {cid} "
                            f"(+{int(contract.gold_reward * player.effective_reward_multiplier)}g, "
                            f"+{contract.rep_reward}rep)")
            else:
                p.fail_contract(cid)
                p.log_action("FAIL", f"Failed {cid} - deadline exceeded")

        elif action["type"] == "idle":
            p.log_action("WAIT", "No viable contracts")
            p.advance_day(1)

        return p

    def _evaluate_state(self, player: Player) -> float:
        """Score overall player state quality."""
        gold_score = player.gold * 1.0
        rep_score = player.reputation * 2.0
        skill_score = sum(player.skills.values()) * 5.0
        completed_score = len(player.completed_ids) * 15.0
        time_penalty = max(0, player.current_day - Player.MAX_DAYS) * 50

        # Bonus for remaining potential (contracts still doable)
        remaining = self.world_map.get_all_available(player)
        potential = sum(c.gold_reward * 0.1 for c in remaining
                       if c.deadline >= player.current_day)

        return gold_score + rep_score + skill_score + completed_score + potential - time_penalty

    def _look_ahead_eval(self, player: Player, depth: int) -> float:
        """Quick recursive look-ahead to estimate future value."""
        if depth <= 0 or player.current_day > Player.MAX_DAYS:
            return self._evaluate_state(player)

        actions = self._get_candidate_actions(player)
        if not actions or actions[0]["type"] == "idle":
            return self._evaluate_state(player)

        # Only check top 2 for speed
        best = -float('inf')
        for action in actions[:2]:
            new_state = self._simulate_action(player, action)
            score = self._look_ahead_eval(new_state, depth - 1)
            best = max(best, score)
        return best

    def optimize(self, player: Player) -> Player:
        """Run beam search to find optimal action sequence."""
        print("=" * 60)
        print("  ZOLDYCK OPTIMIZATION ENGINE - BEAM SEARCH")
        print("=" * 60)
        print(f"  Beam Width: {self.beam_width} | Look-Ahead: {self.look_ahead}")
        print(f"  Starting: Day {player.current_day}, City {player.location}")
        print(f"  Available Contracts: {len(self.world_map.contracts)}")
        print("=" * 60)

        beam: List[Player] = [player.clone()]
        iteration = 0

        while iteration < 500:  # Safety limit
            iteration += 1
            candidates: List[Tuple[float, Player]] = []

            any_active = False
            for state in beam:
                if state.current_day > Player.MAX_DAYS:
                    candidates.append((self._evaluate_state(state), state))
                    continue

                actions = self._get_candidate_actions(state)
                if not actions or (len(actions) == 1 and actions[0]["type"] == "idle"):
                    # No more useful actions - fast forward to end
                    s = state.clone()
                    s.current_day = Player.MAX_DAYS + 1
                    candidates.append((self._evaluate_state(s), s))
                    continue

                any_active = True
                top_n = actions[:self.beam_width]
                for action in top_n:
                    new_state = self._simulate_action(state, action)
                    score = self._evaluate_state(new_state)
                    # Look-ahead bonus
                    if self.look_ahead > 0 and new_state.current_day <= Player.MAX_DAYS:
                        la = self._look_ahead_eval(new_state, self.look_ahead - 1)
                        score = score * 0.6 + la * 0.4
                    candidates.append((score, new_state))

            if not any_active:
                break

            # Keep top beam_width
            candidates.sort(key=lambda x: x[0], reverse=True)
            beam = [s for _, s in candidates[:self.beam_width]]

            best = beam[0]
            if iteration % 5 == 0:
                print(f"  [Step {iteration:3d}] Day {best.current_day:3d} | "
                      f"Gold: {best.gold:6d} | Rep: {best.reputation:5.1f} | "
                      f"Done: {len(best.completed_ids):2d} | "
                      f"Skills: {sum(best.skills.values()):2d}")

            if all(s.current_day > Player.MAX_DAYS for s in beam):
                break

        beam.sort(key=lambda s: self._evaluate_state(s), reverse=True)
        best_result = beam[0]
        print(f"\n  Optimization complete after {iteration} steps.")
        print(f"  Final Score: {self._evaluate_state(best_result):.1f}")
        return best_result
