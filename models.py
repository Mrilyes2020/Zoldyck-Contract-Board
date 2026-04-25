"""
Zoldyck Assassination Contract Board - Data Models
Core OOP classes: Contract, Player, WorldMap
"""

import json
import math
import copy
from typing import Dict, List, Optional, Tuple, Set


class Contract:
    """Represents an assassination contract."""

    def __init__(self, contract_id: str, city: str, difficulty: int,
                 gold_reward: int, rep_reward: float, deadline: int,
                 execution_time: int, required_skill: str,
                 required_skill_level: int, is_trap: bool = False):
        self.contract_id = contract_id
        self.city = city
        self.difficulty = difficulty
        self.gold_reward = gold_reward
        self.rep_reward = rep_reward
        self.deadline = deadline
        self.execution_time = execution_time
        self.required_skill = required_skill
        self.required_skill_level = required_skill_level
        self.is_trap = is_trap

    def effective_difficulty(self) -> int:
        return self.difficulty + (1 if self.is_trap else 0)

    def buffered_execution_time(self) -> int:
        """Execution time with 50% buffer for complications."""
        return math.ceil(self.execution_time * 1.5)

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id, "city": self.city,
            "difficulty": self.difficulty, "gold_reward": self.gold_reward,
            "rep_reward": self.rep_reward, "deadline": self.deadline,
            "execution_time": self.execution_time,
            "required_skill": self.required_skill,
            "required_skill_level": self.required_skill_level,
            "is_trap": self.is_trap
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Contract':
        return cls(**data)

    def __repr__(self):
        return (f"Contract({self.contract_id}, city={self.city}, "
                f"diff={self.difficulty}, gold={self.gold_reward}, "
                f"deadline=D{self.deadline})")


class Player:
    """Tracks player state: time, location, gold, reputation, skills, queue."""

    SKILL_TYPES = ["stealth", "combat", "poison", "intel", "acrobatics"]
    MAX_QUEUE = 5
    MAX_DAYS = 200
    COMPLICATION_CHANCE = 0.20
    FAIL_PENALTY_RATE = 0.10

    def __init__(self):
        self.current_day: int = 1
        self.location: str = "A"
        self.gold: int = 0
        self.reputation: float = 100.0
        self.skills: Dict[str, int] = {s: 0 for s in self.SKILL_TYPES}
        self.active_contract_ids: List[str] = []  # IDs only
        self.completed_ids: Set[str] = set()
        self.failed_ids: Set[str] = set()
        self.abandoned_ids: Set[str] = set()
        self.action_log: List[dict] = []
        self.skill_log: List[dict] = []

    @property
    def days_remaining(self) -> int:
        return self.MAX_DAYS - self.current_day + 1

    @property
    def queue_slots_free(self) -> int:
        return self.MAX_QUEUE - len(self.active_contract_ids)

    @property
    def effective_reward_multiplier(self) -> float:
        return max(0.1, self.reputation / 100.0)

    def can_accept(self, contract_id: str) -> bool:
        if len(self.active_contract_ids) >= self.MAX_QUEUE:
            return False
        if contract_id in self.completed_ids:
            return False
        if contract_id in self.active_contract_ids:
            return False
        if contract_id in self.abandoned_ids:
            return False
        return True

    def complete_contract(self, contract: Contract):
        actual_gold = int(contract.gold_reward * self.effective_reward_multiplier)
        self.gold += actual_gold
        self.reputation = min(100.0, self.reputation + contract.rep_reward)
        skill = contract.required_skill
        old_level = self.skills[skill]
        xp_gain = contract.effective_difficulty() + 1
        self.skills[skill] = min(10, old_level + xp_gain)
        self.skill_log.append({
            "day": self.current_day, "skill": skill,
            "old_level": old_level, "new_level": self.skills[skill],
            "from_contract": contract.contract_id
        })
        self.completed_ids.add(contract.contract_id)
        if contract.contract_id in self.active_contract_ids:
            self.active_contract_ids.remove(contract.contract_id)

    def fail_contract(self, contract_id: str):
        self.reputation *= (1 - self.FAIL_PENALTY_RATE)
        self.failed_ids.add(contract_id)
        if contract_id in self.active_contract_ids:
            self.active_contract_ids.remove(contract_id)

    def abandon_contract(self, contract_id: str):
        self.reputation = max(0, self.reputation - 1)
        self.abandoned_ids.add(contract_id)
        if contract_id in self.active_contract_ids:
            self.active_contract_ids.remove(contract_id)

    def log_action(self, action: str, details: str = ""):
        self.action_log.append({
            "day": self.current_day, "location": self.location,
            "action": action, "details": details,
            "gold": self.gold, "reputation": round(self.reputation, 2)
        })

    def advance_day(self, days: int = 1):
        self.current_day += days

    def clone(self) -> 'Player':
        return copy.deepcopy(self)

    def state_summary(self) -> dict:
        return {
            "day": self.current_day, "location": self.location,
            "gold": self.gold, "reputation": round(self.reputation, 2),
            "skills": dict(self.skills),
            "active_contracts": len(self.active_contract_ids),
            "completed": len(self.completed_ids)
        }


class WorldMap:
    """Graph of cities with travel distances. Immutable reference data."""

    def __init__(self):
        self.cities: List[str] = []
        self.distances: Dict[Tuple[str, str], int] = {}
        self.contracts: Dict[str, Contract] = {}  # id -> Contract
        self.city_contract_ids: Dict[str, List[str]] = {}

    def add_city(self, city_id: str):
        if city_id not in self.cities:
            self.cities.append(city_id)
            self.city_contract_ids[city_id] = []

    def set_distance(self, city_a: str, city_b: str, days: int):
        self.distances[(city_a, city_b)] = days
        self.distances[(city_b, city_a)] = days

    def get_distance(self, city_a: str, city_b: str) -> int:
        if city_a == city_b:
            return 0
        return self.distances.get((city_a, city_b), 999)

    def add_contract(self, contract: Contract):
        self.contracts[contract.contract_id] = contract
        if contract.city not in self.city_contract_ids:
            self.city_contract_ids[contract.city] = []
        self.city_contract_ids[contract.city].append(contract.contract_id)

    def get_contract(self, contract_id: str) -> Optional[Contract]:
        return self.contracts.get(contract_id)

    def get_available_at_city(self, city: str, player: Player) -> List[Contract]:
        """Get contracts at city not yet completed/active/abandoned."""
        excluded = player.completed_ids | set(player.active_contract_ids) | player.abandoned_ids
        result = []
        for cid in self.city_contract_ids.get(city, []):
            if cid not in excluded:
                result.append(self.contracts[cid])
        return result

    def get_all_available(self, player: Player) -> List[Contract]:
        """Get all contracts across all cities that are still available."""
        excluded = player.completed_ids | set(player.active_contract_ids) | player.abandoned_ids
        return [c for cid, c in self.contracts.items() if cid not in excluded]

    @classmethod
    def from_json(cls, map_data: dict, contracts_data: list) -> 'WorldMap':
        wm = cls()
        for city in map_data["cities"]:
            wm.add_city(city)
        for edge in map_data["edges"]:
            wm.set_distance(edge["from"], edge["to"], edge["days"])
        for cd in contracts_data:
            wm.add_contract(Contract.from_dict(cd))
        return wm

    def to_json(self) -> dict:
        edges = []
        seen = set()
        for (a, b), d in self.distances.items():
            key = tuple(sorted([a, b]))
            if key not in seen:
                edges.append({"from": a, "to": b, "days": d})
                seen.add(key)
        contracts = [c.to_dict() for c in self.contracts.values()]
        return {"map": {"cities": self.cities, "edges": edges}, "contracts": contracts}
