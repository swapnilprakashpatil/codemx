# Conflict Resolution Strategies

## Overview

The pipeline generates **mapping conflicts** when:
- Source codes referenced in mapping files don't exist in the loaded code sets
- Target codes referenced in mapping files don't exist in the loaded code sets

With ~93K conflicts (primarily SNOMED→ICD-10), manual resolution is impractical. This system provides **automated resolution strategies** to handle conflicts programmatically.

## Conflict Types

Based on current stats:

| Mapping Type | Conflicts | Reason |
|--------------|-----------|--------|
| SNOMED → ICD-10 | 93,228 | `target_not_found` - ICD-10 codes missing |
| ICD-10 → HCC | 160 | `source_not_found` - ICD-10 codes missing |

## Resolution Strategies

### 1. Invalid Code Ignorer

**What it does:**
- Automatically marks conflicts as "ignored" when codes are clearly invalid
- Detects placeholder patterns (XXXXX, 00000, N/A, TBD, etc.)
- Identifies codes with invalid characters

**Use case:** Clean up junk data that should never have been in mapping files

**Example:**
```python
from pipeline.conflict_resolvers import InvalidCodeIgnorer, get_session

session = get_session()
resolver = InvalidCodeIgnorer(session)

# Process conflicts
for conflict in conflicts:
    if resolver.resolve(conflict):
        print(f"Ignored: {conflict.target_code} (invalid format)")
```

### 2. ICD-10 Fuzzy Matcher

**What it does:**
- Finds close matches for missing ICD-10 codes using string similarity
- Handles format variations (with/without decimals: E11.9 ↔ E119)
- Uses configurable similarity threshold (default: 0.85)

**Use case:** Resolve conflicts when mapping file uses slightly different ICD-10 code formats

**Example:**
```python
from pipeline.conflict_resolvers import ICD10FuzzyMatcher, get_session

session = get_session()
# Threshold: 0.85 = 85% similar strings
resolver = ICD10FuzzyMatcher(session, similarity_threshold=0.85)

# E11.XX might match E11.9 if similarity > 0.85
```

**How fuzzy matching works:**

1. **Format normalization**: Tries code variants (with/without decimals)
2. **String similarity**: Compares codes using SequenceMatcher
3. **Auto-mapping**: Creates mapping with matched code if similarity ≥ threshold

**Threshold guidance:**
- 0.95+ = Very strict, only almost-exact matches
- 0.85-0.90 = Recommended, catches format variations
- 0.70-0.80 = Loose, may produce false matches
- <0.70 = Too loose, not recommended

### 3. Missing ICD-10 Creator (Optional)

**What it does:**
- Creates **placeholder ICD-10 codes** for missing targets
- Marks placeholders as `active=False` (inactive)
- Allows mappings to exist with flagged codes

**Use case:** When you need mappings to exist even with questionable codes

**⚠️ Caution:**
- Populates database with codes that don't exist in official CMS data
- Should only be used when you understand the data quality implications
- Disabled by default

## Usage

### Option 1: Standalone Script

Run conflict resolution independently:

```powershell
# Dry run (test without saving)
python -m backend.pipeline.resolve_conflicts --dry-run --limit 100

# Resolve all conflicts
python -m backend.pipeline.resolve_conflicts

# Custom threshold (stricter matching)
python -m backend.pipeline.resolve_conflicts --fuzzy-threshold 0.9

# Limit to first 10,000 conflicts
python -m backend.pipeline.resolve_conflicts --limit 10000

# Enable placeholder creation (use with caution)
python -m backend.pipeline.resolve_conflicts --create-placeholders

# Verbose logging
python -m backend.pipeline.resolve_conflicts --verbose
```

### Option 2: Integrated with Pipeline

Run resolution automatically after pipeline completes:

```powershell
# Full pipeline + auto-resolve
python -m backend.pipeline.process_data --auto-resolve

# Only resolve first 10K conflicts
python -m backend.pipeline.process_data --auto-resolve --resolve-limit 10000

# Stricter fuzzy matching (0.9 threshold)
python -m backend.pipeline.process_data --auto-resolve --fuzzy-threshold 0.9

# Fresh start + auto-resolve
python -m backend.pipeline.process_data --clean --auto-resolve
```

### Option 3: Programmatic API

Use in Python code:

```python
from pipeline.conflict_resolvers import (
    auto_resolve_conflicts,
    BulkConflictResolver,
    InvalidCodeIgnorer,
    ICD10FuzzyMatcher,
)

# Simple auto-resolution
stats = auto_resolve_conflicts(
    limit=None,              # All conflicts
    dry_run=False,           # Save changes
    fuzzy_threshold=0.85,    # 85% similarity
    create_placeholders=False # Don't create placeholders
)

print(f"Resolved: {stats['resolved']}")
print(f"Ignored: {stats['ignored']}")
print(f"Unresolved: {stats['unresolved']}")

# Custom strategy pipeline
from pipeline.models import get_session

session = get_session()
resolver = BulkConflictResolver(session)

# Add strategies in priority order (first match wins)
resolver.add_strategy(InvalidCodeIgnorer(session))
resolver.add_strategy(ICD10FuzzyMatcher(session, similarity_threshold=0.9))

# Run resolution
stats = resolver.resolve_all(limit=5000, commit_interval=1000)
```

## Resolution Priority

Strategies are applied in order. First match wins:

1. **InvalidCodeIgnorer** - Remove junk codes first
2. **ICD10FuzzyMatcher** - Try to match legitimate codes
3. **MissingICD10Creator** - Create placeholders as last resort (if enabled)

## Output

After resolution, conflicts have updated status:

```python
# Was: status="open", resolution=None
# Now: status="resolved", resolution="Fuzzy matched 'E11.XX' to 'E11.9'"

# Or: status="ignored", resolution="Invalid target code format: 'XXXXX'"
```

## Performance Notes

- **Fuzzy matching** loads all ICD-10 codes into memory (~95MB)
- Resolution processes ~500-1000 conflicts/second
- Commits every 1000 conflicts to balance safety and performance
- For 93K conflicts, expect ~2-5 minutes runtime

## Monitoring

Check resolution progress:

```powershell
# Get conflict stats
$stats = Invoke-RestMethod -Uri "http://localhost:5000/api/conflicts/stats"
$stats | ConvertTo-Json

# View resolved conflicts
$conflicts = Invoke-RestMethod -Uri "http://localhost:5000/api/conflicts?status=resolved&limit=100"
$conflicts.items | Format-Table source_code, target_code, resolution
```

## Recommendations

### For Production Use

```powershell
# Conservative: strict matching, no placeholders
python -m backend.pipeline.process_data --auto-resolve --fuzzy-threshold 0.9

# Generate report of what would be resolved
python -m backend.pipeline.resolve_conflicts --dry-run
```

### For Development/Testing

```powershell
# Permissive: resolve as much as possible
python -m backend.pipeline.process_data --auto-resolve --fuzzy-threshold 0.85

# Test on small batch first
python -m backend.pipeline.resolve_conflicts --dry-run --limit 1000
```

## Best Practices

1. **Always dry-run first** to see what would be resolved
2. **Start with high threshold** (0.9+) and lower if needed
3. **Review resolved conflicts** before deploying to production
4. **Don't use placeholders** unless you have a specific reason
5. **Monitor unresolved count** - high numbers may indicate data quality issues

## Extending the System

Add custom resolution strategies:

```python
from pipeline.conflict_resolvers import ConflictResolver

class CustomResolver(ConflictResolver):
    """Your custom resolution logic."""
    
    def resolve(self, conflict: MappingConflict) -> bool:
        """Return True if resolved, False otherwise."""
        
        # Your logic here
        if some_condition:
            conflict.status = "resolved"
            conflict.resolution = "Your explanation"
            self.stats["resolved"] += 1
            return True
        
        return False

# Use it
resolver = BulkConflictResolver(session)
resolver.add_strategy(CustomResolver(session))
resolver.resolve_all()
```

## Troubleshooting

### "No matches found"
- Try lowering fuzzy threshold (0.85 → 0.80)
- Check if ICD-10 data loaded correctly
- Verify code format patterns in your data

### "Too many false matches"
- Raise fuzzy threshold (0.85 → 0.90)
- Add custom validation logic
- Review match quality in resolved conflicts

### "Resolution is slow"
- Fuzzy matching is CPU-intensive
- Consider processing in batches (`--limit`)
- Run during off-hours for large datasets

## Files

| File | Purpose |
|------|---------|
| `conflict_resolvers.py` | Core resolution strategies |
| `resolve_conflicts.py` | CLI tool for standalone resolution |
| `pipeline.py` | Integrated `--auto-resolve` option |
| `models.py` | MappingConflict model definition |
| `conflict_service.py` | API endpoints for conflict management |

## Examples

See resolved conflicts:

```sql
SELECT 
    source_code,
    target_code,
    resolved_code,
    resolution,
    status
FROM mapping_conflicts
WHERE status = 'resolved'
LIMIT 10;
```

Get resolution summary:

```python
from pipeline.models import get_session, MappingConflict
from sqlalchemy import func

session = get_session()

stats = session.query(
    MappingConflict.status,
    func.count(MappingConflict.id)
).group_by(MappingConflict.status).all()

for status, count in stats:
    print(f"{status}: {count}")
```
