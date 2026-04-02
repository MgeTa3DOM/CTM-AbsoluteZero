//! Fibra — Golden-angle task scheduler.
//!
//! Distributes work across resource slots using the irrational golden angle
//! (≈137.508°) so that no two consecutive tasks ever collide.  Timeouts
//! follow the Fibonacci sequence: 1 1 2 3 5 8 13 21 seconds.

use std::collections::HashMap;
use std::time::{Duration, Instant};

pub const GOLDEN_ANGLE: f64 = 137.507_764_050_037_85;
const FIB_MS: [u64; 8] = [1000, 1000, 2000, 3000, 5000, 8000, 13000, 21000];

/// One scheduled task.
#[derive(Debug, Clone)]
pub struct Task {
    pub id: u64,
    pub angle: f64,
    pub slot: usize,
    pub timeout_level: usize,
    pub born: Instant,
}

impl Task {
    pub fn timeout(&self) -> Duration {
        let idx = self.timeout_level.min(FIB_MS.len() - 1);
        Duration::from_millis(FIB_MS[idx])
    }

    pub fn expired(&self) -> bool {
        self.born.elapsed() > self.timeout()
    }
}

/// Fibonacci-shaped multi-level cache.
///
/// Capacities per level: 1 1 2 3 5 8 13 21 = 55 entries total.
/// Evicted items cascade to the next (colder) level.
pub struct FibCache<K: Eq + Clone, V: Clone> {
    levels: Vec<Vec<(K, V)>>,
    caps: Vec<usize>,
}

impl<K: Eq + Clone, V: Clone> FibCache<K, V> {
    pub fn new() -> Self {
        let caps = vec![1, 1, 2, 3, 5, 8, 13, 21];
        let levels = caps.iter().map(|_| Vec::new()).collect();
        Self { levels, caps }
    }

    pub fn get(&mut self, key: &K) -> Option<V> {
        for lvl in 0..self.levels.len() {
            if let Some(pos) = self.levels[lvl].iter().position(|(k, _)| k == key) {
                let (k, v) = self.levels[lvl].remove(pos);
                self.put_at(0, k, v.clone());
                return Some(v);
            }
        }
        None
    }

    pub fn put(&mut self, key: K, val: V) {
        self.put_at(0, key, val);
    }

    fn put_at(&mut self, lvl: usize, key: K, val: V) {
        if lvl >= self.levels.len() {
            return;
        }
        self.levels[lvl].insert(0, (key, val));
        if self.levels[lvl].len() > self.caps[lvl] {
            let evicted = self.levels[lvl].pop().unwrap();
            self.put_at(lvl + 1, evicted.0, evicted.1);
        }
    }

    pub fn len(&self) -> usize {
        self.levels.iter().map(Vec::len).sum()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

impl<K: Eq + Clone, V: Clone> Default for FibCache<K, V> {
    fn default() -> Self {
        Self::new()
    }
}

/// The scheduler itself.
pub struct Scheduler {
    angle: f64,
    next_id: u64,
    active: HashMap<u64, Task>,
    slots: usize,
}

impl Scheduler {
    pub fn new(slots: usize) -> Self {
        assert!(slots > 0 && slots <= 256);
        Self { angle: 0.0, next_id: 1, active: HashMap::new(), slots }
    }

    /// Schedule a new task. Returns `None` when full.
    pub fn schedule(&mut self) -> Option<Task> {
        if self.active.len() >= self.slots {
            return None;
        }
        let id = self.next_id;
        self.next_id += 1;
        self.angle = (self.angle + GOLDEN_ANGLE) % 360.0;
        let slot = ((self.angle / 360.0) * self.slots as f64) as usize % self.slots;
        let t = Task { id, angle: self.angle, slot, timeout_level: 0, born: Instant::now() };
        self.active.insert(id, t.clone());
        Some(t)
    }

    /// Mark a task as completed.
    pub fn complete(&mut self, id: u64) -> Option<Task> {
        self.active.remove(&id)
    }

    /// Sweep expired tasks and return them.
    pub fn reap(&mut self) -> Vec<Task> {
        let expired: Vec<u64> = self.active.iter()
            .filter(|(_, t)| t.expired())
            .map(|(id, _)| *id)
            .collect();
        expired.iter().filter_map(|id| self.active.remove(id)).collect()
    }

    /// Retry with escalated Fibonacci timeout.
    pub fn retry(&mut self, id: u64) -> Option<Task> {
        if let Some(mut t) = self.active.remove(&id) {
            t.timeout_level += 1;
            t.born = Instant::now();
            self.angle = (self.angle + GOLDEN_ANGLE) % 360.0;
            t.angle = self.angle;
            t.slot = ((self.angle / 360.0) * self.slots as f64) as usize % self.slots;
            self.active.insert(id, t.clone());
            Some(t)
        } else {
            None
        }
    }

    pub fn active_count(&self) -> usize {
        self.active.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_angle_collision() {
        let mut s = Scheduler::new(64);
        let mut angles: Vec<f64> = Vec::new();
        for _ in 0..64 {
            let t = s.schedule().unwrap();
            for &a in &angles {
                let diff = (t.angle - a).abs();
                assert!(diff > 0.01, "collision {:.3} vs {:.3}", t.angle, a);
            }
            angles.push(t.angle);
        }
    }

    #[test]
    fn capacity_respected() {
        let mut s = Scheduler::new(4);
        for _ in 0..4 { assert!(s.schedule().is_some()); }
        assert!(s.schedule().is_none());
    }

    #[test]
    fn fibonacci_timeout_escalation() {
        let mut s = Scheduler::new(8);
        let t = s.schedule().unwrap();
        assert_eq!(t.timeout(), Duration::from_millis(1000));
        let t = s.retry(t.id).unwrap();
        assert_eq!(t.timeout(), Duration::from_millis(1000));
        let t = s.retry(t.id).unwrap();
        assert_eq!(t.timeout(), Duration::from_millis(2000));
        let t = s.retry(t.id).unwrap();
        assert_eq!(t.timeout(), Duration::from_millis(3000));
    }

    #[test]
    fn uniform_distribution() {
        let mut s = Scheduler::new(256);
        let mut slot_counts = vec![0usize; 256];
        for _ in 0..256 {
            let t = s.schedule().unwrap();
            slot_counts[t.slot] += 1;
        }
        let max = *slot_counts.iter().max().unwrap();
        assert!(max <= 3, "max {max} per slot, expected ≤3");
    }

    #[test]
    fn cache_eviction_cascade() {
        let mut c = FibCache::<u32, u32>::new();
        for i in 0..60 {
            c.put(i, i * 10);
        }
        assert!(c.len() <= 55);
        // Recent items accessible
        assert!(c.get(&59).is_some());
    }
}
