# API Response Timeout

## Bug Report
The /api/users endpoint is timing out when returning more than 1000 users.

## Stack
- Backend: Node.js
- Database: PostgreSQL
- Response time: >30s

## Root Cause Analysis
Missing index on user_id column in queries
