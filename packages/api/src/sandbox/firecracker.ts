/**
 * Firecracker Sandbox — Agent isolation layer.
 *
 * Each AI agent runs in its own Firecracker microVM:
 * - 5ms boot time
 * - Memory-limited (cgroup-style, but at VM level)
 * - Network-isolated (tap device per agent)
 * - Filesystem: read-only rootfs + WORM-mounted audit partition
 *
 * This module generates Firecracker configs and manages VM lifecycle.
 * Actual Firecracker binary required at runtime (/usr/bin/firecracker).
 */

export interface MicroVMConfig {
  vmId: string;
  agentId: string;
  /** Memory in MB */
  memMb: number;
  /** vCPUs */
  vcpus: number;
  /** Max execution time in seconds (Fibonacci-bounded) */
  timeoutSec: number;
  /** Read-only root filesystem image */
  rootfsPath: string;
  /** Kernel image */
  kernelPath: string;
  /** Network: tap device name */
  tapDevice: string;
  /** WORM audit mount point */
  wormMount: string;
  /** Capabilities (from Clarity AgentCaps) */
  capabilities: string[];
  /** Denied actions */
  denied: string[];
}

export interface VMStatus {
  vmId: string;
  agentId: string;
  state: "creating" | "running" | "paused" | "stopped" | "killed";
  uptimeMs: number;
  memUsedMb: number;
  cpuPercent: number;
  wormEntries: number;
  lastThought: string;
}

/**
 * Generate Firecracker JSON config for a microVM.
 */
export function generateVMConfig(config: MicroVMConfig): object {
  return {
    "boot-source": {
      kernel_image_path: config.kernelPath,
      boot_args: [
        "console=ttyS0",
        "reboot=k",
        "panic=1",
        "pci=off",
        `agent_id=${config.agentId}`,
        `timeout=${config.timeoutSec}`,
        `caps=${config.capabilities.join(",")}`,
        `denied=${config.denied.join(",")}`,
      ].join(" "),
    },
    "drives": [
      {
        drive_id: "rootfs",
        path_on_host: config.rootfsPath,
        is_root_device: true,
        is_read_only: true,  // Read-only: agent cannot modify its own code
      },
      {
        drive_id: "worm",
        path_on_host: config.wormMount,
        is_root_device: false,
        is_read_only: false,  // Append-only enforced by WORM fs driver
      },
    ],
    "machine-config": {
      vcpu_count: config.vcpus,
      mem_size_mib: config.memMb,
    },
    "network-interfaces": [
      {
        iface_id: "eth0",
        guest_mac: generateMAC(config.vmId),
        host_dev_name: config.tapDevice,
      },
    ],
  };
}

/**
 * Generate a deterministic MAC address from VM ID.
 */
function generateMAC(vmId: string): string {
  let hash = 0;
  for (let i = 0; i < vmId.length; i++) {
    hash = ((hash << 5) - hash + vmId.charCodeAt(i)) | 0;
  }
  const bytes = [
    0x02,  // Locally administered
    (hash >> 0) & 0xff,
    (hash >> 8) & 0xff,
    (hash >> 16) & 0xff,
    (hash >> 24) & 0xff,
    (hash >> 4) & 0xff,
  ];
  return bytes.map(b => b.toString(16).padStart(2, "0")).join(":");
}

/**
 * Sandbox manager — tracks all running microVMs.
 */
export class SandboxManager {
  private vms: Map<string, VMStatus> = new Map();

  /** Register a new VM */
  create(config: MicroVMConfig): VMStatus {
    const status: VMStatus = {
      vmId: config.vmId,
      agentId: config.agentId,
      state: "creating",
      uptimeMs: 0,
      memUsedMb: 0,
      cpuPercent: 0,
      wormEntries: 0,
      lastThought: "booting",
    };
    this.vms.set(config.vmId, status);

    // Simulate boot (in production: spawn firecracker process)
    status.state = "running";
    return status;
  }

  /** Get status of a VM */
  get(vmId: string): VMStatus | undefined {
    return this.vms.get(vmId);
  }

  /** Kill a VM (Fibonacci timeout exceeded) */
  kill(vmId: string): boolean {
    const vm = this.vms.get(vmId);
    if (!vm) return false;
    vm.state = "killed";
    vm.lastThought = "killed: timeout exceeded";
    return true;
  }

  /** Pause a VM (human-in-the-loop escalation) */
  pause(vmId: string): boolean {
    const vm = this.vms.get(vmId);
    if (!vm || vm.state !== "running") return false;
    vm.state = "paused";
    vm.lastThought = "paused: awaiting human approval";
    return true;
  }

  /** Resume a paused VM */
  resume(vmId: string): boolean {
    const vm = this.vms.get(vmId);
    if (!vm || vm.state !== "paused") return false;
    vm.state = "running";
    vm.lastThought = "resumed by human";
    return true;
  }

  /** Update VM metrics (called periodically) */
  updateMetrics(vmId: string, metrics: Partial<VMStatus>) {
    const vm = this.vms.get(vmId);
    if (!vm) return;
    Object.assign(vm, metrics);
  }

  /** List all VMs */
  list(): VMStatus[] {
    return [...this.vms.values()];
  }

  /** Count by state */
  stats(): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const vm of this.vms.values()) {
      counts[vm.state] = (counts[vm.state] || 0) + 1;
    }
    return counts;
  }
}
