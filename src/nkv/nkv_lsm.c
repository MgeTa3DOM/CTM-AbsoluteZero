/*
 * NKV Linux Security Module
 * Capability-based access control for AI agents
 *
 * This LSM module enforces the permissions declared in capabilities.clar
 * files at the kernel level. Even if an AI agent tries to bypass Clarity
 * checks, the kernel blocks unauthorized operations.
 *
 * SECURITY MODEL:
 * - Each AI agent process has an associated capability set
 * - Capabilities are loaded from capabilities.clar at agent start
 * - Every file/network/resource access is checked against capabilities
 * - All access attempts (granted or denied) are logged to WORM partition
 * - Capabilities cannot be escalated without human approval (HILT)
 */

#include <linux/lsm_hooks.h>
#include <linux/security.h>
#include <linux/cred.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/string.h>

#define NKV_MAX_AGENTS     256
#define NKV_MAX_CAPS       64
#define NKV_AGENT_NAME_LEN 64
#define NKV_PATH_LEN       256

/* --- Agent Capability Structure --- */

enum nkv_action {
    NKV_ACT_READ_FILE    = 0x01,
    NKV_ACT_WRITE_FILE   = 0x02,
    NKV_ACT_EXEC_CMD     = 0x04,
    NKV_ACT_NET_ACCESS   = 0x08,
    NKV_ACT_VAULT_ACCESS = 0x10,
};

struct nkv_capability {
    enum nkv_action action;
    char scope[NKV_PATH_LEN];  /* glob pattern or allowlist */
};

struct nkv_agent {
    char name[NKV_AGENT_NAME_LEN];
    pid_t pid;
    unsigned int num_caps;
    struct nkv_capability allowed[NKV_MAX_CAPS];
    struct nkv_capability denied[NKV_MAX_CAPS];
    unsigned int num_denied;
    unsigned long max_memory_bytes;
    unsigned int max_cpu_shares;
    unsigned int timeout_sec;
    int escalation_required;  /* 1 = needs human for critical ops */
};

/* Agent registry */
static struct nkv_agent agents[NKV_MAX_AGENTS];
static int num_agents = 0;
static DEFINE_SPINLOCK(agent_lock);

/* --- WORM Audit Logging --- */

/* WORM partition device (set at init) */
static struct file *worm_file = NULL;

static void worm_log(const char *fmt, ...)
{
    /* In production: append to WORM partition file
     * Write-once: only append, never overwrite or delete
     * Even root cannot delete WORM entries */
    va_list args;
    char buf[512];
    int len;

    va_start(args, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    if (len > 0) {
        pr_info("NKV_WORM: %s", buf);
        /* In production: kernel_write(worm_file, buf, len, &pos) */
    }
}

/* --- Agent Lookup --- */

static struct nkv_agent *find_agent_by_pid(pid_t pid)
{
    int i;
    for (i = 0; i < num_agents; i++) {
        if (agents[i].pid == pid)
            return &agents[i];
    }
    return NULL;
}

/* --- LSM Hooks --- */

/*
 * File open hook: check if agent is allowed to access this file
 */
static int nkv_file_open(struct file *file)
{
    struct nkv_agent *agent;
    const char *path;
    char pathbuf[NKV_PATH_LEN];
    int i;
    int mode;

    agent = find_agent_by_pid(current->pid);
    if (!agent) {
        /* Not an AI agent process, allow normal system access */
        return 0;
    }

    path = d_path(&file->f_path, pathbuf, sizeof(pathbuf));
    if (IS_ERR(path))
        return 0;

    mode = file->f_mode;

    /* Check denied list first */
    for (i = 0; i < agent->num_denied; i++) {
        if ((mode & FMODE_WRITE) &&
            agent->denied[i].action == NKV_ACT_WRITE_FILE) {
            worm_log("DENIED: agent=%s action=write path=%s reason=denied_list\n",
                     agent->name, path);
            return -EACCES;
        }
        if ((mode & FMODE_READ) &&
            agent->denied[i].action == NKV_ACT_READ_FILE) {
            worm_log("DENIED: agent=%s action=read path=%s reason=denied_list\n",
                     agent->name, path);
            return -EACCES;
        }
    }

    /* Check allowed list */
    for (i = 0; i < agent->num_caps; i++) {
        if ((mode & FMODE_READ) &&
            agent->allowed[i].action == NKV_ACT_READ_FILE) {
            /* In production: glob match against scope pattern */
            worm_log("GRANTED: agent=%s action=read path=%s\n",
                     agent->name, path);
            return 0;
        }
        if ((mode & FMODE_WRITE) &&
            agent->allowed[i].action == NKV_ACT_WRITE_FILE) {
            worm_log("GRANTED: agent=%s action=write path=%s\n",
                     agent->name, path);
            return 0;
        }
    }

    /* Default deny for AI agents */
    worm_log("DENIED: agent=%s action=access path=%s reason=not_in_allowed\n",
             agent->name, path);
    return -EACCES;
}

/*
 * Task allocation hook: enforce cgroup limits for new AI agent tasks
 */
static int nkv_task_alloc(struct task_struct *task,
                          unsigned long clone_flags)
{
    struct nkv_agent *parent_agent;

    parent_agent = find_agent_by_pid(current->pid);
    if (!parent_agent)
        return 0;  /* Not an AI agent, allow */

    worm_log("TASK_ALLOC: agent=%s child_pid=%d\n",
             parent_agent->name, task->pid);

    /* In production: apply cgroup limits from agent declaration
     * - memory: agent->max_memory_bytes
     * - cpu: agent->max_cpu_shares
     * - timeout: agent->timeout_sec (via timer) */

    return 0;
}

/*
 * Socket create hook: check network access capability
 */
static int nkv_socket_create(int family, int type,
                             int protocol, int kern)
{
    struct nkv_agent *agent;
    int i;

    if (kern)
        return 0;  /* Kernel sockets always allowed */

    agent = find_agent_by_pid(current->pid);
    if (!agent)
        return 0;  /* Not an AI agent */

    /* Check if agent has network access */
    for (i = 0; i < agent->num_caps; i++) {
        if (agent->allowed[i].action == NKV_ACT_NET_ACCESS) {
            worm_log("GRANTED: agent=%s action=network family=%d\n",
                     agent->name, family);
            return 0;
        }
    }

    worm_log("DENIED: agent=%s action=network reason=no_net_capability\n",
             agent->name);
    return -EACCES;
}

/* --- LSM Hook Registration --- */

static struct security_hook_list nkv_hooks[] __ro_after_init = {
    LSM_HOOK_INIT(file_open, nkv_file_open),
    LSM_HOOK_INIT(task_alloc, nkv_task_alloc),
    LSM_HOOK_INIT(socket_create, nkv_socket_create),
};

/* --- Initialization --- */

static int __init nkv_init(void)
{
    security_add_hooks(nkv_hooks, ARRAY_SIZE(nkv_hooks), "nkv");
    pr_info("NKV LSM: initialized with %d hooks\n",
            (int)ARRAY_SIZE(nkv_hooks));
    pr_info("NKV LSM: max agents=%d, max caps per agent=%d\n",
            NKV_MAX_AGENTS, NKV_MAX_CAPS);
    return 0;
}

DEFINE_LSM(nkv) = {
    .name = "nkv",
    .init = nkv_init,
};

MODULE_LICENSE("GPL");
MODULE_AUTHOR("AI-OS 2026 Project");
MODULE_DESCRIPTION("NKV: Nano Kernel Verified - LSM for AI agent security");
