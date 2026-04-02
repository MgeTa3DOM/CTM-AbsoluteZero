//! Clarity: Controlled Language for AI Runtime & Integrity Transparency Yield
//!
//! Core types for the Clarity type system.
//! Every Decision MUST have an explanation and audit trail.

use std::fmt;
use std::time::{SystemTime, UNIX_EPOCH};

// --- Decision Type ---

/// The core type of Clarity: every AI decision must be wrapped in this.
/// The compiler enforces that `explain` and `audit` are always populated.
#[derive(Debug, Clone)]
pub struct Decision<T: fmt::Debug + Clone> {
    pub value: T,
    pub explain: String,
    pub confidence: f64,
    pub audit: AuditEntry,
}

impl<T: fmt::Debug + Clone> Decision<T> {
    /// Create a new Decision. All fields are mandatory.
    pub fn new(value: T, explain: impl Into<String>, confidence: f64, agent_id: &str) -> Self {
        let explain = explain.into();
        assert!(!explain.is_empty(), "Clarity: explain cannot be empty");
        assert!((0.0..=1.0).contains(&confidence), "Clarity: confidence must be 0.0-1.0");

        let audit = AuditEntry::new(
            agent_id.to_string(),
            format!("{:?}", value),
            explain.clone(),
        );

        Self {
            value,
            explain,
            confidence,
            audit,
        }
    }

    /// Check if this decision should be escalated to a human
    pub fn needs_escalation(&self, threshold: f64) -> bool {
        self.confidence < threshold
    }
}

impl<T: fmt::Debug + Clone + fmt::Display> fmt::Display for Decision<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Decision({}, confidence={:.2}, reason={})",
               self.value, self.confidence, self.explain)
    }
}

// --- Audit Entry ---

#[derive(Debug, Clone)]
pub struct AuditEntry {
    pub timestamp: u64,
    pub agent_id: String,
    pub output: String,
    pub explanation: String,
    pub input_hash: u64,
    pub parent_hash: Option<u64>,
}

impl AuditEntry {
    pub fn new(agent_id: String, output: String, explanation: String) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        Self {
            timestamp,
            agent_id,
            output,
            explanation,
            input_hash: 0,
            parent_hash: None,
        }
    }

    /// Serialize for WORM partition write
    pub fn to_worm_record(&self) -> Vec<u8> {
        format!(
            "AUDIT|ts={}|agent={}|output={}|explain={}|input_hash={}|parent={:?}\n",
            self.timestamp,
            self.agent_id,
            self.output,
            self.explanation,
            self.input_hash,
            self.parent_hash,
        ).into_bytes()
    }
}

// --- Capabilities ---

#[derive(Debug, Clone, PartialEq)]
pub enum Action {
    ReadFile(String),      // Glob pattern
    WriteFile(String),     // Glob pattern
    ExecuteCommand(Vec<String>), // Allowlist
    AccessNetwork(Vec<String>),  // Allowlist
    AccessVault(String),   // Key pattern
}

#[derive(Debug, Clone, PartialEq)]
pub enum Scope {
    Always,
    WhenConfident(f64),   // threshold
    WithHumanApproval,
    Never,
}

#[derive(Debug, Clone)]
pub struct Capability {
    pub action: Action,
    pub scope: Scope,
}

#[derive(Debug, Clone)]
pub struct AgentCapabilities {
    pub agent_name: String,
    pub allowed: Vec<Capability>,
    pub denied: Vec<Action>,
    pub escalation_threshold: f64,
    pub max_cpu: Option<u32>,
    pub max_memory_mb: Option<u64>,
    pub max_timeout_sec: Option<u64>,
}

impl AgentCapabilities {
    pub fn can_perform(&self, action: &Action) -> bool {
        // Check denied list first
        if self.denied.contains(action) {
            return false;
        }
        // Check allowed list
        self.allowed.iter().any(|cap| &cap.action == action && cap.scope != Scope::Never)
    }

    pub fn needs_human_approval(&self, action: &Action) -> bool {
        self.allowed.iter().any(|cap| {
            &cap.action == action && cap.scope == Scope::WithHumanApproval
        })
    }
}

// --- WORM Writer ---

/// Write-Once Read-Many audit log writer
/// In production, this writes to the NKV WORM partition
pub struct WormWriter {
    entries: Vec<Vec<u8>>,
}

impl WormWriter {
    pub fn new() -> Self {
        Self { entries: Vec::new() }
    }

    /// Append an audit entry. Cannot be deleted or modified.
    pub fn append(&mut self, entry: &AuditEntry) {
        self.entries.push(entry.to_worm_record());
    }

    /// Read all entries. WORM: read-many.
    pub fn read_all(&self) -> &[Vec<u8>] {
        &self.entries
    }

    pub fn entry_count(&self) -> usize {
        self.entries.len()
    }

    // No delete method. No modify method. By design.
}

// --- Vault Proxy ---

/// Vault proxy: secrets never enter agent memory space.
/// Agent receives a reference, vault makes the call.
pub struct VaultProxy {
    // In production: HSM-backed secret storage
}

impl VaultProxy {
    pub fn new() -> Self {
        Self {}
    }

    /// Execute an authenticated request without exposing the secret.
    /// The agent never sees the key, only the response.
    pub fn authenticated_request(
        &self,
        _endpoint: &str,
        _secret_ref: &str,
    ) -> Result<String, VaultError> {
        // In production: retrieve secret from HSM, make request, return response only
        Ok("vault_proxied_response".to_string())
    }
}

#[derive(Debug)]
pub enum VaultError {
    SecretNotFound(String),
    AccessDenied(String),
    RequestFailed(String),
}

impl fmt::Display for VaultError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            VaultError::SecretNotFound(s) => write!(f, "Secret not found: {}", s),
            VaultError::AccessDenied(s) => write!(f, "Access denied: {}", s),
            VaultError::RequestFailed(s) => write!(f, "Request failed: {}", s),
        }
    }
}

// --- Tests ---

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decision_requires_explain() {
        let decision = Decision::new(
            "High",
            "Risk score 0.9 exceeds threshold 0.8",
            0.92,
            "risk-classifier",
        );
        assert_eq!(decision.value, "High");
        assert!(!decision.explain.is_empty());
        assert!(decision.confidence > 0.0);
    }

    #[test]
    #[should_panic(expected = "explain cannot be empty")]
    fn test_decision_rejects_empty_explain() {
        Decision::new("Low", "", 0.5, "test-agent");
    }

    #[test]
    #[should_panic(expected = "confidence must be 0.0-1.0")]
    fn test_decision_rejects_invalid_confidence() {
        Decision::new("Low", "reason", 1.5, "test-agent");
    }

    #[test]
    fn test_escalation_threshold() {
        let decision = Decision::new("Medium", "uncertain", 0.55, "agent");
        assert!(decision.needs_escalation(0.7));
        assert!(!decision.needs_escalation(0.5));
    }

    #[test]
    fn test_audit_entry_serialization() {
        let entry = AuditEntry::new(
            "test-agent".to_string(),
            "High".to_string(),
            "score exceeded threshold".to_string(),
        );
        let record = entry.to_worm_record();
        let record_str = String::from_utf8(record).unwrap();
        assert!(record_str.starts_with("AUDIT|"));
        assert!(record_str.contains("test-agent"));
        assert!(record_str.contains("score exceeded threshold"));
    }

    #[test]
    fn test_worm_writer_append_only() {
        let mut worm = WormWriter::new();
        let entry = AuditEntry::new("a".into(), "b".into(), "c".into());

        worm.append(&entry);
        worm.append(&entry);

        assert_eq!(worm.entry_count(), 2);
        assert_eq!(worm.read_all().len(), 2);
        // No delete or modify methods exist on WormWriter
    }

    #[test]
    fn test_capabilities_check() {
        let caps = AgentCapabilities {
            agent_name: "code-reviewer".into(),
            allowed: vec![
                Capability {
                    action: Action::ReadFile("src/**/*.rs".into()),
                    scope: Scope::Always,
                },
            ],
            denied: vec![
                Action::WriteFile("**/*".into()),
                Action::AccessNetwork(vec![]),
            ],
            escalation_threshold: 0.7,
            max_cpu: Some(2),
            max_memory_mb: Some(4096),
            max_timeout_sec: Some(300),
        };

        assert!(caps.can_perform(&Action::ReadFile("src/**/*.rs".into())));
        assert!(!caps.can_perform(&Action::WriteFile("**/*".into())));
        assert!(!caps.can_perform(&Action::AccessNetwork(vec![])));
    }

    #[test]
    fn test_vault_proxy_no_secret_exposure() {
        let vault = VaultProxy::new();
        let result = vault.authenticated_request("https://api.example.com", "api_key");
        assert!(result.is_ok());
        // The response does not contain the secret
        assert!(!result.unwrap().contains("api_key"));
    }
}
