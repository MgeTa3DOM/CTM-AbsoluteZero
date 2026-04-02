//! Clarity: Controlled Language for AI Runtime & Integrity Transparency Yield
//!
//! Core library for transparent, auditable AI code.

pub mod types;

pub use types::{
    Decision,
    AuditEntry,
    AgentCapabilities,
    Capability,
    Action,
    Scope,
    WormWriter,
    VaultProxy,
    VaultError,
};
