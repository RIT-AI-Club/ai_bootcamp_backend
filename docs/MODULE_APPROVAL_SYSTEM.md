# Module Approval System Implementation

**Date:** 2025-10-16
**Status:** ✅ COMPLETE - Ready for Testing

## Overview

Implementing a 2-step validation workflow for module completions:
1. **Student submits all resources** → Module marked as "Pending Review"
2. **Admin/Instructor approves** → Module marked as "Approved" (student can progress)

## Database Changes

###  Migration: `003_add_module_approval_system.sql`

**New columns in `module_completions` table:**
- `approval_status` VARCHAR(50) - Values: `pending`, `approved`, `rejected`
- `reviewed_by` UUID - Admin who reviewed
- `reviewed_at` TIMESTAMP - When reviewed
- `review_comments` TEXT - Feedback from instructor

**New view:** `pending_module_reviews` - Lists all modules waiting for instructor review

## Backend Changes Completed ✅

### 1. Model Updates
- `app/models/progress.py` - Added approval fields to `ModuleCompletion` model
- Constraint: `approval_status IN ('pending', 'approved', 'rejected')`

### 2. Schema Updates
- `app/schemas/progress.py`:
  - `ModuleCompletionResponse` - Now includes approval fields
  - `ModuleWithCompletion` - Added `approval_status` field
  - `ModuleApprovalRequest` - New schema for admin approval requests

### 3. API Updates
- `app/api/v1/progress.py`:
  - Updated `get_pathway_progress()` to include approval status in module list
  - Progress calculation now considers only "approved" modules

## Backend Changes Needed ✅ COMPLETE

### 1. Resource Validation Before Module Completion ✅
The `/modules/complete` endpoint now validates ALL resources are completed.

**Implementation added:**
```python
# In mark_module_complete():
# 1. Get all resources for the module
resources = await resource_crud.get_resources_by_module(db, module_id)

# 2. Get user's resource completions
completions = await resource_crud.get_user_completions_for_module(db, user_id, module_id)

# 3. Check if all resources are complete
if len(completions) < len(resources):
    raise HTTPException(
        status_code=400,
        detail="Cannot complete module: not all resources are finished"
    )

# 4. Check all uploads submitted for required resources
for resource in resources:
    if resource.requires_upload:
        completion = next((c for c in completions if c.resource_id == resource.id), None)
        if not completion or completion.submission_count == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Resource '{resource.title}' requires file submission"
            )
```

### 2. Admin Approval Endpoint ✅
Added endpoint for admins to approve/reject module completions.

**Implemented endpoint:**
```python
@router.post("/modules/{completion_id}/approve")
async def approve_module_completion(
    completion_id: UUID,
    approval: ModuleApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Admin only
):
    # Update approval status
    completion = await ProgressCRUD.update_module_approval(
        db, completion_id, current_user.id, approval
    )
    return completion
```

## Frontend Changes Needed ✅ COMPLETE

### 1. Update ModuleDetailModal
**File:** `components/ModuleDetailModal.tsx`

**Changes:**
```typescript
// Calculate if all resources are completed
const allResourcesComplete = useMemo(() => {
  if (!module.resources) return false;

  const totalResources = module.resources.length;
  const completedCount = Array.from(resourcesProgress.values()).filter(
    (progress) => progress.completion?.status === 'completed' ||
                 progress.completion?.status === 'reviewed'
  ).length;

  // Check uploads for required resources
  const uploadRequiredResources = module.resources.filter(
    (r) => r.type === 'exercise' || r.type === 'project'
  );

  for (const resource of uploadRequiredResources) {
    const resourceId = `${module.id}-r${module.resources.indexOf(resource) + 1}`;
    const progress = resourcesProgress.get(resourceId);
    if (!progress?.submissions || progress.submissions.length === 0) {
      return false; // Missing required upload
    }
  }

  return completedCount === totalResources;
}, [module, resourcesProgress]);

// Update "Mark as Complete" button
<button
  onClick={() => onModuleComplete?.(module.id)}
  disabled={!allResourcesComplete}
  className={`px-6 py-2 rounded-lg font-medium transition-transform ${
    allResourcesComplete
      ? 'bg-green-600 hover:bg-green-700 text-white hover:scale-105'
      : 'bg-gray-600 text-gray-400 cursor-not-allowed'
  }`}
>
  {allResourcesComplete ? 'Submit for Review' : 'Complete All Resources First'}
</button>
```

### 2. Show Approval Status
**In PathwayMap or ModuleCard:**

```typescript
// Show different states
{module.completed && module.approval_status === 'pending' && (
  <div className="flex items-center gap-2 text-yellow-400">
    <ClockIcon className="w-5 h-5" />
    <span>Pending Review</span>
  </div>
)}

{module.completed && module.approval_status === 'approved' && (
  <div className="flex items-center gap-2 text-green-400">
    <CheckCircleIcon className="w-5 h-5" />
    <span>Approved</span>
  </div>
)}

{module.completed && module.approval_status === 'rejected' && (
  <div className="flex items-center gap-2 text-red-400">
    <XCircleIcon className="w-5 h-5" />
    <span>Needs Revision</span>
  </div>
)}
```

### 3. Update Types
**File:** `lib/pathways/types.ts`

```typescript
export interface Module {
  // ... existing fields
  approval_status?: 'pending' | 'approved' | 'rejected';
  review_comments?: string;
}
```

## UX Flow

### Student Experience

1. **Open Module** → See list of resources
2. **Complete Resources** → Mark videos watched, complete exercises, upload projects
3. **All Complete** → "Submit for Review" button becomes enabled
4. **Click Submit** → Module marked as "Pending Review" (yellow badge)
5. **Wait for Instructor** → Cannot progress to next module yet
6. **Approved** → Green badge, can progress to next module
7. **Rejected** → Red badge, see feedback, fix issues and resubmit

### Admin Experience

1. **Dashboard** → See "Pending Module Reviews" count
2. **Review Queue** → List of all pending module completions
3. **Click Module** → See student's resource completions and submissions
4. **Review Work** → Download submissions, check quality
5. **Approve/Reject** → Add comments if rejected
6. **Student Notified** → Status updates on their progress page

## API Endpoints Summary

### Existing
- `POST /api/v1/progress/modules/complete` - Student marks module complete (needs validation update)
- `GET /api/v1/progress/pathways/{slug}` - Get progress with approval status ✅

### New (To Add)
- `POST /api/v1/progress/modules/{id}/approve` - Admin approves module
- `GET /api/v1/progress/modules/pending-reviews` - List pending reviews (admin only)
- `GET /api/v1/progress/modules/{id}/review-details` - Get details for review (admin only)

## Database Queries Needed

### Get Pending Reviews (Admin)
```sql
SELECT * FROM pending_module_reviews
WHERE approval_status = 'pending'
ORDER BY hours_waiting DESC;
```

### Approve Module
```sql
UPDATE module_completions
SET approval_status = 'approved',
    reviewed_by = $1,
    reviewed_at = NOW(),
    review_comments = $2
WHERE id = $3;
```

### Check All Resources Complete
```sql
SELECT
  (SELECT COUNT(*) FROM resources WHERE module_id = $1) as total,
  (SELECT COUNT(*) FROM resource_completions
   WHERE module_id = $1 AND user_id = $2
   AND status IN ('completed', 'submitted', 'reviewed')) as completed;
```

## Migration Steps

1. ✅ Run `003_add_module_approval_system.sql`
2. ✅ Update backend validation in `mark_module_complete()`
3. ✅ Add admin approval endpoint
4. ✅ Update frontend ModuleDetailModal
5. ✅ Update frontend to show approval states
6. ⏳ Test complete workflow (User will test)

## Implementation Complete ✅

All tasks completed:
1. ✅ Added resource validation to module completion endpoint
2. ✅ Created admin approval endpoint
3. ✅ Updated frontend ModuleDetailModal with validation logic
4. ✅ Added approval status badges to UI
5. ⏳ Create admin review dashboard (future enhancement)

See `/MODULE_APPROVAL_IMPLEMENTATION_COMPLETE.md` for full implementation details.

## Notes

- Existing completions will be grandfathered as "approved"
- Students cannot progress until module is approved
- Instructors can add comments when rejecting
- Resubmission is allowed after rejection
