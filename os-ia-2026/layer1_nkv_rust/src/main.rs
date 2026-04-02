use std::collections::HashSet;

#[derive(Debug, Clone)]
struct NkvAgent {
    name: String,
    capabilities: HashSet<String>,
}

impl NkvAgent {
    fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            capabilities: HashSet::new(),
        }
    }

    fn add_capability(&mut self, cap: &str) {
        self.capabilities.insert(cap.to_string());
    }

    fn has_capability(&self, cap: &str) -> bool {
        self.capabilities.contains(cap)
    }
}

fn worm_log(message: &str) {
    // In a real implementation, this would write to a WORM partition
    println!("[WORM LOG] {}", message);
}

// LSM hook: every AI agent capability check
fn nkv_check_capability(agent: &NkvAgent, cap: &str) -> Result<(), &'static str> {
    if !agent.has_capability(cap) {
        worm_log(&format!("DENIED: agent={} cap={}", agent.name, cap));
        return Err("EACCES");
    }

    worm_log(&format!("GRANTED: agent={} cap={}", agent.name, cap));
    Ok(())
}

fn main() {
    println!("NKV Kernel (Nano Kernel Verified) Simulator Initialized");

    let mut code_reviewer = NkvAgent::new("code-reviewer");
    code_reviewer.add_capability("read_files");
    code_reviewer.add_capability("suggest_changes");

    let mut deployer = NkvAgent::new("deployer");
    deployer.add_capability("read_files");
    deployer.add_capability("execute_deploy_staging");

    // Simulate capability checks
    match nkv_check_capability(&code_reviewer, "read_files") {
        Ok(_) => println!("Success: Code reviewer read files."),
        Err(e) => println!("Error: {}", e),
    }

    match nkv_check_capability(&code_reviewer, "execute_deploy_production") {
        Ok(_) => println!("Success: Code reviewer deployed."),
        Err(e) => println!("Error: {}", e),
    }

    match nkv_check_capability(&deployer, "execute_deploy_staging") {
        Ok(_) => println!("Success: Deployer deployed to staging."),
        Err(e) => println!("Error: {}", e),
    }

    match nkv_check_capability(&deployer, "execute_deploy_production") {
        Ok(_) => println!("Success: Deployer deployed to production."),
        Err(e) => println!("Error: {}", e),
    }
}
