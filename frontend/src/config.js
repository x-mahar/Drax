export const DASHBOARD_CONFIG = {
  title: 'Business Dashboard',

  kpis: [
    {
      id: 'total_revenue',
      title: 'Total Revenue',
      subtitle: 'ALL TIME',
      format: 'currency',
      color: 'primary',
    },
    {
      id: 'total_orders',
      title: 'Total Orders',
      subtitle: 'ALL TIME',
      format: 'number',
      color: 'secondary',
    },
    {
      id: 'total_customers',
      title: 'Total Customers',
      subtitle: 'ALL TIME',
      format: 'number',
      color: 'accent',
    },
    {
      id: 'avg_order_value',
      title: 'Avg Order Value',
      subtitle: 'PER CATEGORY',
      format: 'currency',
      color: 'default',
    },
  ],

  charts: [
    {
      id: 'revenue_trend',
      title: 'Revenue Trend',
      subtitle: 'BY MONTH',
      question: 'total payments received by month',
      chartType: 'area',
    },
    {
      id: 'category_breakdown',
      title: 'Sales by Category',
      subtitle: 'DISTRIBUTION',
      question: 'show total revenue by product category',
      chartType: 'pie',
    },
    {
      id: 'top_customers',
      title: 'Top Customers',
      subtitle: 'BY ORDER COUNT',
      question: 'top 5 customers by order count',
      chartType: 'hbar',
    },
    {
      id: 'regional_sales',
      title: 'Sales by Segment',
      subtitle: 'BY SEGMENT',
      question: 'show total orders by customer segment',
      chartType: 'bar',
    },
    {
      id: 'top_products',
      title: 'Top Products',
      subtitle: 'BY REVENUE',
      question: 'top 10 products by revenue',
      chartType: 'hbar',
    },
    {
      id: 'returns_trend',
      title: 'Returns by Category',
      subtitle: 'RETURN RATE',
      question: 'returns by category',
      chartType: 'bar',
    },
  ]
}