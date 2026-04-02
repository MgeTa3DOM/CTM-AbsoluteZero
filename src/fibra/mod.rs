//! Fibra Runtime Library
//! Golden Angle Task Scheduler for zero-deadlock AI agent execution

pub mod scheduler;

pub use scheduler::{
    FibraScheduler,
    FibonacciCache,
    TaskSlot,
    FibraAuditEntry,
    FibraEvent,
    GOLDEN_ANGLE,
    PHI,
    FIBONACCI_TIMEOUTS_MS,
    MAX_AGENTS,
};
