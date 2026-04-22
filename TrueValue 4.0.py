import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Quant Pro Valuation", layout="wide")

# App Header with "About" section
st.title("📊 Advanced Quantitative Valuation Dashboard")
with st.expander("ℹ️ How to use this model (Economic Theory)"):
    st.write("""
    This tool uses **Mean Reversion Theory** to identify stock over/undervaluation. 
    It compares the current P/E ratio against its own history to see if the market is 
    paying more or less than usual for each dollar of earnings.
    
    * **P/E Ratio:** Price divided by Earnings. A measure of 'expensiveness'.
    * **MA_200:** The 200-day Moving Average. It represents the 'Fair Value' baseline.
    * **Outliers:** Data points that represent extreme market euphoria or panic.
    """)

# Sidebar
ticker_symbol = st.sidebar.text_input("Enter Ticker", "AAPL")
lookback_years = st.sidebar.slider("Historical Lookback (Years)", 2, 10, 5)

@st.cache_data
def get_data(ticker, years):
    try:
        tk = yf.Ticker(ticker)
        # Use a longer period to ensure we get enough data for the MA_200
        hist = tk.history(period=f"{years+1}y") 
        info = tk.info
        
        if hist.empty:
            return None, None
            
        # Fallback logic: If 'trailingPE' is missing from info, calculate it manually
        eps = info.get('trailingEps')
        if not eps:
            # If EPS is missing, we can't do P/E analysis
            return None, None
            
        hist['Proxy_PE'] = hist['Close'] / eps
        return hist, info
    except Exception as e:
        print(f"Error: {e}")
        return None, None

data, info = get_data(ticker_symbol, lookback_years)

if data is not None:
    current_pe = info.get('trailingPE', data['Proxy_PE'].iloc[-1])
    hist_pe = data['Proxy_PE'].dropna()
    
    # --- METRICS SECTION ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Current P/E", f"{current_pe:.2f}", help="Price per dollar of earnings.")
    c2.metric("52-Week High P/E", f"{hist_pe.tail(252).max():.2f}")
    c3.metric("Historical Median", f"{hist_pe.median():.2f}", help="The middle value of the historical range.")

    # --- GRAPH 1: TREND ---
    st.subheader("1. Valuation Trend & Mean Reversion")
    data['MA_200'] = data['Proxy_PE'].rolling(window=200).mean()
    
    fig1 = px.line(data, y=['Proxy_PE', 'MA_200'], 
                  title="P/E Ratio vs. 200-Day Moving Average",
                  color_discrete_map={"Proxy_PE": "#636EFA", "MA_200": "#EF553B"})
    st.plotly_chart(fig1, use_container_width=True)
    st.info("**What is MA_200?** This red line is the average P/E of the last 200 days. If the Blue line is far above the Red line, the stock is 'historically expensive'.")

    # --- GRAPH 2 & 3: DISTRIBUTION & OUTLIERS ---
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("2. Distribution Density")
        fig2 = px.histogram(data, x="Proxy_PE", nbins=50, marginal="rug",
                           title="Historical P/E Frequency")
        fig2.add_vline(x=current_pe, line_color="red", line_dash="dash")
        st.plotly_chart(fig2, use_container_width=True)
        st.write("**Rug Plot (Ticks at top):** Each tick is one day. Dense areas show the 'normal' price zone.")
        
    with col_right:
        st.subheader("3. Statistical Outliers")
        fig3 = px.box(data, y="Proxy_PE", points="all", title="Statistical Range")
        st.plotly_chart(fig3, use_container_width=True)
        st.write("**Dots outside the box:** These represent extreme market events (bubbles or crashes) where the price was an outlier.")

    # --- FINAL SIGNAL ---
    st.divider()
    percentile = (hist_pe < current_pe).mean() * 100
    st.subheader(f"Final Quant Signal: {percentile:.1f}% Percentile")
    if percentile > 90:
        st.error("🚨 OVERVALUED: This stock is currently more expensive than 90% of its history.")
    elif percentile < 10:
        st.success("💰 UNDERVALUED: This stock is currently cheaper than 90% of its history.")
    else:
        st.warning("⚖️ NEUTRAL: The stock is trading within its normal historical range.")

else:
    st.error("Ticker not found. Please try a standard symbol like MSFT or GOOGL.")
