# 🛡️ SAFETY DOCUMENTATION - READ BEFORE USING!

## ⚠️ CRITICAL: File Deletion Safety

This application handles file deletion with **MULTIPLE LAYERS OF PROTECTION** to prevent accidental data loss.

---

## 🔒 Safety Mechanisms

### 1. **Backend Protections**

#### ✅ Explicit Confirmation Required
- All delete operations require `confirm=true` parameter
- Without it, operations return a **preview only**
- No files are touched without explicit confirmation

#### ✅ Rate Limiting (100 files max per operation)
- Maximum 100 files can be deleted at once
- Forces users to work in smaller, manageable batches
- Prevents accidental mass deletion
- Backend validates and rejects requests over 100 files

#### ✅ Root Folder Protection
- Cannot delete the root folder `/`
- Extra validation prevents any attempts to delete root

#### ✅ Comprehensive Logging
- ALL deletion attempts are logged
- Audit trail includes:
  - Timestamp
  - Number of files
  - File paths
  - Success/failure status
- Logs stored in `backend/logs/` for investigation

#### ✅ Individual Error Handling
- Each file deletion is independent
- If one fails, others continue
- Failed deletions are reported separately
- No "all or nothing" behavior

---

### 2. **Frontend Protections**

#### ✅ Confirmation Modal
- Large, clear warning modal
- Shows exactly how many files will be deleted
- Shows amount of space to be freed
- Prominent red warning: "THIS ACTION CANNOT BE UNDONE!"
- Must click explicit "Yes, Delete X Files" button

#### ✅ Extra Confirmation for Large Deletions
- If deleting > 50 files: Additional browser confirm() dialog
- Requires TWO confirmations for large deletions
- Clear warning about large deletion size

#### ✅ 100 File Safety Limit (Frontend Check)
- Frontend also checks for 100 file limit
- Shows clear error message if limit exceeded
- Instructs user to delete in smaller batches

#### ✅ Recommended Files Are PROTECTED
- Files recommended to keep have checkboxes **disabled**
- Cannot accidentally select them
- Highlighted with green border
- Badge: "Recommended Keep" or "Best Quality"

#### ✅ Pre-Selection Logic
- Only NON-recommended files are pre-selected
- Recommended files are never pre-selected
- User must explicitly choose to delete anything

#### ✅ Clear Status Messages
- Success: "✅ Successfully deleted X files!"
- Failure: Shows counts and details
- Error: "No files were deleted. Please try again."

---

## 🎯 How The Protection Works

### Scenario 1: Deleting Duplicates

1. **Scan finds duplicates**
2. **System recommends which to keep** (best path, best name)
3. **Recommended files are highlighted green**
4. **Recommended files CANNOT be checked** (disabled checkbox)
5. **Only non-recommended files are pre-selected**
6. User clicks "Delete Selected"
7. **Modal pops up with clear warning**
8. User must click "Yes, Delete X Files"
9. **If > 50 files: Extra browser confirmation**
10. **If > 100 files: Rejected with error message**
11. Backend logs the attempt
12. **Backend requires confirm=true** or returns preview
13. Each file deleted individually
14. Success/failure reported
15. Audit trail saved to logs

### Scenario 2: Deleting Similar Images

1. **Scan finds similar images**
2. **System scores quality** (resolution + sharpness + compression + aspect)
3. **Best quality version highlighted**
4. **Best quality CANNOT be checked** (disabled checkbox)
5. **Only lower quality versions pre-selected**
6. Same protection layers as above
7. Best quality image is ALWAYS kept

---

## 📋 Safety Checklist

Before any deletion can occur, ALL of these must be true:

- [ ] User explicitly clicked "Delete Selected" button
- [ ] Confirmation modal was shown
- [ ] User clicked "Yes, Delete X Files" in modal
- [ ] If > 50 files: User confirmed extra dialog
- [ ] < 100 files selected (hard limit)
- [ ] Recommended files are NOT in selection (disabled)
- [ ] Backend received confirm=true parameter
- [ ] Each file path validated
- [ ] No root folder in selection
- [ ] Operation logged to audit trail

**If ANY of these fail: DELETION IS BLOCKED**

---

## 🚫 What CANNOT Happen

❌ **Cannot delete all files at once**
   - 100 file limit per operation

❌ **Cannot delete recommended files**
   - Checkboxes are disabled
   - Cannot be selected

❌ **Cannot delete without confirmation**
   - Modal must be confirmed
   - Large deletions need extra confirmation

❌ **Cannot delete root folder**
   - Backend validation prevents this

❌ **Cannot delete without logging**
   - ALL operations logged with timestamps

❌ **Cannot accidentally click delete**
   - Multiple steps required
   - No single-click deletion

---

## 📊 Deletion Limits

| Limit | Value | Reason |
|-------|-------|--------|
| Max files per operation | 100 | Prevents mass deletion |
| Extra confirmation threshold | 50 | Additional safety for large deletions |
| Recommended file selection | BLOCKED | Protects best files |
| Root folder deletion | BLOCKED | Prevents catastrophic loss |
| Confirmations required (< 50 files) | 1 modal | Standard protection |
| Confirmations required (> 50 files) | 1 modal + 1 browser | Extra protection |

---

## 🔍 Verification Steps

**Before using the application, verify:**

1. ✅ Check recommended files have green borders
2. ✅ Try to click checkbox on recommended file (should be disabled)
3. ✅ Try to delete files (modal should appear)
4. ✅ Check logs exist in `backend/logs/`
5. ✅ Test with 1-2 files first
6. ✅ Review what will be deleted before confirming

---

## 🆘 Emergency: What If Something Goes Wrong?

### If You Accidentally Deleted Files:

1. **Check Dropbox Trash**
   - Files go to Dropbox trash first
   - Can be restored for 30 days (or more with Plus/Pro)
   - Go to: https://www.dropbox.com/deleted_files

2. **Check the Logs**
   - Look in `backend/logs/dropbox_sorter_YYYYMMDD.log`
   - Find exactly what was deleted and when
   - Use for recovery reference

3. **Check Error Messages**
   - Failed deletions are reported
   - Console shows details
   - Some files might have failed and are still there

### Prevention Tips:

1. **Start Small** - Test on a folder with copies first
2. **Review Carefully** - Check what's selected before clicking
3. **Read Warnings** - Modal warnings are there for a reason
4. **Trust Recommendations** - System is conservative about what to keep
5. **Delete in Batches** - Don't rush, do 10-20 files at a time
6. **Check Trash** - Verify deletions went to trash, not permanent

---

## ✅ Best Practices

1. **First Time Users:**
   - Create a test folder with duplicate files
   - Run a scan on that folder only
   - Practice the deletion workflow
   - Verify files in Dropbox trash
   - Then use on real data

2. **Regular Usage:**
   - Always review the recommended files
   - Start with obvious duplicates (screenshots, IMG_xxxx)
   - Delete in small batches (10-20 at a time)
   - Check Dropbox after each batch
   - Keep logs for reference

3. **Large Cleanups:**
   - Scan specific folders, not entire Dropbox
   - Do duplicates first, similar images second
   - Take breaks between batches
   - Keep notes of what you deleted
   - Back up important files first

---

## 🎓 Understanding the Recommendations

### Duplicate Files - System Keeps:
- ✅ Files with better paths (shorter, more organized)
- ✅ Files with descriptive names (vs IMG_1234)
- ✅ More recently modified files
- ❌ Generic screenshot names
- ❌ Files in deep folder structures
- ❌ "Copy of..." files

### Similar Images - System Keeps:
- ✅ Highest resolution
- ✅ Sharpest image (edge detection)
- ✅ Best compression ratio
- ✅ Normal aspect ratio
- ❌ Over-compressed images
- ❌ Lower resolution versions
- ❌ Blurry images

---

## 🔐 Summary

**You are protected by:**
- ✅ 100 file limit per operation
- ✅ Multiple confirmation dialogs
- ✅ Disabled checkboxes on recommended files
- ✅ Comprehensive logging
- ✅ Individual error handling
- ✅ Clear warnings and messages
- ✅ Preview mode option
- ✅ Dropbox trash safety net (30 days)

**The application is designed to be PARANOID about deletions.**

**When in doubt: DON'T DELETE. Review first, delete later.**

---

**Built with safety as the #1 priority! 🛡️**
