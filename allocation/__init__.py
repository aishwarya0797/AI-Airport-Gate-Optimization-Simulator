"""Allocation module for gate assignment."""
from .gate_allocator import RuleBasedAllocator, NaiveAllocator, AllocationResult
from .conflict_detector import ConflictDetector, Conflict
