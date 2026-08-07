# Data Stores

## Goal

Define persistence ownership, Postgres schemas, caches, and Inbox/Outbox patterns according to the current microservices codebase.

## Source of truth

This file was updated on **2026-06-25** after reviewing service bootstraps (`Program.cs`), endpoints, repositories, and Kafka configuration.

## Principles

1. Each microservice exclusively owns its data.
2. In local development, schemas may share the same Postgres instance from `docker-compose.yml`.
3. No microservice should directly access another service's table or schema.
4. Service integration happens through REST APIs or Kafka.
5. Outbox/Inbox is documented as implemented only when it actually exists in the current code/registration.

## Implemented data matrix

| Service | Current schema/database | Owned data | Cache | Observed Kafka persistence pattern |
|---|---|---|---|---|
| Marketplace BFF (`MarketplaceWeb.Bff`) | No dedicated database | Transient web-experience aggregation; shopping cart is the only persisted-state exception | Redis with `cart:` prefix (`cart:<cartOwnerId>`) | Publishes `cart.abandoned` directly, without outbox, when a cart is inactive beyond the configured threshold |
| Product Search Service | `Default` connection string; read model in `products` table | Active-product search index/read model | Not registered in current bootstrap | No direct Kafka usage in current code |
| Checkout Service | `CheckoutDb`; falls back to mocks without a connection string | Checkout, items, idempotency, promise projection | Redis not registered in current bootstrap | Publishes `checkout.shipping.quote.requested` and `checkout.confirmed`; consumes `shipping.promise.calculated` when Kafka is configured |
| Shipping Promise Service | `ShippingPromiseDb` | Calculated promises and composition audit/snapshot | Redis with `shipping-promise:` prefix | Consumes `checkout.shipping.quote.requested`; publishes `shipping.promise.calculated` |
| Product Catalog Service | `product_catalog` through `ProductCatalogDbConnectionFactory` | SKU logistics attributes, weight, dimensions, and restrictions | Redis | Has an outbox writer; no dispatcher is registered in the current `Program.cs` |
| Inventory Service | `InventoryDb` | Inventory balances and reservations | Not registered | Consumes `inventory.commands`; publishes `inventory.reserved`, `inventory.reservation.confirmed`, `inventory.reservation.failed`, `inventory.reservation.released` |
| Fulfillment Center Service | `FulfillmentDb` | Fulfillment centers, capacity, operating calendar, and reservations | Not registered | Consumes `fulfillment.commands`; publishes `fulfillment.capacity.reserved`, `fulfillment.capacity.confirmed`, `fulfillment.capacity.failed` |
| Routing Service | `RoutingDb`; can use a mock repository | Logistics graph, lanes, and calculated routes | Redis with `routing:` prefix or distributed memory cache in mock mode | Kafka is not used in current bootstrap |
| Carrier Service | `CarrierDb` | Carriers, service levels, lanes, status, and availability | Redis with `carrier:` prefix | Has an administrative outbox writer; no dispatcher is currently registered |
| Shipping Pricing Service | `PricingDb` | Rate cards, policies, prices, and quotes | Redis with `shipping-pricing:` prefix | Has an outbox writer; no dispatcher is currently registered |
| Payment Service | Postgres schema `payment` (`search_path`) | `PaymentAuthorization`, inbox, and outbox | Not registered | Consumes `payment.commands`; publishes `payment.approved`, `payment.rejected`, `payment.captured`, `payment.capture.failed` |
| Order Service | `OrderDb`; fallback schema `order_domain` | Orders, items, inbox, outbox, saga state, and idempotency | Not registered | Consumes checkout/inventory/fulfillment/payment/shipment/status events and publishes `order.created`, `inventory.commands`, `fulfillment.commands`, `payment.commands`, `shipment.commands`, `order.events` |
| Shipment Service | `ShipmentDb` | Shipment, packages, items, label, inbox/outbox | FileSystem for labels; no registered cache | Consumes `order.created` and `shipment.commands`; publishes `shipment.created`; writes `carrier-shipment.commands` on cancellation |
| Tracking Service | `TrackingDb` | `ShipmentTracking` and `TrackingEvent` | Not registered | Consumes `shipment.created`; publishes `shipment.status.updated` |
| Notification Service | `NotificationDb` | Notifications, deliveries, preferences, outbox/inbox | Not registered | Consumes events configured in `KafkaOptions`; sends Email/SMS/Push through external channels rather than canonical Kafka events |
| Audit Service | Postgres schema `audit` (`search_path`), using Dapper/Npgsql rather than EF Core | Immutable `AuditEntry` records and inbox | Not registered | Consumes the ten canonical topics that currently have real producers; publishes no events |
| Order Visibility Service | Postgres schema `order_visibility` (`OrderVisibilityDb`) | `order_journey` consolidated status and `order_journey_events` timeline; its own read model, not a transactional source of truth | Not registered | Consumes checkout/order/inventory/fulfillment/payment/shipment/tracking events, except `*.commands`; publishes no Kafka events and pushes updates to the UI through SignalR |

## Local infrastructure

The repository's `docker-compose.yml` provides shared development/demo infrastructure:

| Resource | Local use |
|---|---|
| Postgres `logistica_envios` | Shared local database with domain schemas where applicable |
| Redis | Local cache for services that register Redis at bootstrap |
| Kafka | Local broker for configured events and commands |
| Kafka UI | Manual topic inspection |
| Prometheus/Grafana | Local observability |

## Schema conventions

| Type | Convention |
|---|---|
| Postgres schema | Domain-level `snake_case` when the service uses an explicit schema |
| Outbox | Producer-owned outbox table when implemented |
| Inbox | Consumer-owned inbox table when implemented |
| Idempotency | Persisted in the domain when exposed by an API or critical command |
| Redis key prefix | Prefix defined at service bootstrap when Redis is registered |

## Notes

- `ProductSearchService` must not be described as currently running on OpenSearch: the code registers `PostgresProductSearchRepository`.
- `AuditService` intentionally uses Dapper/Npgsql instead of EF Core; this is an explicit architectural choice.
- Topics without an implemented producer must be marked as configured/pending rather than described as production-ready end-to-end flows.
- The shopping cart in `MarketplaceWeb.Bff` (`cart:<cartOwnerId>` in Redis) is a deliberate exception to the rule that BFFs should not own persistent state. It is ephemeral session/UX data, not a durable business record. Publishing `cart.abandoned` without an outbox is acceptable because a lost or duplicated reminder has substantially lower severity than saga events such as payment or inventory. This exception should not be used as precedent for moving other domain data into a BFF.
