from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)


class DataGenerator:
    """Generate and manage sample sales data"""

    def __init__(self):
        self.regions = ['North', 'South', 'East', 'West']
        self.products = ['Electronics', 'Clothing', 'Home & Garden', 'Sports']
        self.data = self.generate_sample_data()

    def generate_sample_data(self, num_records=5000):
        """Generate realistic sample sales data"""
        np.random.seed(42)  # For reproducible data

        # Date range: last 2 years
        start_date = datetime.now() - timedelta(days=730)
        end_date = datetime.now()

        data = []

        for _ in range(num_records):
            # Random date in range
            random_date = start_date + timedelta(
                days=np.random.randint(0, (end_date - start_date).days)
            )

            # Seasonal patterns
            month = random_date.month
            seasonal_multiplier = 1.0
            if month in [11, 12]:  # Holiday season
                seasonal_multiplier = 1.5
            elif month in [6, 7, 8]:  # Summer
                seasonal_multiplier = 1.2

            # Regional patterns
            region = np.random.choice(self.regions)
            region_multiplier = {
                'North': 1.1, 'South': 0.9, 'East': 1.2, 'West': 1.0
            }[region]

            # Product patterns
            product = np.random.choice(self.products)
            base_price = {
                'Electronics': 500, 'Clothing': 80,
                'Home & Garden': 150, 'Sports': 120
            }[product]

            # Calculate sales with patterns
            base_sales = base_price * (0.5 + np.random.random() * 2)
            sales = base_sales * seasonal_multiplier * region_multiplier

            data.append({
                'date': random_date.strftime('%Y-%m-%d'),
                'region': region,
                'product': product,
                'sales': round(sales, 2),
                'orders': np.random.randint(1, 6),
                'customers': np.random.randint(20, 101),
                'customer_id': f'CUST_{np.random.randint(1000, 9999)}',
                'order_id': f'ORD_{np.random.randint(10000, 99999)}'
            })

        return pd.DataFrame(data)

    def get_filtered_data(self, region=None, product=None, date_range=None):
        """Filter data based on parameters"""
        df = self.data.copy()

        # Convert date column to datetime for filtering
        df['date'] = pd.to_datetime(df['date'])

        # Apply filters
        if region and region != 'all':
            df = df[df['region'] == region]

        if product and product != 'all':
            df = df[df['product'] == product]

        if date_range and date_range != 'all':
            days_back = int(date_range)
            cutoff_date = datetime.now() - timedelta(days=days_back)
            df = df[df['date'] >= cutoff_date]

        return df


# Initialize data generator
data_gen = DataGenerator()


@app.route('/')
def dashboard():
    """Serve the main dashboard"""
    return render_template('dashboard.html')


@app.route('/api/data')
def get_data():
    """API endpoint to get filtered data"""
    # Get filter parameters
    region = request.args.get('region', 'all')
    product = request.args.get('product', 'all')
    date_range = request.args.get('date_range', 'all')

    # Get filtered data
    df = data_gen.get_filtered_data(region, product, date_range)

    # Calculate metrics
    total_sales = df['sales'].sum()
    total_orders = df['orders'].sum()
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    unique_customers = df['customer_id'].nunique()
    conversion_rate = (total_orders / unique_customers * 100) if unique_customers > 0 else 0

    # Prepare data for charts
    response_data = {
        'metrics': {
            'total_sales': round(total_sales, 2),
            'total_orders': int(total_orders),
            'avg_order_value': round(avg_order_value, 2),
            'conversion_rate': round(conversion_rate, 1)
        },
        'charts': {
            'sales_trend': prepare_sales_trend(df),
            'region_data': prepare_region_data(df),
            'product_data': prepare_product_data(df),
            'growth_data': prepare_growth_data(df),
            'heatmap_data': prepare_heatmap_data(df)
        }
    }

    return jsonify(response_data)


def prepare_sales_trend(df):
    """Prepare data for sales trend chart"""
    # Group by date and sum sales
    daily_sales = df.groupby('date')['sales'].sum().reset_index()
    daily_sales['date'] = daily_sales['date'].dt.strftime('%Y-%m-%d')

    return {
        'dates': daily_sales['date'].tolist(),
        'sales': daily_sales['sales'].tolist()
    }


def prepare_region_data(df):
    """Prepare data for region pie chart"""
    region_sales = df.groupby('region')['sales'].sum().reset_index()

    return {
        'regions': region_sales['region'].tolist(),
        'sales': region_sales['sales'].tolist()
    }


def prepare_product_data(df):
    """Prepare data for product bar chart"""
    product_sales = df.groupby('product')['sales'].sum().reset_index()

    return {
        'products': product_sales['product'].tolist(),
        'sales': product_sales['sales'].tolist()
    }


def prepare_growth_data(df):
    """Prepare data for growth rate chart"""
    # Group by month and calculate growth rate
    df['month'] = df['date'].dt.to_period('M')
    monthly_sales = df.groupby('month')['sales'].sum().reset_index()
    monthly_sales['month'] = monthly_sales['month'].astype(str)

    # Calculate growth rate
    monthly_sales['growth_rate'] = monthly_sales['sales'].pct_change() * 100
    monthly_sales['growth_rate'] = monthly_sales['growth_rate'].fillna(0)

    return {
        'months': monthly_sales['month'].tolist(),
        'growth_rates': monthly_sales['growth_rate'].tolist()
    }


def prepare_heatmap_data(df):
    """Prepare data for heatmap chart"""
    # Create pivot table for heatmap
    heatmap_pivot = df.pivot_table(
        values='sales',
        index='region',
        columns='product',
        aggfunc='sum',
        fill_value=0
    )

    return {
        'regions': heatmap_pivot.index.tolist(),
        'products': heatmap_pivot.columns.tolist(),
        'values': heatmap_pivot.values.tolist()
    }


@app.route('/api/export')
def export_data():
    """Export filtered data as CSV"""
    region = request.args.get('region', 'all')
    product = request.args.get('product', 'all')
    date_range = request.args.get('date_range', 'all')

    df = data_gen.get_filtered_data(region, product, date_range)

    # Create export filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'sales_data_{timestamp}.csv'

    # Save to temporary file
    export_path = os.path.join('exports', filename)
    os.makedirs('exports', exist_ok=True)
    df.to_csv(export_path, index=False)

    return jsonify({
        'success': True,
        'filename': filename,
        'records': len(df),
        'message': f'Exported {len(df)} records to {filename}'
    })


@app.route('/api/realtime')
def get_realtime_data():
    """Simulate real-time data updates"""
    # Add new random records
    new_records = []
    for _ in range(np.random.randint(1, 6)):
        new_record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'region': np.random.choice(data_gen.regions),
            'product': np.random.choice(data_gen.products),
            'sales': round(np.random.uniform(50, 1000), 2),
            'orders': np.random.randint(1, 6),
            'customers': np.random.randint(20, 101),
            'customer_id': f'CUST_{np.random.randint(1000, 9999)}',
            'order_id': f'ORD_{np.random.randint(10000, 99999)}'
        }
        new_records.append(new_record)

    # Add to main dataset
    new_df = pd.DataFrame(new_records)
    data_gen.data = pd.concat([data_gen.data, new_df], ignore_index=True)

    return jsonify({
        'success': True,
        'new_records': len(new_records),
        'total_records': len(data_gen.data)
    })


@app.route('/api/stats')
def get_stats():
    """Get dataset statistics"""
    df = data_gen.data

    stats = {
        'total_records': len(df),
        'date_range': {
            'start': df['date'].min(),
            'end': df['date'].max()
        },
        'regions': df['region'].value_counts().to_dict(),
        'products': df['product'].value_counts().to_dict(),
        'sales_stats': {
            'min': df['sales'].min(),
            'max': df['sales'].max(),
            'mean': df['sales'].mean(),
            'median': df['sales'].median()
        }
    }

    return jsonify(stats)


if __name__ == '__main__':
    # Create templates directory and save HTML
    os.makedirs('templates', exist_ok=True)

    # Updated HTML template with API integration
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analytics Dashboard - Flask + Pandas</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.24.1/plotly.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
        }

        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin-bottom: 10px;
        }

        .header p {
            text-align: center;
            color: #666;
            font-size: 1.1rem;
        }

        .tech-stack {
            text-align: center;
            margin-top: 15px;
            padding: 10px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 10px;
        }

        .tech-stack span {
            display: inline-block;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            margin: 3px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .controls-panel {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .controls-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            align-items: end;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
        }

        .filter-group label {
            font-weight: 600;
            margin-bottom: 8px;
            color: #555;
        }

        .filter-group select, .filter-group input {
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s ease;
            background: white;
        }

        .filter-group select:focus, .filter-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }

        .btn.secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3);
        }

        .btn.secondary:hover {
            box-shadow: 0 8px 25px rgba(245, 87, 108, 0.4);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 5px;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }

        .chart-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .chart-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
            text-align: center;
        }

        .full-width {
            grid-column: 1 / -1;
        }

        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            font-size: 1.1rem;
            color: #666;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .status-bar {
            background: rgba(255, 255, 255, 0.9);
            padding: 10px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 0.9rem;
            color: #666;
        }

        .last-updated {
            color: #667eea;
            font-weight: 600;
        }

        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }

            .controls-grid {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="header">
            <h1>📊 Sales Analytics Dashboard</h1>
            <p>Professional Data Visualization with Flask, Pandas & Plotly</p>
            <div class="tech-stack">
                <span>Flask</span>
                <span>Pandas</span>
                <span>Plotly</span>
                <span>NumPy</span>
                <span>Python</span>
                <span>REST API</span>
            </div>
        </div>

        <div class="status-bar">
            <span>Dataset: <strong id="recordCount">Loading...</strong> records</span> | 
            <span>Last Updated: <span class="last-updated" id="lastUpdated">Loading...</span></span>
        </div>

        <div class="controls-panel">
            <div class="controls-grid">
                <div class="filter-group">
                    <label for="regionFilter">Region</label>
                    <select id="regionFilter">
                        <option value="all">All Regions</option>
                        <option value="North">North</option>
                        <option value="South">South</option>
                        <option value="East">East</option>
                        <option value="West">West</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="productFilter">Product Category</label>
                    <select id="productFilter">
                        <option value="all">All Products</option>
                        <option value="Electronics">Electronics</option>
                        <option value="Clothing">Clothing</option>
                        <option value="Home & Garden">Home & Garden</option>
                        <option value="Sports">Sports</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="dateRange">Date Range</label>
                    <select id="dateRange">
                        <option value="all">All Time</option>
                        <option value="30">Last 30 Days</option>
                        <option value="90">Last 90 Days</option>
                        <option value="365">Last Year</option>
                    </select>
                </div>
                <div class="filter-group">
                    <button class="btn" onclick="applyFilters()">Apply Filters</button>
                </div>
                <div class="filter-group">
                    <button class="btn secondary" onclick="exportData()">Export CSV</button>
                </div>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="totalSales">$0</div>
                <div class="metric-label">Total Sales</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="totalOrders">0</div>
                <div class="metric-label">Total Orders</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="avgOrderValue">$0</div>
                <div class="metric-label">Avg Order Value</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="conversionRate">0%</div>
                <div class="metric-label">Conversion Rate</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">Sales Trend Analysis</div>
                <div id="salesTrendChart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Revenue by Region</div>
                <div id="regionChart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Product Performance</div>
                <div id="productChart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Monthly Growth Rate</div>
                <div id="growthChart"></div>
            </div>
            <div class="chart-container full-width">
                <div class="chart-title">Sales Performance Heatmap</div>
                <div id="heatmapChart"></div>
            </div>
        </div>
    </div>

    <script>
        let currentData = null;

        // Fetch data from Flask API
        const fetchData = async (filters = {}) => {
            try {
                const params = new URLSearchParams(filters);
                const response = await fetch(`/api/data?${params}`);
                const data = await response.json();
                currentData = data;
                return data;
            } catch (error) {
                console.error('Error fetching data:', error);
                return null;
            }
        };

        // Update metrics
        const updateMetrics = (metrics) => {
            document.getElementById('totalSales').textContent = `$${metrics.total_sales.toLocaleString()}`;
            document.getElementById('totalOrders').textContent = metrics.total_orders.toLocaleString();
            document.getElementById('avgOrderValue').textContent = `$${metrics.avg_order_value.toFixed(2)}`;
            document.getElementById('conversionRate').textContent = `${metrics.conversion_rate}%`;
        };

        // Create sales trend chart
        const createSalesTrendChart = (data) => {
            const trace = {
                x: data.dates,
                y: data.sales,
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#667eea', width: 3 },
                marker: { size: 6, color: '#764ba2' },
                fill: 'tonexty',
                fillcolor: 'rgba(102, 126, 234, 0.1)'
            };

            const layout = {
                margin: { t: 10, r: 10, b: 40, l: 60 },
                xaxis: { title: 'Date' },
                yaxis: { title: 'Sales ($)' },
                showlegend: false,
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };

            Plotly.newPlot('salesTrendChart', [trace], layout, {responsive: true});
        };

        // Create region chart
        const createRegionChart = (data) => {
            const trace = {
                labels: data.regions,
                values: data.sales,
                type: 'pie',
                hole: 0.4,
                marker: { colors: ['#667eea', '#764ba2', '#f093fb', '#f5576c'] }
            };

            const layout = {
                margin: { t: 10, r: 10, b: 10, l: 10 },
                showlegend: true,
                legend: { orientation: 'h', y: -0.1 },
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };

            Plotly.newPlot('regionChart', [trace], layout, {responsive: true});
        };

        // Create product chart
        const createProductChart = (data) => {
            const trace = {
                x: data.products,
                y: data.sales,
                type: 'bar',
                marker: {
                    color: data.sales,
                    colorscale: [[0, '#667eea'], [1, '#764ba2']]
                }
            };

            const layout = {
                margin: { t: 10, r: 10, b: 60, l: 60 },
                xaxis: { title: 'Product Category' },
                yaxis: { title: 'Sales ($)' },
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };

            Plotly.newPlot('productChart', [trace], layout, {responsive: true});
        };

        // Create growth chart
        const createGrowthChart = (data) => {
            const trace = {
                x: data.months,
                y: data.growth_rates,
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#f5576c', width: 3 },
                marker: { size: 8, color: '#f093fb' }
            };

            const layout = {
                margin: { t: 10, r: 10, b: 60, l: 60 },
                xaxis: { title: 'Month' },
                yaxis: { title: 'Growth Rate (%)' },
                showlegend: false,
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };

            Plotly.newPlot('growthChart', [trace], layout, {responsive: true});
        };

        // Create heatmap chart
        const createHeatmapChart = (data) => {
            const trace = {
                z: data.values,
                x: data.products,
                y: data.regions,
                type: 'heatmap',
                colorscale: [[0, '#667eea'], [1, '#764ba2']]
            };

            const layout = {
                margin: { t: 10, r: 10, b: 60, l: 60 },
                xaxis: { title: 'Product Category' },
                yaxis: { title: 'Region' },
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };

            Plotly.newPlot('heatmapChart', [trace], layout, {responsive: true});
        };

        // Apply filters
        const applyFilters = async () => {
            const filters = {
                region: document.getElementById('regionFilter').value,
                product: document.getElementById('productFilter').value,
                date_range: document.getElementById('dateRange').value
            };

            const data = await fetchData(filters);
            if (data) {
                updateDashboard(data);
            }
        };

        // Update dashboard
        const updateDashboard = (data) => {
            updateMetrics(data.metrics);
            createSalesTrendChart(data.charts.sales_trend);
            createRegionChart(data.charts.region_data);
            createProductChart(data.charts.product_data);
            createGrowthChart(data.charts.growth_data);
            createHeatmapChart(data.charts.heatmap_data);

            document.getElementById('lastUpdated').textContent = new Date().toLocaleString();
        };

        // Export data
        const exportData = async () => {
            const filters = {
                region: document.getElementById('regionFilter').value,
                product: document.getElementById('productFilter').value,
                date_range: document.getElementById('dateRange').value
            };

            try {
                const params = new URLSearchParams(filters);
                const response = await fetch(`/api/export?${params}`);
                const result = await response.json();

                if (result.success) {
                    alert(`✅ ${result.message}`);
                } else {
                    alert('❌ Export failed');
                }
            } catch (error) {
                console.error('Export error:', error);
                alert('❌ Export failed');
            }
        };

        // Get dataset stats
        const updateStats = async () => {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                document.getElementById('recordCount').textContent = stats.total_records.toLocaleString();
            } catch (error) {
                console.error('Stats error:', error);
            }
        };

        // Initialize dashboard
        const initDashboard = async () => {
            await updateStats();
            const data = await fetchData();
            if (data) {
                updateDashboard(data);
            }
        };

        // Auto-refresh every 30 seconds
        setInterval(async () => {
            await fetch('/api/realtime');
            await applyFilters();
        }, 30000);

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', initDashboard);
    </script>
</body>
</html>'''

    # Save HTML template
    with open('templates/dashboard.html', 'w') as f:
        f.write(html_template)

    print("🚀 Starting Flask Dashboard Server...")
    print("📊 Dashboard URL: http://localhost:5000")
    print("🔗 API Endpoints:")
    print("   - GET /api/data - Get filtered dashboard data")
    print("   - GET /api/export - Export data as CSV")
    print("   - GET /api/stats - Get dataset statistics")
    print("   - GET /api/realtime - Simulate real-time updates")
    print("\n💡 Features:")
    print("   ✅ Interactive filtering by Region, Product, Date Range")
    print("   ✅ Real-time KPI metrics")
    print("   ✅ 5 different chart types (Line, Pie, Bar, Growth, Heatmap)")
    print("   ✅ CSV export functionality")
    print("   ✅ Auto-refresh with simulated real-time data")
    print("   ✅ Professional responsive design")
    print("   ✅ RESTful API architecture")

    app.run(debug=True, host='0.0.0.0', port=5000)