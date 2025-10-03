# Backend Scripts

This directory contains utility scripts for database migrations, maintenance, and administrative tasks.

## Available Scripts

### Workflow Migration

#### `migrate_workflows.py`
Migrates existing workflow records from old format to align with the latest data model defined in `shared/models/` and `shared/node_specs/`.

**Quick Start:**
```bash
# Preview migration on 1 workflow
python scripts/migrate_workflows.py --dry-run --limit 1

# Execute migration on all workflows
python scripts/migrate_workflows.py --execute
```

**See Also:** [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for complete documentation

---

## Script Guidelines

### Environment Setup

Before running any script that accesses the database:

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SECRET_KEY="your-service-role-key"
```

### Safety Practices

1. **Always test first**: Use `--dry-run` or test on dev/staging
2. **Backup data**: Create database backups before destructive operations
3. **Review logs**: Check verbose output for errors
4. **Test small batches**: Use `--limit` for gradual rollout
5. **Verify results**: Run verification queries after migration

### Adding New Scripts

When adding new scripts:

1. Place in `apps/backend/scripts/`
2. Add docstring with usage examples
3. Support `--dry-run` for safety
4. Add logging with appropriate levels
5. Handle errors gracefully
6. Document in this README
7. Add to `.gitignore` if generating sensitive output

### Script Template

```python
"""
Script Name

Description of what this script does.

Usage:
    python script_name.py --dry-run
    python script_name.py --execute
"""

import argparse
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    dry_run = not args.execute

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be applied")
    else:
        logger.warning("EXECUTION MODE - Changes will be applied")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Cancelled")
            return

    # Your script logic here


if __name__ == "__main__":
    main()
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`:

```bash
# Make sure you're in the backend directory
cd apps/backend

# Install dependencies
pip install -r requirements.txt
# or
uv sync
```

### Database Connection Issues

If you see connection errors:

1. Verify environment variables are set
2. Check network connectivity to Supabase
3. Verify credentials are correct
4. Check Supabase project status

### Permission Errors

Scripts typically require service role key (not anon key) for administrative operations.

## Common Tasks

### Backup Database

```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
psql $DATABASE_URL < backup_YYYYMMDD.sql
```

### Check Script Syntax

```bash
python -m py_compile scripts/script_name.py
```

### Run with Timeout

```bash
timeout 300 python scripts/script_name.py --execute
```

## Best Practices Summary

- ✅ Use `--dry-run` by default
- ✅ Backup before execution
- ✅ Start with small limits
- ✅ Monitor logs carefully
- ✅ Verify results after completion
- ✅ Document any issues encountered
- ✅ Keep scripts idempotent when possible
- ✅ Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- ✅ Handle keyboard interrupts gracefully
- ✅ Provide clear error messages with solutions

## Support

For questions or issues:

1. Check script docstrings and inline comments
2. Review relevant documentation in `/docs`
3. Check logs with `--verbose` flag
4. Contact the development team

## Future Scripts

Planned utility scripts:

- [ ] Workflow validation script
- [ ] Database health check script
- [ ] Execution cleanup script (remove old executions)
- [ ] Node specification validator
- [ ] Workflow template export/import
- [ ] User data migration
