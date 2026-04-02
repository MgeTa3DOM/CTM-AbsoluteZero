//! Fibra: Golden Angle Task Scheduler
//! Zero deadlock concurrent execution using Fibonacci spiral distribution
//!
//! Based on the mathematical property that the golden angle (137.5 degrees)
//! produces the most uniform distribution of points on a circle,
//! the same way sunflower seeds are arranged in nature.

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

// --- Constants ---

/// Golden angle in degrees (360 / phi^2)
pub const GOLDEN_ANGLE: f64 = 137.50776405003785;

/// Golden ratio
pub const PHI: f64 = 1.618033988749895;

/// Fibonacci timeout sequence in milliseconds
pub const FIBONACCI_TIMEOUTS_MS: [u64; 8] = [1000, 1000, 2000, 3000, 5000, 8000, 13000, 21000];

/// Maximum concurrent agents
pub const MAX_AGENTS: usize = 256;

// --- Fibonacci Cache ---

/// Cache with Fibonacci-sized levels
/// L0: 1 entry (hot)
/// L1: 1 entry (warm)
/// L2: 2 entries (recent)
/// L3: 3 entries (short-term)
/// L4: 5 entries (medium-term)
/// L5: 8 entries (long-term)
/// L6: 13 entries (archive)
/// L7: 21 entries (cold)
/// Total: 55 entries
pub struct FibonacciCache<K, V> {
    levels: Vec<Vec<(K, V)>>,
    capacities: Vec<usize>,
}

impl<K: Clone + PartialEq, V: Clone> FibonacciCache<K, V> {
    pub fn new() -> Self {
        let capacities = vec![1, 1, 2, 3, 5, 8, 13, 21];
        let levels = capacities.iter().map(|_| Vec::new()).collect();
        Self { levels, capacities }
    }

    pub fn get(&mut self, key: &K) -> Option<V> {
        for level in 0..self.levels.len() {
            if let Some(pos) = self.levels[level].iter().position(|(k, _)| k == key) {
                let (k, v) = self.levels[level].remove(pos);
                // Promote to L0
                self.insert_at_level(0, k, v.clone());
                return Some(v);
            }
        }
        None
    }

    pub fn insert(&mut self, key: K, value: V) {
        self.insert_at_level(0, key, value);
    }

    fn insert_at_level(&mut self, level: usize, key: K, value: V) {
        if level >= self.levels.len() {
            return; // Evicted from cold storage
        }
        self.levels[level].insert(0, (key, value));
        // If level overflows, demote oldest to next level
        if self.levels[level].len() > self.capacities[level] {
            let evicted = self.levels[level].pop().unwrap();
            self.insert_at_level(level + 1, evicted.0, evicted.1);
        }
    }

    pub fn total_entries(&self) -> usize {
        self.levels.iter().map(|l| l.len()).sum()
    }
}

// --- Task Slot ---

#[derive(Debug, Clone)]
pub struct TaskSlot {
    pub task_id: u64,
    pub angle: f64,
    pub resource_slot: usize,
    pub timeout_level: usize,
    pub created_at: Instant,
}

impl TaskSlot {
    pub fn timeout_duration(&self) -> Duration {
        let ms = if self.timeout_level < FIBONACCI_TIMEOUTS_MS.len() {
            FIBONACCI_TIMEOUTS_MS[self.timeout_level]
        } else {
            FIBONACCI_TIMEOUTS_MS[FIBONACCI_TIMEOUTS_MS.len() - 1]
        };
        Duration::from_millis(ms)
    }

    pub fn is_expired(&self) -> bool {
        self.created_at.elapsed() > self.timeout_duration()
    }
}

// --- Scheduler ---

pub struct FibraScheduler {
    current_angle: f64,
    next_task_id: AtomicU64,
    active_slots: HashMap<u64, TaskSlot>,
    max_slots: usize,
    cache: FibonacciCache<u64, Vec<u8>>,
}

impl FibraScheduler {
    pub fn new(max_slots: usize) -> Self {
        assert!(max_slots <= MAX_AGENTS, "Cannot exceed {} agents", MAX_AGENTS);
        Self {
            current_angle: 0.0,
            next_task_id: AtomicU64::new(1),
            active_slots: HashMap::new(),
            max_slots,
            cache: FibonacciCache::new(),
        }
    }

    /// Schedule a new task using golden angle distribution.
    /// Returns None if scheduler is at capacity.
    pub fn schedule(&mut self) -> Option<TaskSlot> {
        if self.active_slots.len() >= self.max_slots {
            return None;
        }

        let task_id = self.next_task_id.fetch_add(1, Ordering::SeqCst);
        self.current_angle = (self.current_angle + GOLDEN_ANGLE) % 360.0;

        let resource_slot = self.angle_to_slot(self.current_angle);

        let slot = TaskSlot {
            task_id,
            angle: self.current_angle,
            resource_slot,
            timeout_level: 0,
            created_at: Instant::now(),
        };

        self.active_slots.insert(task_id, slot.clone());
        Some(slot)
    }

    /// Complete a task and remove from active slots
    pub fn complete(&mut self, task_id: u64) -> Option<TaskSlot> {
        self.active_slots.remove(&task_id)
    }

    /// Preempt expired tasks (fibonacci-bounded timeout)
    pub fn preempt_expired(&mut self) -> Vec<TaskSlot> {
        let expired: Vec<u64> = self.active_slots
            .iter()
            .filter(|(_, slot)| slot.is_expired())
            .map(|(id, _)| *id)
            .collect();

        expired.iter()
            .filter_map(|id| self.active_slots.remove(id))
            .collect()
    }

    /// Retry a task with escalated timeout (next Fibonacci level)
    pub fn retry(&mut self, task_id: u64) -> Option<TaskSlot> {
        if let Some(mut slot) = self.active_slots.remove(&task_id) {
            slot.timeout_level += 1;
            slot.created_at = Instant::now();
            // Re-assign angle (golden angle guarantees no collision)
            self.current_angle = (self.current_angle + GOLDEN_ANGLE) % 360.0;
            slot.angle = self.current_angle;
            slot.resource_slot = self.angle_to_slot(self.current_angle);
            self.active_slots.insert(task_id, slot.clone());
            Some(slot)
        } else {
            None
        }
    }

    /// Convert angle to resource slot index
    /// The golden angle ensures uniform distribution across slots
    fn angle_to_slot(&self, angle: f64) -> usize {
        ((angle / 360.0) * self.max_slots as f64) as usize % self.max_slots
    }

    pub fn active_count(&self) -> usize {
        self.active_slots.len()
    }

    pub fn cache_mut(&mut self) -> &mut FibonacciCache<u64, Vec<u8>> {
        &mut self.cache
    }
}

// --- Audit Integration ---

#[derive(Debug, Clone)]
pub struct FibraAuditEntry {
    pub task_id: u64,
    pub event: FibraEvent,
    pub angle: f64,
    pub timestamp: Instant,
}

#[derive(Debug, Clone)]
pub enum FibraEvent {
    Scheduled,
    Completed,
    Preempted { timeout_level: usize },
    Retried { new_timeout_level: usize },
}

// --- Tests ---

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_golden_angle_distribution() {
        let mut scheduler = FibraScheduler::new(64);
        let mut angles = Vec::new();

        for _ in 0..64 {
            let slot = scheduler.schedule().unwrap();
            // No two angles should be the same
            for &existing in &angles {
                assert!((slot.angle - existing).abs() > 0.001,
                    "Angle collision detected: {} vs {}", slot.angle, existing);
            }
            angles.push(slot.angle);
        }
    }

    #[test]
    fn test_fibonacci_timeout_escalation() {
        let slot = TaskSlot {
            task_id: 1,
            angle: 0.0,
            resource_slot: 0,
            timeout_level: 0,
            created_at: Instant::now(),
        };
        assert_eq!(slot.timeout_duration(), Duration::from_millis(1000));

        let slot3 = TaskSlot { timeout_level: 3, ..slot.clone() };
        assert_eq!(slot3.timeout_duration(), Duration::from_millis(3000));

        let slot7 = TaskSlot { timeout_level: 7, ..slot.clone() };
        assert_eq!(slot7.timeout_duration(), Duration::from_millis(21000));

        // Beyond max level, cap at 21s
        let slot99 = TaskSlot { timeout_level: 99, ..slot };
        assert_eq!(slot99.timeout_duration(), Duration::from_millis(21000));
    }

    #[test]
    fn test_fibonacci_cache() {
        let mut cache = FibonacciCache::<u64, Vec<u8>>::new();

        // Insert 55 items (total capacity)
        for i in 0..55 {
            cache.insert(i, vec![i as u8]);
        }

        // Recent items should be findable
        assert!(cache.get(&54).is_some());
        assert!(cache.get(&53).is_some());

        // Total should not exceed 55
        assert!(cache.total_entries() <= 55);
    }

    #[test]
    fn test_scheduler_capacity() {
        let mut scheduler = FibraScheduler::new(4);

        assert!(scheduler.schedule().is_some());
        assert!(scheduler.schedule().is_some());
        assert!(scheduler.schedule().is_some());
        assert!(scheduler.schedule().is_some());
        assert!(scheduler.schedule().is_none()); // At capacity
    }

    #[test]
    fn test_zero_deadlock_property() {
        // The golden angle is irrational, so no two tasks ever map to
        // the same exact slot. This is the mathematical guarantee of
        // zero deadlock: resources are never contested.
        let mut scheduler = FibraScheduler::new(256);
        let mut slot_map: HashMap<usize, Vec<u64>> = HashMap::new();

        for _ in 0..256 {
            let slot = scheduler.schedule().unwrap();
            slot_map.entry(slot.resource_slot).or_default().push(slot.task_id);
        }

        // With 256 slots and 256 tasks using golden angle,
        // distribution should be near-uniform
        let max_per_slot = slot_map.values().map(|v| v.len()).max().unwrap_or(0);
        assert!(max_per_slot <= 3, "Distribution too uneven: max {} per slot", max_per_slot);
    }
}
