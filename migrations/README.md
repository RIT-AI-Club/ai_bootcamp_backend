# Database Migrations

This directory contains SQL migration scripts for the AI Bootcamp database schema.

## Migration Files

| Migration | Description | Date |
|-----------|-------------|------|
| `001_add_oauth_support.sql` | Add Google OAuth authentication support | 2025-10-16 |

---

## How to Run Migrations

### Method 1: Direct psql (Recommended for Development)

```bash
# From the project root
psql postgresql://aibc_admin:AIbc2024SecurePass@localhost:5432/aibc_db -f migrations/001_add_oauth_support.sql
```

### Method 2: Docker exec

```bash
# Copy migration to container
docker cp migrations/001_add_oauth_support.sql aibc_postgres:/tmp/

# Execute migration
docker exec -i aibc_postgres psql -U aibc_admin -d aibc_db -f /tmp/001_add_oauth_support.sql
```

### Method 3: Via Docker Compose

```bash
# Connect to database
docker-compose exec postgres psql -U aibc_admin -d aibc_db

# Then paste the migration SQL
\i /path/to/migrations/001_add_oauth_support.sql
```

---

## Migration 001: OAuth Support

### What It Does

1. **Makes `password_hash` nullable** in `users` table
   - Allows OAuth users without passwords
   - Existing password users unaffected

2. **Creates `oauth_accounts` table**
   - Links users to OAuth providers (Google, etc.)
   - Stores provider tokens and metadata

3. **Adds indexes** for performance
   - `idx_oauth_accounts_user_id`
   - `idx_oauth_accounts_provider`
   - `idx_oauth_accounts_provider_account`

4. **Sets up triggers**
   - Auto-updates `updated_at` timestamp

### Safety Features

- ✅ **Idempotent:** Safe to run multiple times
- ✅ **Non-destructive:** Doesn't delete or modify existing data
- ✅ **Backward compatible:** Existing authentication still works
- ✅ **Verification checks:** Confirms changes applied correctly

### Verification

After running the migration, check the output for:

```
✓ password_hash column is nullable
✓ oauth_accounts table exists
✓ oauth_accounts table has 0 records
Migration 001_add_oauth_support.sql completed successfully
```

---

## Rolling Back

If you need to revert the OAuth changes:

```bash
psql postgresql://aibc_admin:AIbc2024SecurePass@localhost:5432/aibc_db -f migrations/001_add_oauth_support_rollback.sql
```

**⚠️ WARNING:** Rollback will fail if OAuth-only users exist (users with `password_hash = NULL`). You must either:
- Assign passwords to OAuth users first, OR
- Delete OAuth-only users

---

## Migration Checklist

Before running a migration:

- [ ] **Backup database** (production only)
  ```bash
  pg_dump -U aibc_admin -d aibc_db > backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Review migration SQL** - Read through the migration file

- [ ] **Test in development first** - Never run untested migrations in production

- [ ] **Check application compatibility** - Ensure code supports schema changes

After running a migration:

- [ ] **Verify success** - Check migration output for success messages

- [ ] **Test application** - Ensure all features still work

- [ ] **Check logs** - Look for any database errors

- [ ] **Document** - Update this README if needed

---

## Creating New Migrations

When creating a new migration:

1. **Use sequential numbering:** `002_description.sql`, `003_description.sql`, etc.

2. **Include header comments:**
   ```sql
   -- Migration: Description
   -- Date: YYYY-MM-DD
   -- Description: What this migration does
   ```

3. **Make it idempotent:** Use `IF NOT EXISTS`, `IF EXISTS`, etc.

4. **Add verification:** Include checks to confirm changes

5. **Create rollback:** Always include a `_rollback.sql` file

6. **Test thoroughly:** Test both migration and rollback

7. **Document:** Update this README with migration details

---

## Best Practices

### DO ✅

- Always backup production databases before migrations
- Test migrations in development environment first
- Make migrations idempotent (safe to run multiple times)
- Include verification queries in migrations
- Create rollback scripts for each migration
- Use transactions when appropriate
- Document breaking changes clearly

### DON'T ❌

- Don't modify existing migration files after they've been run
- Don't run migrations directly in production without testing
- Don't skip migrations (run them in order)
- Don't delete data without explicit backups
- Don't ignore migration errors
- Don't mix schema and data migrations

---

## Troubleshooting

### Migration fails with "relation already exists"

This is normal if the migration has been run before. The migration is idempotent and will skip already-existing objects.

### Migration fails with "cannot alter type of column"

You may have data that conflicts with the schema change. Review the error and adjust the migration or data accordingly.

### Rollback fails with "OAuth-only users exist"

You have users who signed up via OAuth and don't have passwords. Either:
1. Keep the OAuth implementation, or
2. Manually assign passwords to these users before rolling back

### Can't connect to database

Check that:
- Docker containers are running: `docker-compose ps`
- Database credentials match `.env` file
- Port 5432 is not blocked

---

## Production Migration Workflow

For production deployments:

```bash
# 1. Create backup
pg_dump -U aibc_admin -d aibc_db -h your-db-host > backup_pre_migration.sql

# 2. Test migration in staging
psql -U aibc_admin -d aibc_db_staging -h staging-host -f migrations/001_add_oauth_support.sql

# 3. Verify staging works
# ... run application tests ...

# 4. Schedule maintenance window
# ... coordinate with team ...

# 5. Run migration in production
psql -U aibc_admin -d aibc_db -h prod-host -f migrations/001_add_oauth_support.sql

# 6. Verify production
# ... check application health ...

# 7. If issues arise, rollback
psql -U aibc_admin -d aibc_db -h prod-host -f migrations/001_add_oauth_support_rollback.sql
```

---

## Support

If you encounter issues with migrations:

1. Check the migration output for error messages
2. Review database logs: `docker logs aibc_postgres`
3. Verify database connection: `docker-compose exec postgres psql -U aibc_admin -d aibc_db -c '\dt'`
4. Consult the troubleshooting section above
5. Create a database backup before attempting fixes

---

## Migration History

| Version | Date | Description | Status |
|---------|------|-------------|--------|
| 001 | 2025-10-16 | Add OAuth support | ✅ Active |

---

**Last Updated:** 2025-10-16
