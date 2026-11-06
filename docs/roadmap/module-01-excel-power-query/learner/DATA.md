# Exercise data

The bundled files contain a training extract of the Brazilian Olist marketplace data. It includes the first 20 delivered and first 3 other-status orders with item rows in each of June and July 2018, ordered by purchase timestamp and then order ID. The extract includes all item rows for the selected orders and the corresponding customers and products. Some records were deliberately altered or added for the exercise. Use these files to study cleaning and reporting. The selection is unsuitable for estimating marketplace-wide sales or comparing monthly performance.

The files are UTF-8 with comma delimiters, decimal points, and ISO-style timestamps. Blank cells represent missing values. Row counts exclude headers.

| CSV | Raw rows | Row grain and key |
|---|---:|---|
| `orders.csv` | 47 | One order per `order_id` after cleaning |
| `customers.csv` | 47 | One order-customer record per `customer_id`. `customer_unique_id` identifies the shopper across orders and can recur. |
| `products.csv` | 49 | One product per `product_id` after cleaning |
| `order_items.csv` | 55 | One item line per `order_id` + `order_item_id`. A single order can have multiple lines. |

- Treat IDs, ZIP prefixes, state, category, and status as **Text**. A ZIP prefix is a code.
- `order_purchase_timestamp` and `order_delivered_customer_date` are **Date/Time**. A missing delivery date can be legitimate. Use purchase date to assign the reporting month.
- `order_item_id` is a **Whole Number** within each order.
- `price` is the item's merchandise amount in BRL. `freight_value` is its separate shipping amount. Use **Fixed Decimal Number** for both.
- `product_category_name` contains the original Portuguese category labels where available.
