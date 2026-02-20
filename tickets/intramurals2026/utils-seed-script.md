# Create Comprehensive Database Seed Script

## Problem

The project needs a complete seed script to populate the database with sample/test data (sports, teams, matches, users) for development and testing. Currently, no seed script exists or it's incomplete.

## Potentially Related Files

- [supabase/config.toml](../app/supabase/config.toml#L54) — Seed configuration (sql_paths references seed.sql)
- [prisma/schema.prisma](../app/prisma/schema.prisma) — Database schema (data model reference)
- [app/package.json](../app/package.json) — Scripts (can add seed command)

## What to Fix

1. Create seed data file(s):
   - `supabase/seed.sql` (for Supabase) or
   - `app/prisma/seed.ts` (for Prisma)
2. Include sample data for:
   - **Venues** (Gymnasium, CASE Room, etc.)
   - **Sports** (Basketball, Volleyball, Badminton, etc. with categories MEN/WOMEN)
   - **Teams** (colleges/departments CCS, CCJE, etc.)
   - **Matches** (sample matches with scores and status)
   - **Users/Profiles** (admin and moderator accounts)
3. Add seed command to package.json
4. Document seed instructions in README

## Acceptance Criteria

- Seed script populates all core tables
- Can run `npm run seed` (or supabase seed) from app directory
- Database contains realistic test data after seeding
- Includes at least:
  - 5 venues
  - 10+ sports with MEN/WOMEN categories
  - 10+ teams
  - 20+ sample matches
  - 2 admin/test users
- Script is idempotent (safe to run multiple times)
- All foreign key constraints are satisfied
