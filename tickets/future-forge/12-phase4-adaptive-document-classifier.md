# 12-phase4-adaptive-document-classifier.md

**[PRIORITY]**

## Problem
Different document domains require radically different audit approaches: legal contracts require strict liability analysis, SOPs require step-by-step role execution, and financial audits require zero-rounding numerical precision. Using a generic system prompt fails to adapt to domain expectations.

## Potentially Related Files
- `app/classifier.py` - zero-cost keyword density analyzer and persona definitions
- `app/main.py` - classification integration in document upload workflow
- `tests/test_classifier.py` - domain classification accuracy tests

## What to Fix
1. Define 5 domain profiles: `LEGAL_CONTRACT`, `SOP_PROCEDURAL`, `FINANCIAL_AUDIT`, `ACADEMIC_POLICY`, and `TECHNICAL_MANUAL`.
2. Implement fast keyword-density scoring on the first 1-2 pages of the document during upload.
3. Assign a specialized system prompt addon corresponding to the detected document persona.
4. Calculate a classification confidence score (70% - 98%) based on keyword frequency.
5. Provide a fallback to `GENERAL_SPECIFICATION` for unrecognized document formats.

## Acceptance Criteria
- Documents are classified in under 2 milliseconds without LLM API calls.
- Legal contracts automatically activate the Legal & Compliance Auditor persona.
- Technical manuals automatically activate the Senior Systems Architect persona.
- Tests pass for all 5 document categories and the general fallback.
