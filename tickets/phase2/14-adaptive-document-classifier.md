# Adaptive Document Classifier and Persona Prompt Router

**[PRIORITY]**

## Problem
Different document domains require radically different audit approaches: legal contracts require strict liability analysis, SOPs require step-by-step role execution, and financial audits require numerical precision. Using a generic system prompt fails to adapt to domain expectations. In addition, returning a hardcoded 75% confidence when zero domain keywords match misleads users on classification certainty.

## Potentially Related Files
- `app/classifier.py` - zero-cost keyword density analyzer and persona definitions
- `app/main.py` - classification integration in document upload workflow
- `tests/test_classifier.py` - domain classification accuracy tests

## What to Fix
1. Define 5 domain profiles: `LEGAL_CONTRACT`, `SOP_PROCEDURAL`, `FINANCIAL_AUDIT`, `ACADEMIC_POLICY`, and `TECHNICAL_MANUAL`.
2. Implement fast keyword-density scoring on the first 1-2 pages of the document during upload.
3. Assign a specialized system prompt addon corresponding to the detected document persona.
4. Calculate true classification confidence based on matching keyword density; return `0.0%` confidence and default to `GENERAL_SPECIFICATION` when zero keywords match.
5. Expose detected domain and persona in document metadata for frontend badges and tailored analysis.

## Acceptance Criteria
- Documents are classified in under 2 milliseconds without LLM API calls.
- Legal contracts activate Legal & Compliance Auditor persona; SOPs activate Operational Compliance Auditor.
- Unrecognized documents with 0 keyword matches return 0.0% confidence without hardcoded guesses.
- Unit tests pass for all 5 document categories and zero-match fallback.
