# HTTP Contract Validation — Logistics Marketplace

Revalidation date: 2026-06-14

## Goal

Revalidate the HTTP contracts across the Logistics Marketplace repositories after fixing the eight issues identified in the previous validation.

Reference consolidated OpenAPI file:

- [`logistica-envios-apis.openapi.yaml`](logistica-envios-apis.openapi.yaml)

## Validation method

The validation prioritized the current implementation of HTTP endpoints and clients:

- `Api/*Endpoints.cs`
- `Clients/*Client.cs`
- `Contracts/*.cs`
- `Program.cs` when required to confirm endpoint mappings

## Executive result

All eight critical issues from the previous validation were fixed.

| Item | Validation | Status |
|---|---|---:|
| 1 | `ShippingPromiseService -> FulfillmentCenterService` maps the actual Fulfillment response. | OK |
| 2 | `ShippingPromiseService -> RoutingService` reads `SearchRoutesResponse.routes[]` and maps it to `RouteOption`. | OK |
| 3 | `ShippingPromiseService -> CarrierService` sends `checkId` in each item of `checks`. | OK |
| 4 | `ShippingPromiseService -> ShippingPricingService` sends `buyerId`, `sellerId`, `destinationPostalCode`, `cartTotal`, `currency`, and `candidates[]`. | OK |
| 5 | `MarketplaceWeb.Bff -> TrackingService` calls `GET /tracking/shipments/{shipmentId}`. | OK |
| 6 | `MarketplaceWeb.Bff -> OrderService` no longer calls `GET /orders`. | OK |
| 7 | `MarketplaceWeb.Bff -> OrderService` sends a cancellation body and handles `202 Accepted` without a response body. | OK |
| 8 | `MarketplaceWeb.Bff -> ShipmentService` handles the label as JSON containing `url` and `expiresInSeconds`. | OK |

## Status by component

| Component | Status | Result |
|---|---:|---|
| MarketplaceWeb | N/A | Web frontend; does not expose a downstream API. |
| MarketplaceWeb.Bff | OK | Endpoints and downstream clients revalidated. |
| ProductSearchService | OK | `GET /v1/products/search` is compatible with the BFF. |
| ProductCatalogService | OK | `GET /products/{skuId}` and `POST /products/physical-info/batch` are compatible. |
| CheckoutService | OK | `POST /checkouts`, `GET /checkouts/{checkoutId}`, and `POST /checkouts/{checkoutId}/confirm` are compatible with the BFF. |
| ShippingPromiseService | OK | Public endpoint and downstream clients revalidated. |
| InventoryService | OK | Endpoint and response are compatible with `ShippingPromiseService`. |
| FulfillmentCenterService | OK | Route, request, and response are compatible through the `ShippingPromiseService` adapter. |
| RoutingService | OK | Route and response are compatible through the `ShippingPromiseService` adapter. |
| CarrierService | OK | Request now includes the required `checkId`. |
| ShippingPricingService | OK | Request and response are compatible through the `ShippingPromiseService` adapter. |
| OrderService | OK | Query-by-ID and cancellation are compatible with the BFF. |
| ShipmentService | OK | Label JSON is compatible with the BFF. |
| TrackingService | OK | Shipment lookup route is compatible with the BFF. |
| NotificationService | OK | HTTP endpoints match the current documentation. |

## Revalidation details

### 1. ShippingPromiseService -> FulfillmentCenterService

**Status:** OK.

The client still calls:

```http
POST /fulfillment-centers/candidates/search
```

It now deserializes the real `FulfillmentCenterService` response into a downstream DTO:

```csharp
FulfillmentCenterCandidateResponse(
  Guid FulfillmentCenterId,
  string Region,
  DateTimeOffset CutoffAt,
  int AvailableCapacityUnits,
  int Score)
```

and maps it to the internal model:

```csharp
FulfillmentCandidate(
  FulfillmentCenterId,
  Region,
  TimeOnly.FromTimeSpan(CutoffAt.TimeOfDay),
  AvailableCapacityUnits > 0,
  Score)
```

The mismatch between `cutoffAt`/`availableCapacityUnits`/`score` and `cutoffTime`/`hasCapacity`/`capacityScore` is resolved.

### 2. ShippingPromiseService -> RoutingService

**Status:** OK.

The client calls:

```http
POST /routes/search
```

and now deserializes the correct response object:

```csharp
SearchRoutesResponse(IReadOnlyList<RouteResponse>? Routes)
```

Each route is mapped to `RouteOption` using `routeId`, origin/destination node IDs, elapsed time, carrier code, and service-level/mode information.

### 3. ShippingPromiseService -> CarrierService

**Status:** OK.

The client still calls:

```http
POST /carrier-availability/search
```

and now includes the required `checkId` in each check:

```csharp
checkId = $"{route.RouteId}:{route.CarrierCode}:{route.ServiceLevelCode}"
```

### 4. ShippingPromiseService -> ShippingPricingService

**Status:** OK.

The client calls:

```http
POST /shipping-prices/quotes/batch
```

with the expected payload:

```json
{
  "buyerId": "guid",
  "sellerId": "guid",
  "destinationPostalCode": "01310-100",
  "cartTotal": 199.90,
  "currency": "BRL",
  "requestedAtUtc": "2026-06-14T00:00:00Z",
  "candidates": []
}
```

It also reads `customerPrice` as the customer-facing cost:

```csharp
new ShippingPrice(price.CustomerPrice, price.Discount)
```

### 5. MarketplaceWeb.Bff -> TrackingService

**Status:** OK.

The BFF now calls the actual route:

```http
GET /tracking/shipments/{shipmentId}
```

The BFF DTO still contains `Events`, while the main endpoint does not return history. If the UI needs history, the BFF should also call:

```http
GET /tracking/shipments/{shipmentId}/events
```

or treat `Events` as optional/empty.

### 6. MarketplaceWeb.Bff -> OrderService — listing

**Status:** OK.

The invalid `GET /orders` call was removed. The BFF now exposes only lookup by order ID and correctly calls:

```http
GET /orders/{orderId}
```

### 7. MarketplaceWeb.Bff -> OrderService — cancellation

**Status:** OK.

The BFF now forwards the cancellation body and treats the downstream response as `202 Accepted` without a response body.

```http
POST /orders/{orderId}/cancel
Idempotency-Key: {key}
Content-Type: application/json

{
  "reason": "Buyer request"
}
```

### 8. MarketplaceWeb.Bff -> ShipmentService — label

**Status:** OK.

`ShipmentService` returns:

```json
{
  "url": "https://shipment.local/labels/...pdf",
  "expiresInSeconds": 300
}
```

The BFF now deserializes it as:

```csharp
ShipmentLabelDto(string Url, int ExpiresInSeconds)
```

and returns the same JSON payload to the frontend.

## Remaining recommendations

No critical HTTP-contract issue remained after the eight fixes. Two cleanup items remain:

1. Update the consolidated OpenAPI definition so `GET /api/web/v1/shipments/{shipmentId}/label` returns JSON rather than `application/pdf`.
2. Decide whether the BFF should fetch tracking history from `GET /tracking/shipments/{shipmentId}/events` or treat `Events` as optional/empty.

## Contract decision

> The canonical contract is always owned by the service that owns the API. Consumer clients adapt to the owner service, not the other way around.
