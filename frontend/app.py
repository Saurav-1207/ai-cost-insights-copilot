# frontend/app.py - COMPLETE FIXED STREAMLIT FRONTEND

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="AI Cost & Insights Copilot",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
    }
    
    .recommendation-card {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin-bottom: 1rem;
    }
    
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    
    .error-message {
        background: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = "http://localhost:8000"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_api_data(endpoint: str, params: dict = None):
    """Fetch data from API with caching and error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data from {endpoint}: {str(e)}")
        return None

def post_api_data(endpoint: str, data: dict):
    """Post data to API with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to post to {endpoint}: {str(e)}")
        return None

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI Cost & Insights Copilot</h1>
        <p>Enterprise-grade FinOps analytics with AI-powered natural language querying</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", [
        "📊 Executive Dashboard", 
        "💬 AI Assistant", 
        "🎯 Cost Optimization", 
        "📈 System Monitor"
    ])
    
    # Route to appropriate page
    if page == "📊 Executive Dashboard":
        show_dashboard()
    elif page == "💬 AI Assistant":
        show_ai_assistant()
    elif page == "🎯 Cost Optimization":
        show_recommendations()
    elif page == "📈 System Monitor":
        show_system_monitor()

def show_dashboard():
    """Executive dashboard with KPIs and trends"""
    st.header("📊 Executive Dashboard")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        month_filter = st.selectbox("Filter by Month", 
                                   ["All", "2024-09", "2024-08", "2024-07", "2024-06", "2024-05"])
    with col2:
        service_filter = st.selectbox("Filter by Service", 
                                     ["All", "Compute", "Storage", "Database", "AI/ML", "Networking"])
    with col3:
        min_cost_filter = st.number_input("Minimum Cost ($)", min_value=0.0, value=0.0)
    
    # Build API parameters
    params = {}
    if month_filter != "All":
        params['month'] = month_filter
    if service_filter != "All":
        params['service'] = service_filter
    if min_cost_filter > 0:
        params['min_cost'] = min_cost_filter
    
    # Fetch KPI data
    kpi_data = fetch_api_data("/api/kpi", params)
    
    if kpi_data:
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>${kpi_data['monthly_total']:,.2f}</h3>
                <p>Total Monthly Cost</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{kpi_data['resource_count']:,}</h3>
                <p>Active Resources</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{kpi_data['service_count']}</h3>
                <p>Services Used</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            avg_cost = kpi_data['monthly_total'] / max(kpi_data['resource_count'], 1)
            st.markdown(f"""
            <div class="metric-card">
                <h3>${avg_cost:,.2f}</h3>
                <p>Avg Cost per Resource</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Charts section
        st.subheader("📈 Cost Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Service breakdown pie chart
            if kpi_data['service_breakdown']:
                fig_pie = px.pie(
                    values=list(kpi_data['service_breakdown'].values()),
                    names=list(kpi_data['service_breakdown'].keys()),
                    title="Cost Distribution by Service"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Resource group bar chart
            if kpi_data['resource_group_breakdown']:
                rg_data = kpi_data['resource_group_breakdown']
                fig_bar = px.bar(
                    x=list(rg_data.values()),
                    y=list(rg_data.keys()),
                    orientation='h',
                    title="Top Resource Groups by Cost"
                )
                fig_bar.update_layout(height=400)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Trend analysis
        if kpi_data['trend_data']:
            st.subheader("📊 Monthly Trend Analysis")
            
            trend_df = pd.DataFrame(kpi_data['trend_data'])
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=trend_df['month_name'],
                y=trend_df['total_cost'],
                mode='lines+markers',
                name='Monthly Cost',
                line=dict(width=3),
                marker=dict(size=8)
            ))
            
            fig_trend.update_layout(
                title="Monthly Cost Trends",
                xaxis_title="Month",
                yaxis_title="Cost ($)",
                height=400
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
        
        # Top resources table
        if kpi_data['top_resources']:
            st.subheader("💰 Top Cost Drivers")
            
            resources_df = pd.DataFrame(kpi_data['top_resources'])
            resources_df['total_cost'] = resources_df['total_cost'].apply(lambda x: f"${x:,.2f}")
            resources_df['avg_usage'] = resources_df['avg_usage'].apply(lambda x: f"{x:.2f}")
            
            st.dataframe(
                resources_df[['resource_name', 'service', 'resource_group', 'total_cost', 'avg_usage']],
                use_container_width=True
            )

def show_ai_assistant():
    """AI-powered chat interface"""
    st.header("💬 AI Assistant")
    st.write("Ask questions about your cloud costs in natural language!")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "metadata" in message:
                # Show additional metadata
                metadata = message["metadata"]
                with st.expander("📊 Response Details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Confidence:** {metadata.get('confidence', 0)*100:.1f}%")
                        st.write(f"**Processing Time:** {metadata.get('processing_time', 0):.2f}s")
                    with col2:
                        st.write(f"**Data Available:** {'Yes' if metadata.get('data_available') else 'No'}")
                        st.write(f"**Classification:** {metadata.get('query_classification', 'Unknown')}")
                    
                    # Show token usage if available
                    if 'token_usage' in metadata:
                        tokens = metadata['token_usage']
                        st.write("**Token Usage:**")
                        st.write(f"- Input: {tokens.get('input_tokens', 0):,} tokens")
                        st.write(f"- Output: {tokens.get('output_tokens', 0):,} tokens")
                        st.write(f"- Total: {tokens.get('total_tokens', 0):,} tokens")
                        st.write(f"- Estimated Cost: ${tokens.get('estimated_cost', 0):.4f}")
                    
                    # Show recommendations if available
                    if message.get("recommendations"):
                        st.write("**💡 Recommendations:**")
                        for i, rec in enumerate(message["recommendations"][:3], 1):
                            st.write(f"{i}. {rec}")
    
    # Chat input
    if prompt := st.chat_input("Ask about your cloud costs..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your question..."):
                response_data = post_api_data("/api/ask", {"question": prompt})
                
                if response_data:
                    answer = response_data.get("answer", "No response received")
                    st.markdown(answer)
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "recommendations": response_data.get("recommendations", []),
                        "metadata": {
                            "confidence": response_data.get("confidence", 0),
                            "processing_time": response_data.get("processing_time", 0),
                            "data_available": response_data.get("data_available", False),
                            "query_classification": response_data.get("query_classification", "unknown"),
                            "token_usage": response_data.get("token_usage", {})
                        }
                    })
                else:
                    error_msg = "I apologize, but I'm having trouble processing your request. Please try again."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Sample questions
    st.subheader("💡 Sample Questions")
    sample_questions = [
        "What was total spend in September? Break it down by service and resource group.",
        "Why did spend increase vs August? Show top 5 contributors.",
        "Which resources look idle, and how much could we save if we right-size?",
        "List items with missing owner tag.",
        "Explain token usage and how you prevent prompt injection."
    ]
    
    for question in sample_questions:
        if st.button(question, key=f"sample_{hash(question)}"):
            # Trigger the question
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()

def show_recommendations():
    """Cost optimization recommendations"""
    st.header("🎯 Cost Optimization Recommendations")
    
    # Fetch recommendations
    with st.spinner("Analyzing your cloud costs for optimization opportunities..."):
        recommendations_data = fetch_api_data("/api/recommendations")
    
    if recommendations_data:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        summary = recommendations_data.get('summary', {})
        
        with col1:
            st.metric("Total Recommendations", summary.get('total_recommendations', 0))
        
        with col2:
            savings = recommendations_data.get('total_potential_savings', 0)
            st.metric("Potential Savings", f"${savings:,.2f}")
        
        with col3:
            priority = recommendations_data.get('priority_breakdown', {})
            st.metric("High Priority", priority.get('high', 0))
        
        with col4:
            analysis_period = recommendations_data.get('analysis_period', 'N/A')
            st.metric("Analysis Month", analysis_period)
        
        # Priority breakdown chart
        if priority:
            fig_priority = px.pie(
                values=list(priority.values()),
                names=list(priority.keys()),
                title="Recommendations by Priority"
            )
            st.plotly_chart(fig_priority, use_container_width=True)
        
        # Detailed recommendations
        st.subheader("📋 Detailed Recommendations")
        
        recommendations = recommendations_data.get('recommendations', [])
        
        if recommendations:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                priority_filter = st.selectbox("Filter by Priority", ["All", "high", "medium", "low"])
            with col2:
                type_filter = st.selectbox("Filter by Type", ["All", "idle_resource", "tagging_gap", "high_cost_review"])
            
            # Apply filters
            filtered_recs = recommendations
            if priority_filter != "All":
                filtered_recs = [r for r in filtered_recs if r.get('priority') == priority_filter]
            if type_filter != "All":
                filtered_recs = [r for r in filtered_recs if r.get('type') == type_filter]
            
            # Display recommendations
            for i, rec in enumerate(filtered_recs[:20]):  # Show top 20
                priority_color = {"high": "#dc3545", "medium": "#ffc107", "low": "#28a745"}.get(rec.get('priority', 'low'), "#6c757d")
                
                with st.expander(f"{rec.get('priority', 'Unknown').upper()} - {rec.get('resource_name', 'Unknown Resource')} (${rec.get('estimated_savings', 0):,.2f} savings)"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Resource ID:** {rec.get('resource_id', 'N/A')}")
                        st.write(f"**Service:** {rec.get('service', 'N/A')}")
                        st.write(f"**Resource Group:** {rec.get('resource_group', 'N/A')}")
                        st.write(f"**Current Cost:** ${rec.get('current_cost', 0):,.2f}/month")
                    
                    with col2:
                        st.write(f"**Estimated Savings:** ${rec.get('estimated_savings', 0):,.2f}/month")
                        st.write(f"**Annual Impact:** ${rec.get('estimated_savings', 0)*12:,.2f}/year")
                        st.write(f"**Confidence:** {rec.get('confidence', 0)*100:.1f}%")
                        st.write(f"**Priority:** {rec.get('priority', 'Unknown').title()}")
                    
                    st.write(f"**Description:** {rec.get('description', 'No description available')}")
                    st.write(f"**Recommendation:** {rec.get('recommendation', 'No recommendation available')}")
                    
                    # Additional details based on type
                    if rec.get('type') == 'idle_resource':
                        st.write(f"**Utilization Rate:** {rec.get('utilization_rate', 0)}%")
                        st.write(f"**Usage Range:** {rec.get('usage_range', 'N/A')}")
                    elif rec.get('type') == 'tagging_gap':
                        st.write(f"**Missing Tag:** {rec.get('missing_tag_type', 'Unknown').replace('_', ' ').title()}")
                        st.write(f"**Governance Impact:** {rec.get('governance_impact', 'N/A')}")
        else:
            st.info("No recommendations available at this time.")
    else:
        st.error("Failed to load recommendations. Please check the API connection.")

def show_system_monitor():
    """System monitoring and metrics"""
    st.header("📈 System Monitor")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh (every 30 seconds)")
    
    if auto_refresh:
        # Auto-refresh every 30 seconds
        time.sleep(1)  # Small delay for better UX
        st.rerun()
    
    # Manual refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Health check
    health_data = fetch_api_data("/health")
    if health_data:
        status = health_data.get('status', 'unknown')
        status_color = {"healthy": "🟢", "degraded": "🟡", "critical": "🔴"}.get(status, "⚪")
        
        st.subheader(f"{status_color} System Health: {status.title()}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Service Version", health_data.get('version', 'Unknown'))
        with col2:
            uptime = health_data.get('uptime_seconds', 0)
            st.metric("Uptime", f"{uptime/3600:.1f} hours")
        with col3:
            st.metric("Database Status", health_data.get('database_status', 'Unknown'))
        with col4:
            st.metric("AI Service", health_data.get('ai_service_status', 'Unknown'))
    
    # Metrics
    metrics_data = fetch_api_data("/api/metrics")
    if metrics_data:
        st.subheader("📊 Performance Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Requests", f"{metrics_data.get('total_requests', 0):,}")
        with col2:
            st.metric("AI Queries", f"{metrics_data.get('ai_queries', 0):,}")
        with col3:
            st.metric("Error Rate", f"{metrics_data.get('error_rate', 0):.2f}%")
        with col4:
            st.metric("Avg Response Time", f"{metrics_data.get('avg_response_time', 0):.1f}ms")
        
        # Token usage metrics
        token_usage = metrics_data.get('token_usage', {})
        if token_usage:
            st.subheader("🤖 AI Token Usage & Security")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Tokens Used", f"{token_usage.get('total_tokens_used', 0):,}")
            with col2:
                st.metric("Input Tokens", f"{token_usage.get('input_tokens', 0):,}")
            with col3:
                st.metric("Output Tokens", f"{token_usage.get('output_tokens', 0):,}")
            with col4:
                st.metric("Estimated Cost", f"${token_usage.get('estimated_cost', 0):.4f}")
        
        # Security metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Security Blocks", metrics_data.get('security_blocks', 0))
        with col2:
            st.metric("Validation Failures", metrics_data.get('validation_failures', 0))
        with col3:
            st.metric("Gemini API Calls", metrics_data.get('gemini_api_calls', 0))
        
        # Response time chart
        response_times = metrics_data.get('recent_response_times', [])
        if response_times:
            st.subheader("⏱️ Response Time Trends")
            
            fig_response = go.Figure()
            fig_response.add_trace(go.Scatter(
                y=response_times,
                mode='lines+markers',
                name='Response Time (ms)',
                line=dict(width=2),
                marker=dict(size=4)
            ))
            
            fig_response.update_layout(
                title="Recent Response Times",
                xaxis_title="Request Number",
                yaxis_title="Response Time (ms)",
                height=400
            )
            
            st.plotly_chart(fig_response, use_container_width=True)
        
        # Requests per hour
        requests_per_hour = metrics_data.get('requests_per_hour', {})
        if requests_per_hour:
            st.subheader("📈 Request Volume by Hour")
            
            hours = list(requests_per_hour.keys())
            counts = list(requests_per_hour.values())
            
            fig_requests = px.bar(
                x=hours,
                y=counts,
                title="Requests per Hour"
            )
            fig_requests.update_xaxes(tickangle=45)
            st.plotly_chart(fig_requests, use_container_width=True)
        
        # Error breakdown
        error_breakdown = metrics_data.get('error_breakdown', {})
        if error_breakdown:
            st.subheader("⚠️ Error Analysis")
            
            fig_errors = px.pie(
                values=list(error_breakdown.values()),
                names=list(error_breakdown.keys()),
                title="Error Types Distribution"
            )
            st.plotly_chart(fig_errors, use_container_width=True)
    
    # Analytics data
    analytics_data = fetch_api_data("/api/analytics")
    if analytics_data:
        st.subheader("📊 Usage Analytics")
        
        # Popular queries
        popular_queries = analytics_data.get('popular_queries', [])
        if popular_queries:
            st.write("**Most Popular Questions:**")
            for i, query in enumerate(popular_queries[:5], 1):
                st.write(f"{i}. {query['query']} ({query['count']} times)")
        
        # System insights
        insights = analytics_data.get('system_insights', {})
        if insights:
            st.write("**System Insights:**")
            for suggestion in insights.get('optimization_suggestions', []):
                st.write(f"• {suggestion}")

if __name__ == "__main__":
    main()