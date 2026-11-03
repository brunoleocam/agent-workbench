---
status: approved
complexity: M
security_risk: HIGH
security_triggers: sql_database, authentication
---
# Spec: desconto por cupom

## Requirements

### REQ-001: Aplicar cupom
WHEN the customer applies a valid coupon THE SYSTEM SHALL reduce the order total by the coupon percentage.

### REQ-002: Rejeitar cupom expirado
IF the coupon is expired THEN THE SYSTEM SHALL keep the total and return the error COUPON_EXPIRED.

## Acceptance Criteria

### AC-001: Desconto aplicado
- Requirements: REQ-001
Given an order of 100 and a 10% coupon When it is applied Then the total is 90.

### AC-002: Cupom expirado
- Requirements: REQ-002
Given an expired coupon When it is applied Then the total stays 100 and the error is COUPON_EXPIRED.

## Constraints

- Coupon codes come from user input and reach the database.
