# %%
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
from streamlit_plotly_events import plotly_events  # For click events

px.defaults.template = "plotly_white"

# Initialize connection
@st.cache_resource
def init_connection():
    conn_str = "postgresql+psycopg2://postgres:Badre2152%40@127.0.0.1:5432/new_test1"
    return create_engine(conn_str)

engine = init_connection()

# %%
@st.cache_data
def get_data():
    query = """
    SELECT 
        o.order_date,
        od.sales,
        od.profit,
        g.region,
        p.category,
        o.customer_id,
        od.product_id,
        p.product_name,
        c.customer_name
    FROM orders o
    JOIN order_details od ON o.order_id = od.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN geography g ON c.postal_code = g.postal_code
    JOIN products p ON od.product_id = p.product_id
    """
    df = pd.read_sql(query, engine)
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['month_year'] = df['order_date'].dt.to_period('M').astype(str)
    df['profit_margin'] = df.apply(lambda row: (row['profit']/row['sales']*100) if row['sales'] else 0, axis=1)
    return df

df = get_data()

# %%
st.sidebar.header(" Filter control panel")
region_filter = st.sidebar.multiselect(
    "Area",
    options=df["region"].unique(),
    default=df["region"].unique()
)
category_filter = st.sidebar.multiselect(
    "Category",
    options=df["category"].unique(),
    default=df["category"].unique()
)

df_filtered = df[
    (df["region"].isin(region_filter)) &
    (df["category"].isin(category_filter))
]

# %%
st.title("📊 Superstore Analytics Dashboard")
st.markdown("Interactive analysis of sales, profit, and customer performance")

with st.expander("📘 Dashboard Instructions"):
    st.markdown("""
- Use sidebar filters to select **regions** and **categories**.
- KPIs summarize overall **sales performance**.
- Click on Pie chart slices to filter all charts by category.
- Charts display **trends and comparisons**.
- The heatmap shows **correlations between metrics**.
- All visualizations update automatically when filters change.
""")

st.markdown("---")

# KPI Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Sales", f"${df_filtered['sales'].sum():,.0f}")
col2.metric("📈 Total Profit", f"${df_filtered['profit'].sum():,.0f}")
sales_sum = df_filtered['sales'].sum()
weighted_profit_margin = (df_filtered['profit'].sum() / sales_sum * 100) if sales_sum else 0
col3.metric("📊 Profit Margin", f"{weighted_profit_margin:.1f}%")
col4.metric("🧾 Orders Count", len(df_filtered))

st.markdown("---")

# Descriptive Statistics
st.subheader("📈 Descriptive Statistics")
stats = df_filtered[['sales','profit','profit_margin']].describe()
st.dataframe(stats)

st.markdown("---")

# Sales Distribution Pie Chart (Click to filter)
st.subheader("🥧 Sales Distribution by Category (Click to filter)")
category_sales = df_filtered.groupby('category')['sales'].sum().reset_index()
fig_pie = px.pie(
    category_sales,
    values='sales',
    names='category',
    title='Sales Distribution by Category',
    hover_data={'sales':':,.0f'}
)
fig_pie.update_traces(textposition='inside', textinfo='percent+label')

selected_points = plotly_events(fig_pie, click_event=True)
selected_categories = [p['label'] for p in selected_points]

# Apply click filter
if selected_categories:
    df_click_filtered = df_filtered[df_filtered['category'].isin(selected_categories)]
else:
    df_click_filtered = df_filtered

st.plotly_chart(fig_pie, use_container_width=True)
st.markdown("---")

# Sales Trend + 3-Month Moving Average
sales_trend = df_click_filtered.groupby('month_year')['sales'].sum().reset_index()
sales_trend['sales_MA3'] = sales_trend['sales'].rolling(window=3, min_periods=1).mean()

fig_line = go.Figure()
fig_line.add_trace(
    go.Scatter(
        x=sales_trend['month_year'],
        y=sales_trend['sales'],
        mode='lines+markers',
        name='Actual Sales',
        line=dict(color='blue'),
        hovertemplate='Month: %{x}<br>Sales: $%{y:,.0f}<extra></extra>'
    )
)
fig_line.add_trace(
    go.Scatter(
        x=sales_trend['month_year'],
        y=sales_trend['sales_MA3'],
        mode='lines+markers',
        name='3-Month MA',
        line=dict(color='red', dash='dash'),
        hovertemplate='Month: %{x}<br>3-Month MA: $%{y:,.0f}<extra></extra>'
    )
)
fig_line.update_layout(
    title='📈 Sales Trend Over Time (with 3-Month Moving Average)',
    xaxis_title='Month',
    yaxis_title='Sales ($)',
    title_x=0.5
)

# Sales by Category Bar Chart
fig_bar = px.bar(
    df_click_filtered.groupby('category')['sales'].sum().reset_index(),
    x='category',
    y='sales',
    color='category',
    text_auto=True,
    title="🛍 Sales by Category",
    hover_data={'sales':':,.0f'}
)
fig_bar.update_layout(title_x=0.5)

# Display Line chart and Bar chart side by side
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_line, use_container_width=True)
with col2:
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# Sales vs Profit Chart
if df_click_filtered.empty:
    st.warning("⚠️ No data available for Sales vs Profit chart.")
else:
    sales_profit_melted = df_click_filtered.groupby('category')[['sales','profit']].sum().reset_index().melt(
        id_vars='category', value_vars=['sales','profit'], var_name='Metric', value_name='Amount'
    )
    fig_comb = px.bar(
        sales_profit_melted,
        x='category',
        y='Amount',
        color='Metric',
        barmode='group',
        text_auto=True,
        title="Sales vs Profit by Category",
        hover_data={'Amount':':,.0f'}
    )
    st.plotly_chart(fig_comb, use_container_width=True)

st.markdown("---")

# Top 10 Products
top_products = df_click_filtered.groupby('product_name')['sales'].sum().sort_values(ascending=False).head(10)
fig_top_products = px.bar(
    top_products.reset_index(),
    x='product_name',
    y='sales',
    text_auto=True,
    title="🏆 Top 10 Products by Sales",
    hover_data={'sales':':,.0f'}
)
st.plotly_chart(fig_top_products, use_container_width=True)

# Top 10 Clients
top_clients = df_click_filtered.groupby('customer_name')['sales'].sum().sort_values(ascending=False).head(10)
fig_top_clients = px.bar(
    top_clients.reset_index(),
    x='customer_name',
    y='sales',
    text_auto=True,
    title="🏆 Top 10 Clients by Sales",
    hover_data={'sales':':,.0f'}
)
st.plotly_chart(fig_top_clients, use_container_width=True)

st.markdown("---")

# Correlation Heatmap
st.subheader("🔍 Correlation Heatmap")
numeric_cols = df_click_filtered.select_dtypes(include='number').columns.tolist()
corr = df_click_filtered[numeric_cols].corr()
plt.figure(figsize=(7,5))
sns.heatmap(corr, annot=True, cmap='coolwarm', linewidths=0.5, center=0)
st.pyplot(plt)