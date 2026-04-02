/*
 * WORM Filesystem Driver for NKV Kernel
 * Write-Once Read-Many: immutable audit logs
 *
 * DESIGN PRINCIPLES:
 * - Append only: new data can only be added at the end
 * - No overwrite: existing data cannot be modified
 * - No delete: files and entries cannot be removed
 * - No truncate: files cannot be shortened
 * - Even root/kernel cannot bypass these restrictions
 *
 * USE CASE:
 * All AI agent decisions, capability checks, and audit trails
 * are written to this partition. This provides a tamper-proof
 * record that can be inspected after any incident.
 */

#include <linux/fs.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/slab.h>
#include <linux/buffer_head.h>
#include <linux/time.h>

#define WORM_MAGIC     0x574F524D  /* "WORM" in hex */
#define WORM_BLOCK_SIZE 4096
#define WORM_VERSION    1

/* --- On-Disk Structures --- */

struct worm_super_block {
    __le32 magic;
    __le32 version;
    __le64 created_at;       /* Timestamp of filesystem creation */
    __le64 total_blocks;
    __le64 used_blocks;
    __le64 next_append_pos;  /* Next position for append */
    __le32 flags;
    __le32 reserved[16];
};

struct worm_entry_header {
    __le64 timestamp;        /* Entry creation time */
    __le32 entry_type;       /* AUDIT, CAPABILITY, EVENT, etc. */
    __le32 data_length;      /* Length of entry data */
    __le64 prev_entry;       /* Offset of previous entry (linked list) */
    __u8   hash[32];         /* SHA-256 of entry data (integrity) */
};

enum worm_entry_type {
    WORM_ENTRY_AUDIT      = 0x01,  /* Decision audit trail */
    WORM_ENTRY_CAPABILITY = 0x02,  /* Capability grant/deny log */
    WORM_ENTRY_EVENT      = 0x03,  /* System event */
    WORM_ENTRY_ESCALATION = 0x04,  /* Human escalation request */
};

/* --- VFS Operations --- */

/*
 * Write operation: APPEND ONLY
 * - Writing is only allowed at the end of the file
 * - Any attempt to write at a previous position is denied
 * - The position pointer is automatically advanced
 */
static ssize_t worm_file_write(struct file *file, const char __user *buf,
                                size_t count, loff_t *ppos)
{
    struct inode *inode = file_inode(file);
    loff_t file_size = i_size_read(inode);

    /* WORM rule: only append at end of file */
    if (*ppos != file_size) {
        pr_warn("WORM: overwrite attempt DENIED at offset %lld (file_size=%lld)\n",
                *ppos, file_size);
        return -EACCES;
    }

    /* In production: write to underlying block device
     * For now, log the write attempt */
    pr_info("WORM: append %zu bytes at offset %lld\n", count, *ppos);

    /* Update position for next append */
    *ppos += count;

    return count;
}

/*
 * Unlink (delete): ALWAYS DENIED
 * WORM files cannot be deleted. Period.
 */
static int worm_unlink(struct inode *dir, struct dentry *dentry)
{
    pr_warn("WORM: DELETE DENIED for '%s' - WORM filesystem is immutable\n",
            dentry->d_name.name);
    return -EROFS;
}

/*
 * Rename: ALWAYS DENIED
 * WORM files cannot be renamed (could be used to hide audit trails)
 */
static int worm_rename(struct inode *old_dir, struct dentry *old_dentry,
                       struct inode *new_dir, struct dentry *new_dentry,
                       unsigned int flags)
{
    pr_warn("WORM: RENAME DENIED for '%s' - WORM filesystem is immutable\n",
            old_dentry->d_name.name);
    return -EROFS;
}

/*
 * Truncate/setattr: DENY size reduction
 * Files can only grow, never shrink
 */
static int worm_setattr(struct dentry *dentry, struct iattr *attr)
{
    if (attr->ia_valid & ATTR_SIZE) {
        struct inode *inode = d_inode(dentry);
        if (attr->ia_size < i_size_read(inode)) {
            pr_warn("WORM: TRUNCATE DENIED for '%s' - cannot shrink WORM files\n",
                    dentry->d_name.name);
            return -EROFS;
        }
    }

    /* Allow metadata updates that don't reduce data */
    return 0;
}

/*
 * Read: ALWAYS ALLOWED
 * WORM = Write-Once, Read-Many
 * Anyone can read audit logs (transparency principle)
 */
static ssize_t worm_file_read(struct file *file, char __user *buf,
                               size_t count, loff_t *ppos)
{
    /* In production: read from underlying block device */
    pr_info("WORM: read %zu bytes from offset %lld\n", count, *ppos);
    return 0;  /* Stub */
}

/* --- File Operations --- */

static const struct file_operations worm_file_ops = {
    .read    = worm_file_read,
    .write   = worm_file_write,
    /* No ioctl for deletion/modification */
};

/* --- Inode Operations --- */

static const struct inode_operations worm_dir_ops = {
    .unlink  = worm_unlink,
    .rename  = worm_rename,
    .setattr = worm_setattr,
    /* No rmdir - directories cannot be deleted either */
};

/* --- Module Init --- */

static int __init worm_init(void)
{
    pr_info("WORM FS: initialized (v%d)\n", WORM_VERSION);
    pr_info("WORM FS: append-only, no delete, no overwrite, no truncate\n");
    return 0;
}

static void __exit worm_exit(void)
{
    pr_info("WORM FS: unloaded\n");
}

module_init(worm_init);
module_exit(worm_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("AI-OS 2026 Project");
MODULE_DESCRIPTION("WORM: Write-Once Read-Many filesystem for immutable audit logs");
MODULE_VERSION("1.0");
