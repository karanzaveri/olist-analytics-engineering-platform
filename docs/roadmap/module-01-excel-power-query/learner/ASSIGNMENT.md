# Practical assignment · Build a delivered-sales report

You receive four monthly export files from a marketplace team. Build a refreshable summary that answers how much delivered merchandise and freight came from each customer state and purchase month. Keep a visible list of item rows you cannot trust for reporting.

## Exercise 1 · Import and profile

1. Open **Excel for Windows**, create a blank workbook, and save it as `Module 1 - My Olist Analysis.xlsx`.
2. Choose **Data → Get Data → From File → From Text/CSV** (or **Data → From Text/CSV**). Open [orders.csv](data/orders.csv). Confirm **UTF-8** and **Comma**, then select **Transform Data**.
3. Name the query `raw_orders`. Remove the automatically generated **Changed Type** step if present. Keep the header promotion step, or select **Use First Row as Headers** if the preview shows `Column1` headings.
4. Turn on **View → Column quality**, **Column distribution**, and **Column profile**. In the preview status bar, choose profiling based on the **entire data set**. Record the row count, one field that needs cleanup, and one field where a blank may be legitimate.
5. Repeat for [customers.csv](data/customers.csv), [products.csv](data/products.csv), and [order_items.csv](data/order_items.csv). Name the queries `raw_customers`, `raw_products`, and `raw_order_items`. Use **Home → Close & Load To… → Only Create Connection** for staging. If **Load To** is unavailable in the editor, set it via **Data → Queries & Connections**, right-click the query, then **Load To…**.
6. Check the four raw row counts against [the data dictionary](DATA.md). For an exact count, create a temporary **Reference** and use **Transform → Count Rows**.

## Exercise 2 · Create reusable clean queries

1. In Power Query Editor, right-click each raw query and select **Reference**. Name the new queries `orders_clean`, `customers_clean`, `products_clean`, and `items_clean`. Keep the raw queries unchanged so you can compare source and clean counts after a refresh.
2. Apply **Transform → Format → Trim** to the ID columns and to status, state, and category. Convert order status to lowercase and customer state to uppercase.
3. Set types using the dictionary. For price and freight use **Change Type → Using Locale → Fixed Decimal Number → English (United States)** so Excel on a comma-decimal Windows setup reads the dot correctly. Use **Date/Time** with the same explicit locale if Windows misreads the timestamps.
4. Remove exact duplicates by selecting all columns and using **Home → Remove Rows → Remove Duplicates**. To check key uniqueness, group a reference query by the documented key, use **Count Rows**, and filter for counts greater than 1. Never deduplicate item rows by order ID alone. If a key repeats with conflicting values, flag it for review instead of keeping an arbitrary row.
5. In `products_clean`, use **Add Column → Custom Column** to turn a blank category into `Uncategorized`. Retain the product row. Leave a missing price as null and leave missing delivery dates as null.

## Exercise 3 · Join and validate

1. Create a reference to `items_clean` named `items_joined`. Use **Home → Merge Queries** with a **Left Outer** join to `orders_clean` on `order_id`. Expand the order's customer ID, status, purchase timestamp and delivery date.
2. Merge to `customers_clean` using the customer ID from the order, then expand state. Merge to `products_clean` on `product_id` and expand the matched product ID and category. Turn off automatic prefixes or rename the expanded fields clearly, for example `matched_product_id`. Match text to text.
3. Record row counts after each merge and expansion. An increase indicates a nonunique key on the right. Use **Left Anti** joins in temporary references to confirm unmatched keys, or inspect the expanded right-side key for nulls. A matched product with a missing category stays `Uncategorized`; an item with no matching product is an exception.
4. Create `item_exceptions` as a reference to `items_joined`. Keep rows with missing/invalid price or freight, a missing match, an unusable purchase timestamp or a missing state. The supplied amounts must be nonnegative. Include the item key and a reason. Create a separate valid-items reference using the inverse rule. Resolve type conversion errors or explicitly flag them before reporting.

## Exercise 4 · Publish locally and reconcile

1. Reference the valid item rows, filter cleaned status to `delivered`, and name the query `delivered_sales`. Add a month-start date from `order_purchase_timestamp` (**Add Column → Date → Month → Start of Month** after extracting the date, or use a custom column).
2. Reference `delivered_sales` as `sales_by_month_state`. Choose **Home → Group By → Advanced**. Group by purchase month and customer state. Calculate **Count Rows**, **Sum of price**, and **Sum of freight_value**. Label the sums as BRL and keep the two amounts separate.
3. Load `sales_by_month_state` and `item_exceptions` as tables. Optionally load `delivered_sales` and create an Excel PivotTable with purchase month in rows, state in columns, and sum of price as values. Format amounts to two decimals and label them BRL. Count item lines separately from orders.
4. Run **Data → Refresh All** with the same local files. Compare the refreshed counts and totals with the checkpoints below. Submit your workbook and a short note explaining what you excluded and why.

| Checkpoint | Expected result |
|---|---|
| Clean orders / customers / products / item lines | 46 / 46 / 48 / 54 |
| Item rows after each left join and expansion | 54 |
| Missing order / customer / product matches | 0 / 0 / 1 |
| Exceptions / valid item rows | 2 / 52 |
| Delivered orders / delivered item lines | 40 / 45 |
| Delivered lines with a matched but uncategorized product | 1 |
| Month-state summary groups | 16 |
| Merchandise / freight totals | BRL 6,367.98 / BRL 1,121.54 |

[Microsoft’s Excel CSV import guide](https://support.microsoft.com/en-us/excel/get-started/import-or-export-text-txt-or-csv-files) · [Set a locale in Power Query](https://support.microsoft.com/en-us/excel/set-a-locale-or-region-for-data-power-query) · [Merge queries](https://support.microsoft.com/en-us/excel/merge-queries-power-query)
