## Description
<!-- Briefly describe what this PR changes, adds, or fixes -->

## Type of Change
- [ ]  Bug fix (non-breaking change which fixes an issue)
- [ ]  New feature (non-breaking change which adds functionality)
- [ ]  Performance improvement
- [ ]  Documentation update
- [ ]  Security / Safety fix

## Safety Checklist
- [ ] **No permanent email deletion**: Confirmed only `INBOX` label stripping / archiving is performed.
- [ ] **Protected items safe**: Starred, 2FA, OTPs, receipts, and priority messages are untouched.
- [ ] **Unit tests added or updated**: All tests pass via `pytest`.
- [ ] **No committed secrets**: No `.env`, API keys, or OAuth credentials are included in this PR.
