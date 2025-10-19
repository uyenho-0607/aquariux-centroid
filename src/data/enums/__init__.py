import random
from enum import Enum


class BaseEnum(str, Enum):
    """Base enum class that provides string representation functionality."""

    def __str__(self):
        return self.value

    @classmethod
    def list_values(cls, except_val=None):
        except_val = except_val if isinstance(except_val, list) else [except_val]
        return [item for item in cls if item not in except_val]

    @classmethod
    def sample_values(cls, amount=1, except_val=None):
        res = random.sample(cls.list_values(except_val), k=amount)
        return res[0] if amount == 1 else res

    @classmethod
    def random_values(cls, amount=1, except_val=None):
        res = random.choices(cls.list_values(except_val), k=amount)
        return res[0] if amount == 1 else res
