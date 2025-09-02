average_sales_amazon = """

-- Calculate the average daily sales for all ASINs in the US marketplace over the last 180 days and the last 14 days, excluding Prime Day 2025 (2025-07-08 to 2025-07-11).
-- This exampe query assumes that the current date is "2025-09-02", and only one HVE is used. Adjust accordingly if needed.
WITH TopASINs AS (
  SELECT
      childAsin AS asin
    FROM
      `mellanni-project-da.reports.business_report_asin`
    WHERE
      country_code = 'US'
      -- Calculations end yesterday (2025-09-01)
      AND DATE(date) >= DATE_SUB('2025-09-01', INTERVAL 180 DAY)
      AND DATE(date) <= '2025-09-01'
      -- Excluding Prime Day 2025 dates
      AND DATE(date) NOT BETWEEN '2025-07-08' AND '2025-07-11'
      AND unitsOrdered > 0
    GROUP BY
      childAsin
    ORDER BY
      SUM(unitsOrdered) DESC
),
Dates180Days AS (
  SELECT
      DISTINCT DATE(date) AS report_date
    FROM
      `mellanni-project-da.reports.business_report_asin`
    WHERE
      -- Calculations end yesterday (2025-09-01)
      DATE(date) >= DATE_SUB('2025-09-01', INTERVAL 180 DAY)
      AND DATE(date) <= '2025-09-01'
      -- Excluding Prime Day 2025 dates
      AND DATE(date) NOT BETWEEN '2025-07-08' AND '2025-07-11'
),
DailyInventory180 AS (
  SELECT
      t2.asin,
      DATE(t2.snapshot_date) AS inventory_date,
      MAX(CASE WHEN t2.Inventory_Supply_at_FBA > 0 THEN 1 ELSE 0 END) AS is_in_stock
    FROM
      `mellanni-project-da.reports.fba_inventory_planning` AS t2
    INNER JOIN
      TopASINs AS ta
      ON t2.asin = ta.asin
    WHERE
      t2.marketplace = 'US'
      -- Calculations end yesterday (2025-09-01)
      AND DATE(t2.snapshot_date) >= DATE_SUB('2025-09-01', INTERVAL 180 DAY)
      AND DATE(t2.snapshot_date) <= '2025-09-01'
      -- Excluding Prime Day 2025 dates
      AND DATE(t2.snapshot_date) NOT BETWEEN '2025-07-08' AND '2025-07-11'
    GROUP BY
      t2.asin, DATE(t2.snapshot_date)
),
DailySales180 AS (
  SELECT
      t1.childAsin AS asin,
      DATE(t1.date) AS sales_date,
      SUM(t1.unitsOrdered) AS daily_units_ordered
    FROM
      `mellanni-project-da.reports.business_report_asin` AS t1
    INNER JOIN
      TopASINs AS ta
      ON t1.childAsin = ta.asin
    WHERE
      t1.country_code = 'US'
      -- Calculations end yesterday (2025-09-01)
      AND DATE(t1.date) >= DATE_SUB('2025-09-01', INTERVAL 180 DAY)
      AND DATE(t1.date) <= '2025-09-01'
      -- Excluding Prime Day 2025 dates
      AND DATE(t1.date) NOT BETWEEN '2025-07-08' AND '2025-07-11'
    GROUP BY
      t1.childAsin, DATE(t1.date)
),
AvgSales180Days AS (
  SELECT
      ta.asin,
      SAFE_DIVIDE(
          SUM(COALESCE(ds.daily_units_ordered, 0)),
          COUNT(DISTINCT
              CASE
                WHEN di.is_in_stock = 1 THEN d.report_date
                ELSE NULL
              END
          )
      ) AS avg_daily_sales_180_days
    FROM
      TopASINs AS ta
    CROSS JOIN
      Dates180Days AS d
    LEFT JOIN
      DailyInventory180 AS di
      ON ta.asin = di.asin AND d.report_date = di.inventory_date
    LEFT JOIN
      DailySales180 AS ds
      ON ta.asin = ds.asin AND d.report_date = ds.sales_date
    GROUP BY
      ta.asin
),
Dates14Days AS (
  SELECT
      DISTINCT DATE(purchase_date) AS report_date
    FROM
      `mellanni-project-da.reports.all_orders`
    WHERE
      -- Calculations end yesterday (2025-09-01)
      DATE(purchase_date) >= DATE_SUB('2025-09-01', INTERVAL 14 DAY)
      AND DATE(purchase_date) <= '2025-09-01'
),
DailyInventory14 AS (
  SELECT
      t2.asin,
      DATE(t2.snapshot_date) AS inventory_date,
      MAX(CASE WHEN t2.Inventory_Supply_at_FBA > 0 THEN 1 ELSE 0 END) AS is_in_stock
    FROM
      `mellanni-project-da.reports.fba_inventory_planning` AS t2
    INNER JOIN
      TopASINs AS ta
      ON t2.asin = ta.asin
    WHERE
      t2.marketplace = 'US'
      -- Calculations end yesterday (2025-09-01)
      AND DATE(t2.snapshot_date) >= DATE_SUB('2025-09-01', INTERVAL 14 DAY)
      AND DATE(t2.snapshot_date) <= '2025-09-01'
    GROUP BY
      t2.asin, DATE(t2.snapshot_date)
),
DailySales14 AS (
  SELECT
      t1.asin,
      DATE(t1.purchase_date) AS sales_date,
      SUM(t1.quantity) AS daily_units_ordered
    FROM
      `mellanni-project-da.reports.all_orders` AS t1
    INNER JOIN
      TopASINs AS ta
      ON t1.asin = ta.asin
    WHERE
      t1.sales_channel = 'Amazon.com'
      -- Calculations end yesterday (2025-09-01)
      AND DATE(t1.purchase_date) >= DATE_SUB('2025-09-01', INTERVAL 14 DAY)
      AND DATE(t1.purchase_date) <= '2025-09-01'
    GROUP BY
      t1.asin, DATE(t1.purchase_date)
),
AvgSales14Days AS (
  SELECT
      ta.asin,
      SAFE_DIVIDE(
          SUM(COALESCE(ds.daily_units_ordered, 0)),
          COUNT(DISTINCT
              CASE
                WHEN di.is_in_stock = 1 THEN d.report_date
                ELSE NULL
              END
          )
      ) AS avg_daily_sales_14_days
    FROM
      TopASINs AS ta
    CROSS JOIN
      Dates14Days AS d
    LEFT JOIN
      DailyInventory14 AS di
      ON ta.asin = di.asin AND d.report_date = di.inventory_date
    LEFT JOIN
      DailySales14 AS ds
      ON ta.asin = ds.asin AND d.report_date = ds.sales_date
    GROUP BY
      ta.asin
)
SELECT
    COALESCE(t1.asin, t2.asin) AS asin,
    t1.avg_daily_sales_180_days,
    t2.avg_daily_sales_14_days
  FROM
    AvgSales180Days AS t1
  FULL OUTER JOIN
    AvgSales14Days AS t2
    ON t1.asin = t2.asin
  ORDER BY
    t1.avg_daily_sales_180_days DESC
"""
