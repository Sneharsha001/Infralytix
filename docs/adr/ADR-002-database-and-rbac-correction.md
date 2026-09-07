# ADR 002: Database and RBAC Correction

## Context
During a documentation and code audit, inconsistencies were discovered between the original Software Requirements Specification (`Infralytix_02_SRS.pdf`) and the actual shipped implementation of the system.

### Database Drift
* **Original SRS Claim:** Section 2.1 ("Product Perspective") and Section 6.6 ("Portability") state that the system uses PostgreSQL for production and SQLite for development.
* **Actual Implementation:** The application backend (`backend/pyproject.toml` dependencies: `aiomysql`, `pymysql`; `backend/app/database/session.py`) exclusively uses MySQL for all environments. There are no PostgreSQL or SQLite drivers present in the codebase.

### RBAC Role Drift
* **Original SRS Claim:** Section 6.2 ("Security") specifies RBAC roles of Owner, Collaborator, and Viewer.
* **Actual Implementation:** The application (`app/models/user.py`, `UserRole` enum) defines three different roles: `USER`, `ADMINISTRATOR`, and `EVALUATOR`.

## Decision
This document exists to formally record a documentation-to-code drift discovered during audit. This discrepancy is recognized as a deliberate design evolution rather than a code defect.

Going forward, the statement of record is updated to reflect the actual implementation:
* **Database:** The mandated relational store for all environments is **MySQL**.
* **RBAC Roles:** The official roles in the system are **USER**, **ADMINISTRATOR**, and **EVALUATOR**.

The original `Infralytix_02_SRS.pdf` is left unedited to serve as a historical record. This ADR explicitly supersedes the SRS PDF on these two specific points (Database selection and RBAC Role definitions).
