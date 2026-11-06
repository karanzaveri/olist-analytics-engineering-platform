# Instructor solution · Keep separate from the learner handout

## Reference implementation

Create the four `raw_*` connections and four clean references as in the assignment. The correct order is trim and normalize, cast, remove full-row duplicates, then assert the documented keys are unique. The lab has one exact duplicate in each file. There are five real multi-line orders, so deduplicating by order ID on the item table destroys data.

For reliable locale handling in M, the following is the type step for items. Keep the original CSV query as a separate connection.

```powerquery
Table.TransformColumnTypes(
    Trimmed,
    {{"order_id", type text}, {"order_item_id", Int64.Type},
     {"product_id", type text}, {"price", Currency.Type},
     {"freight_value", Currency.Type}},
    "en-US"
)
```

Use `type datetime` for the order timestamps. After trimming category text, a custom category expression is `if [product_category_name] = null or [product_category_name] = "" then "Uncategorized" else [product_category_name]`. Use the new category column in the product expansion.

The following query assumes the clean reference names below and that `products_clean` exposes its filled category as `category`. The populated right-side keys allow unmatched joins to be distinguished from missing attributes.

```powerquery
let
    Orders = Table.NestedJoin(items_clean, {"order_id"}, orders_clean, {"order_id"}, "o", JoinKind.LeftOuter),
    OrderFields = Table.ExpandTableColumn(Orders, "o",
        {"order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_delivered_customer_date"},
        {"matched_order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_delivered_customer_date"}),
    Customers = Table.NestedJoin(OrderFields, {"customer_id"}, customers_clean, {"customer_id"}, "c", JoinKind.LeftOuter),
    CustomerFields = Table.ExpandTableColumn(Customers, "c",
        {"customer_id", "customer_state"}, {"matched_customer_id", "customer_state"}),
    Products = Table.NestedJoin(CustomerFields, {"product_id"}, products_clean, {"product_id"}, "p", JoinKind.LeftOuter),
    ProductFields = Table.ExpandTableColumn(Products, "p", {"product_id", "category"}, {"matched_product_id", "category"}),
    Audit = Table.AddColumn(ProductFields, "exception_reason", each
        if [matched_order_id] = null then "Missing order"
        else if [matched_customer_id] = null then "Missing customer"
        else if [matched_product_id] = null then "Missing product"
        else if [price] = null or [price] < 0 then "Missing or invalid price"
        else if [freight_value] = null or [freight_value] < 0 then "Missing or invalid freight"
        else if [order_purchase_timestamp] = null then "Missing purchase timestamp"
        else if [customer_state] = null or [customer_state] = "" then "Missing state"
        else null, type nullable text)
in
    Audit
```

Save that as `items_joined`. For `item_exceptions` use `Table.SelectRows(items_joined, each [exception_reason] <> null)`. The supplied fixture has no conversion-error cells after the explicit types. For other files, resolve or quarantine conversion errors before this expression. For `delivered_sales` and its summary use:

```powerquery
// delivered_sales
let
    Valid = Table.SelectRows(items_joined, each [exception_reason] = null),
    Delivered = Table.SelectRows(Valid, each [order_status] = "delivered"),
    Month = Table.AddColumn(Delivered, "purchase_month",
        each Date.StartOfMonth(Date.From([order_purchase_timestamp])), type date)
in
    Month
```

```powerquery
// sales_by_month_state
let
    Groups = Table.Group(delivered_sales, {"purchase_month", "customer_state"},
        {{"item_lines", each Table.RowCount(_), Int64.Type},
         {"merchandise_brl", each List.Sum([price]), Currency.Type},
         {"freight_brl", each List.Sum([freight_value]), Currency.Type}}),
    Sorted = Table.Sort(Groups, {{"purchase_month", Order.Ascending}, {"customer_state", Order.Ascending}})
in
    Sorted
```

## Review key

- Item 99 has a missing price. Item 100 references `lab-missing-product`. Both belong in exceptions. One genuine, matched product has a deliberately blank category. Keep its delivered line in sales under `Uncategorized`.
- An order can be valid even with no delivery date. Filter delivered sales by normalized order status. The six other-status orders are outside the delivered report, so their valid item rows do not appear in the exception table.
- Compare all 16 rows with [expected-sales-by-month-state.csv](expected-sales-by-month-state.csv), matching the CSV's `YYYY-MM` month to the workbook's month-start date. Check 45 lines across 40 delivered orders and verify the BRL 6,367.98 merchandise and BRL 1,121.54 freight totals separately.
- Grade reproducibility by refreshing from the CSVs. Check that raw queries still preserve the import, each cleaned lookup is unique, and the three left joins never multiply item rows.
