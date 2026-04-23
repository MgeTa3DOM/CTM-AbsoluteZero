import { describe, test, expect, beforeEach } from "bun:test";
import { SandboxManager, generateVMConfig, MicroVMConfig } from "./firecracker";

const mockConfig: MicroVMConfig = {
  vmId: "vm-123",
  agentId: "agent-456",
  memMb: 512,
  vcpus: 2,
  timeoutSec: 30,
  rootfsPath: "/path/to/rootfs",
  kernelPath: "/path/to/kernel",
  tapDevice: "tap0",
  wormMount: "/mnt/worm",
  capabilities: ["net", "fs"],
  denied: ["exec"],
};

describe("SandboxManager", () => {
  let manager: SandboxManager;

  beforeEach(() => {
    manager = new SandboxManager();
  });

  test("create() registers a new VM and sets state to running", () => {
    const status = manager.create(mockConfig);
    expect(status.vmId).toBe(mockConfig.vmId);
    expect(status.agentId).toBe(mockConfig.agentId);
    expect(status.state).toBe("running");
    expect(manager.get(mockConfig.vmId)).toBe(status);
  });

  test("get() returns undefined for non-existent VM", () => {
    expect(manager.get("non-existent")).toBeUndefined();
  });

  test("kill() transitions VM to killed state", () => {
    manager.create(mockConfig);
    const success = manager.kill(mockConfig.vmId);
    expect(success).toBe(true);
    const status = manager.get(mockConfig.vmId);
    expect(status?.state).toBe("killed");
    expect(status?.lastThought).toContain("killed");
  });

  test("pause() and resume() state transitions", () => {
    manager.create(mockConfig);

    // Pause
    expect(manager.pause(mockConfig.vmId)).toBe(true);
    expect(manager.get(mockConfig.vmId)?.state).toBe("paused");

    // Resume
    expect(manager.resume(mockConfig.vmId)).toBe(true);
    expect(manager.get(mockConfig.vmId)?.state).toBe("running");
  });

  test("pause() only works on running VMs", () => {
    manager.create(mockConfig);
    manager.kill(mockConfig.vmId);
    expect(manager.pause(mockConfig.vmId)).toBe(false);
  });

  test("resume() only works on paused VMs", () => {
    manager.create(mockConfig);
    expect(manager.resume(mockConfig.vmId)).toBe(false);
  });

  test("updateMetrics() updates VM status", () => {
    manager.create(mockConfig);
    manager.updateMetrics(mockConfig.vmId, { cpuPercent: 50, memUsedMb: 256 });
    const status = manager.get(mockConfig.vmId);
    expect(status?.cpuPercent).toBe(50);
    expect(status?.memUsedMb).toBe(256);
  });

  test("list() returns all VMs", () => {
    manager.create(mockConfig);
    manager.create({ ...mockConfig, vmId: "vm-2" });
    expect(manager.list().length).toBe(2);
  });

  test("stats() returns correct counts", () => {
    manager.create(mockConfig); // running
    manager.create({ ...mockConfig, vmId: "vm-2" }); // running
    manager.pause("vm-2");

    const stats = manager.stats();
    expect(stats["running"]).toBe(1);
    expect(stats["paused"]).toBe(1);
  });
});

interface FirecrackerConfig {
  "boot-source": {
    kernel_image_path: string;
    boot_args: string;
  };
  drives: Array<{
    drive_id: string;
    path_on_host: string;
    is_root_device: boolean;
    is_read_only: boolean;
  }>;
  "machine-config": {
    vcpu_count: number;
    mem_size_mib: number;
  };
  "network-interfaces": Array<{
    iface_id: string;
    guest_mac: string;
    host_dev_name: string;
  }>;
}

describe("generateVMConfig", () => {
  test("produces correct Firecracker JSON structure", () => {
    const config = generateVMConfig(mockConfig) as unknown as FirecrackerConfig;

    expect(config["boot-source"].kernel_image_path).toBe(mockConfig.kernelPath);
    expect(config["boot-source"].boot_args).toContain(`agent_id=${mockConfig.agentId}`);

    expect(config.drives).toHaveLength(2);
    expect(config.drives[0].path_on_host).toBe(mockConfig.rootfsPath);

    expect(config["machine-config"].vcpu_count).toBe(mockConfig.vcpus);
    expect(config["machine-config"].mem_size_mib).toBe(mockConfig.memMb);

    expect(config["network-interfaces"]).toHaveLength(1);
    expect(config["network-interfaces"][0].host_dev_name).toBe(mockConfig.tapDevice);
    expect(config["network-interfaces"][0].guest_mac).toMatch(/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/);
  });
});
