# License Service - Architecture & Design Documentation

## Problem Statement

group.one is integrating multiple WordPress-focused brands (WP Rocket, Imagify, RankMath, BackWPup, RocketCDN, WP.one) into a unified ecosystem. A key requirement is a **centralized License Service** that acts as the single source of truth for license lifecycle and entitlements across all brands.

### Key Requirements

1. **Multi-tenant support** - Each brand operates independently with its own products and API credentials
2. **License provisioning** - Brands can create license keys and associate multiple product licenses
3. **License lifecycle management** - Support for renewal, suspension, resumption, and cancellation
4. **Activation management** - End-user products can activate licenses on specific instances with seat limits
5. **Validation** - Products can verify license validity in real-time
6. **Cross-brand lookup** - Ability to query all licenses for a customer email across the ecosystem

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                        License Service                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │  Brand API   │     │ Product API  │     │  Admin UI    │        │
│  │  (Internal)  │     │  (Public)    │     │  (Django)    │        │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘        │
│         │                    │                    │                 │
│         └────────────────────┼────────────────────┘                 │
│                              │                                      │
│                    ┌─────────▼─────────┐                           │
│                    │   Service Layer   │                           │
│                    │   (Business Logic)│                           │
│                    └─────────┬─────────┘                           │
│                              │                                      │
│                    ┌─────────▼─────────┐                           │
│                    │   Data Layer      │                           │
│                    │   (Django ORM)    │                           │
│                    └─────────┬─────────┘                           │
│                              │                                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │     PostgreSQL      │
                    └─────────────────────┘
```

### Data Model

```
┌─────────────┐       ┌─────────────┐
│   Brand     │───────│   Product   │
│             │ 1   * │             │
└─────────────┘       └──────┬──────┘
      │                      │
      │ 1                    │ 1
      │                      │
      ▼ *                    ▼ *
┌─────────────┐       ┌─────────────┐
│ LicenseKey  │───────│   License   │
│             │ 1   * │             │
└─────────────┘       └──────┬──────┘
                             │ 1
                             │
                             ▼ *
                      ┌─────────────┐
                      │ Activation  │
                      └─────────────┘
```

### Entity Descriptions

| Entity | Description |
|--------|-------------|
| **Brand** | A tenant in the system (e.g., WP Rocket, RankMath). Has unique API credentials. |
| **Product** | A product within a brand (e.g., RankMath Pro, Content AI). Has default seat limits. |
| **LicenseKey** | Customer-facing key that can unlock multiple licenses. Tied to customer email and one brand. |
| **License** | Individual product entitlement with status, expiration, and seat limit. |
| **Activation** | Instance where a license is activated (site URL, machine ID). Consumes a seat. |

---

## Design Decisions & Trade-offs

### 1. Multi-Tenancy Approach

**Decision**: Shared database with tenant isolation via foreign keys (not schema-per-tenant).

**Rationale**:
- Simpler to implement and maintain
- Sufficient for the expected scale (dozens of brands, not thousands)
- Easier cross-brand queries (US6 requirement)
- Lower operational overhead

**Trade-off**: Less isolation between tenants. Mitigated by:
- API key authentication per brand
- Query filtering by brand in all endpoints
- Database-level constraints

**Alternative considered**: Schema-per-tenant would provide stronger isolation but adds complexity for cross-brand queries and migrations.

### 2. License Key Structure

**Decision**: One license key per brand per customer, with multiple licenses attached.

**Rationale**:
- Matches the user story example (RankMath + Content AI on same key, WP Rocket on different key)
- Simplifies customer experience within a brand
- Allows cross-selling within brand ecosystem

**Trade-off**: Customers need multiple keys for multiple brands. This is intentional per requirements.

### 3. Authentication Strategy

**Decision**: Two separate authentication mechanisms:
- **Brand API**: API Key + Secret in headers
- **Product API**: License key (no additional auth)

**Rationale**:
- Brand systems are trusted internal services - API key auth is simple and effective
- Product API needs to be accessible from WordPress plugins - license key is the natural auth token
- Separating the APIs prevents accidental privilege escalation

**Trade-off**: Product API is "public" - anyone with a license key can validate it. This is acceptable as:
- License keys are meant to be shared with customers
- No sensitive operations exposed (only activation/validation)
- Rate limiting can be added for abuse prevention

### 4. Seat Management

**Decision**: Implemented with configurable limits per license (0 = unlimited).

**Rationale**:
- Flexible for different product tiers
- Simple counting model (active activations vs limit)
- Reactivation of same instance doesn't consume additional seat

**Implementation details**:
- `seat_limit = 0` means unlimited activations
- Deactivation frees the seat immediately
- Same instance can be reactivated without consuming new seat

### 5. License Status Model

**Decision**: Four statuses: `valid`, `suspended`, `cancelled`, `expired`.

**Rationale**:
- `valid`: Active and usable
- `suspended`: Temporarily disabled (e.g., payment issue), can be resumed
- `cancelled`: Permanently disabled, cannot be resumed
- `expired`: Time-based expiration (checked dynamically)

**Note**: `expired` is computed from `expires_at`, not stored. This ensures accuracy without background jobs.

---

## User Story Implementation

### US1: Brand can provision a license ✅ IMPLEMENTED

**Endpoints**:
- `POST /api/v1/brand/license-keys/` - Create license key
- `POST /api/v1/brand/license-keys/{key}/licenses/` - Add license to key

**Flow**:
1. Brand creates a license key for customer email
2. Brand adds one or more product licenses to the key
3. License key is returned to brand for delivery to customer

**Example scenario from requirements**:
```
1. User buys RankMath → Create LicenseKey #1 + RankMath license
2. User buys Content AI → Add Content AI license to LicenseKey #1
3. User buys WP Rocket → Create LicenseKey #2 + WP Rocket license
```

### US2: Brand can change license lifecycle ✅ IMPLEMENTED

**Endpoints**:
- `POST /api/v1/brand/licenses/{id}/renew/` - Extend expiration
- `POST /api/v1/brand/licenses/{id}/suspend/` - Suspend license
- `POST /api/v1/brand/licenses/{id}/resume/` - Resume suspended license
- `POST /api/v1/brand/licenses/{id}/cancel/` - Cancel license

### US3: End-user product can activate a license ✅ IMPLEMENTED

**Endpoint**: `POST /api/v1/product/activate/`

**Flow**:
1. Product sends license key, product slug, and instance ID
2. Service validates license (status, expiration, seat limit)
3. Creates or reactivates activation record
4. Returns activation confirmation with seat info

**Seat enforcement**: If `seat_limit > 0` and all seats used, activation fails with `seat_limit_exceeded` error.

### US4: User can check license status ✅ IMPLEMENTED

**Endpoints**:
- `POST /api/v1/product/validate/` - Quick validation
- `GET /api/v1/product/status/?license_key=` - Full status

**Validation response includes**:
- Overall validity
- Per-license status, expiration, seat usage
- Product information

### US5: End-user product can deactivate a seat ✅ IMPLEMENTED

**Endpoint**: `POST /api/v1/product/deactivate/`

**Flow**:
1. Product sends license key, product slug, and instance ID
2. Service finds and deactivates the activation
3. Seat is freed for reuse

### US6: Brands can list licenses by customer email ✅ IMPLEMENTED

**Endpoint**: `GET /api/v1/brand/customers/?email=`

**Returns**: All license keys and licenses for the email across ALL brands.

**Note**: This is a cross-brand query, intentionally accessible to any authenticated brand for support purposes.

---

## Observability & Operations

### Logging

- **Structured JSON logging** in production for log aggregation
- **Request ID tracking** via middleware (`X-Request-ID` header)
- **Context-rich logs**: Include license IDs, customer emails, operation types

### Health Checks

- `GET /api/v1/health/` - Returns service and database health
- Suitable for load balancer health checks and monitoring

### Error Handling

- Consistent error response format:
```json
{
  "error": {
    "code": "license_not_found",
    "message": "License not found",
    "details": {}
  },
  "meta": {
    "request_id": "abc123"
  }
}
```

- Custom exception classes for domain errors
- Proper HTTP status codes (400, 401, 404, 500)

### Monitoring (Design)

For production deployment, recommend:
- **Metrics**: Request count, latency percentiles, error rates
- **Alerts**: High error rate, slow responses, database connectivity
- **Dashboards**: License creation rate, activation patterns, seat utilization

---

## Scaling Considerations

### Current Design Limits

The current implementation is suitable for:
- Hundreds of brands
- Millions of license keys
- Tens of millions of activations

### Scaling Strategies

1. **Database**:
   - Add read replicas for validation queries
   - Partition activations table by date
   - Add indexes on frequently queried fields (already done)

2. **Caching** (future):
   - Cache license validation results (short TTL)
   - Cache brand credentials
   - Use Redis for distributed caching

3. **API**:
   - Add rate limiting per brand/license key
   - Implement request queuing for high-traffic periods
   - Consider async processing for non-critical operations

4. **Horizontal Scaling**:
   - Stateless application servers behind load balancer
   - Database connection pooling (PgBouncer)

---

## Security Considerations

### Implemented

- API key authentication for brand endpoints
- No sensitive data in logs (passwords, full API secrets)
- Input validation on all endpoints
- SQL injection prevention via ORM
- CORS configuration for production

### Recommended for Production

- HTTPS enforcement
- API key rotation mechanism
- Rate limiting
- Request signing for brand API
- Audit logging for sensitive operations
- Regular security audits

---

## Known Limitations

1. **No background jobs**: License expiration is checked on-demand, not proactively. Expired licenses remain in database until queried.

2. **No webhook notifications**: Brands are not notified of license events. Would require message queue infrastructure.

3. **No bulk operations**: Creating many licenses requires multiple API calls. Batch endpoints could be added.

4. **Simple seat model**: No support for concurrent seat limits or floating licenses. Current model is "named seats" (one activation per instance).

5. **No license transfer**: Cannot transfer license between customers without manual intervention.

---

## Next Steps

1. **Rate limiting**: Implement per-brand and per-license-key rate limits
2. **Webhooks**: Notify brands of license events (activation, expiration)
3. **Analytics**: Track license usage patterns for business insights
4. **Bulk operations**: Batch license creation for enterprise customers
5. **License transfer**: API for transferring licenses between customers
6. **Audit log**: Detailed audit trail for compliance

---

## How to Run Locally

See [README.md](README.md) for detailed setup instructions.

### Quick Start

```bash
# With Docker
docker-compose up -d

# Without Docker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Create Test Data

```bash
# Create a superuser
python manage.py createsuperuser

# Access admin at http://localhost:8000/admin/
# Create a Brand, then a Product
# Use the API to create license keys
```

### Run Tests

```bash
pytest -v
pytest --cov=apps
```
