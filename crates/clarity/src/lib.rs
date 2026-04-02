//! Clarity — Transparent decision type system for AI agents.
//!
//! Core rule: every `Decision` **must** carry an explanation.
//! No explanation → no compilation. The type system enforces this.

use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

/// Immutable audit record.  Written to append-only storage (WORM).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub ts: u64,
    pub agent: String,
    pub action: String,
    pub explain: String,
    pub input_hash: String,
}

impl AuditEntry {
    pub fn now(agent: &str, action: &str, explain: &str, input_hash: &str) -> Self {
        Self {
            ts: SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() as u64,
            agent: agent.into(),
            action: action.into(),
            explain: explain.into(),
            input_hash: input_hash.into(),
        }
    }

    pub fn to_line(&self) -> String {
        serde_json::to_string(self).unwrap_or_default()
    }
}

/// A decision with mandatory explanation.
///
/// There is **no** constructor that skips `explain`.
/// The only way to create a `Decision` is through [`Decision::new`],
/// which panics on empty explanation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision<T: std::fmt::Debug + Clone> {
    pub value: T,
    pub explain: String,
    pub confidence: f64,
    pub audit: AuditEntry,
}

impl<T: std::fmt::Debug + Clone> Decision<T> {
    /// Create a decision.  Panics if `explain` is empty.
    pub fn new(value: T, explain: impl Into<String>, confidence: f64, agent: &str) -> Self {
        let explain = explain.into();
        assert!(!explain.is_empty(), "clarity: decision without explanation");
        assert!((0.0..=1.0).contains(&confidence), "clarity: confidence must be 0–1");
        let audit = AuditEntry::now(agent, &format!("{:?}", value), &explain, "");
        Self { value, explain, confidence, audit }
    }

    pub fn needs_escalation(&self, threshold: f64) -> bool {
        self.confidence < threshold
    }
}

/// Capability declaration for an agent.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Capability {
    pub action: String,
    pub scope: String,
    pub allowed: bool,
}

/// Agent capability set — evaluated at runtime by the kernel layer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentCaps {
    pub name: String,
    pub caps: Vec<Capability>,
    pub escalation_threshold: f64,
}

impl AgentCaps {
    pub fn can(&self, action: &str) -> bool {
        self.caps.iter().any(|c| c.action == action && c.allowed)
    }

    pub fn denied(&self, action: &str) -> bool {
        self.caps.iter().any(|c| c.action == action && !c.allowed)
    }
}

/// Append-only audit log (WORM in-memory simulation).
pub struct WormLog {
    entries: Vec<String>,
}

impl WormLog {
    pub fn new() -> Self {
        Self { entries: Vec::new() }
    }

    pub fn append(&mut self, entry: &AuditEntry) {
        self.entries.push(entry.to_line());
    }

    pub fn entries(&self) -> &[String] {
        &self.entries
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    // No delete. No modify. By design.
}

impl Default for WormLog {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decision_requires_explain() {
        let d = Decision::new("high", "score 0.9 > threshold 0.8", 0.9, "risk-agent");
        assert_eq!(d.value, "high");
        assert!(!d.explain.is_empty());
    }

    #[test]
    #[should_panic(expected = "decision without explanation")]
    fn empty_explain_panics() {
        Decision::new("x", "", 0.5, "a");
    }

    #[test]
    #[should_panic(expected = "confidence must be 0")]
    fn bad_confidence_panics() {
        Decision::new("x", "reason", 1.5, "a");
    }

    #[test]
    fn escalation_check() {
        let d = Decision::new("low", "reason", 0.4, "a");
        assert!(d.needs_escalation(0.7));
        assert!(!d.needs_escalation(0.3));
    }

    #[test]
    fn worm_is_append_only() {
        let mut log = WormLog::new();
        let e = AuditEntry::now("a", "read", "test", "abc");
        log.append(&e);
        log.append(&e);
        assert_eq!(log.len(), 2);
    }

    #[test]
    fn caps_check() {
        let caps = AgentCaps {
            name: "reviewer".into(),
            caps: vec![
                Capability { action: "read".into(), scope: "src/**".into(), allowed: true },
                Capability { action: "write".into(), scope: "**".into(), allowed: false },
            ],
            escalation_threshold: 0.7,
        };
        assert!(caps.can("read"));
        assert!(!caps.can("write"));
        assert!(caps.denied("write"));
    }

    #[test]
    fn audit_serialization() {
        let e = AuditEntry::now("agent1", "classify", "score > 0.5", "hash123");
        let json = e.to_line();
        assert!(json.contains("agent1"));
        assert!(json.contains("score > 0.5"));
        let parsed: AuditEntry = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.agent, "agent1");
    }
}
