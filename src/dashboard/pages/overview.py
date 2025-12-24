"""
Overview Dashboard Page.

Displays pipeline-wide metrics and stage performance for selected date.
"""

import pandas as pd
import streamlit as st

from dashboard.components.metrics_cards import render_metric_cards_row
from dashboard.components.sidebar import render_sidebar
from services.metrics_service import job_metrics_service

# Configure page
st.set_page_config(
    page_title="Overview - Pipeline Health Dashboard",
    page_icon="📊",
    layout="wide",
)

# Render sidebar
render_sidebar()

# Main content
st.title("📊 Pipeline Overview")

# Check if date is selected
if not st.session_state.get("selected_date"):
    st.warning("⚠️ Please select a date from the calendar in the sidebar.")
    st.stop()

selected_date = st.session_state.selected_date
st.markdown(f"### Date: {selected_date}")
st.markdown("---")

# Fetch data
with st.spinner("Loading pipeline metrics..."):
    aggregate = job_metrics_service.get_pipeline_health_metrics(selected_date)

if not aggregate:
    st.error(f"❌ No data found for {selected_date}")
    st.stop()

# === METRICS CARDS ===
st.subheader("📈 Key Metrics")

metrics = [
    {
        "label": "Companies Processed",
        "value": aggregate.total_companies_processed,
        "icon": "🏢",
    },
    {
        "label": "Overall Success Rate",
        "value": f"{aggregate.overall_success_rate:.1f}%",
        "icon": "✅",
    },
    {
        "label": "New Jobs Found",
        "value": aggregate.total_new_jobs,
        "icon": "🆕",
    },
    {
        "label": "Net Job Change",
        "value": f"{aggregate.net_job_change:+d}"
        if aggregate.net_job_change != 0
        else "0",
        "delta_color": "normal" if aggregate.net_job_change >= 0 else "inverse",
        "icon": "📊",
    },
    {
        "label": "Total Active Jobs",
        "value": f"{aggregate.total_active_jobs:,}",
        "icon": "💼",
    },
]

render_metric_cards_row(metrics)

st.markdown("---")

# === COMPANY STATUS BREAKDOWN ===
st.subheader("🏢 Company Status Breakdown")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="✅ Successful",
        value=aggregate.companies_successful,
    )

with col2:
    st.metric(
        label="⚠️ Partial Success",
        value=aggregate.companies_partial,
    )

with col3:
    st.metric(
        label="❌ Failed",
        value=aggregate.companies_with_failures,
    )

st.markdown("---")

# === STAGE PERFORMANCE ===
st.subheader("🔄 Stage Performance")

# Create stage performance data
stage_data = []
for stage in range(1, 6):
    stage_data.append(
        {
            "Stage": f"Stage {stage}",
            "Processed": getattr(aggregate, f"stage_{stage}_total_processed"),
            "Success Rate": f"{getattr(aggregate, f'stage_{stage}_success_rate'):.1f}%",
            "Avg Time (s)": f"{getattr(aggregate, f'stage_{stage}_avg_execution_seconds'):.2f}",
        }
    )

# Display as table
df = pd.DataFrame(stage_data)
st.dataframe(df, use_container_width=True, hide_index=True)

# === STAGE PERFORMANCE BARS ===
st.markdown("#### Success Rate by Stage")

stage_cols = st.columns(5)
for i, stage in enumerate(range(1, 6)):
    with stage_cols[i]:
        success_rate = getattr(aggregate, f"stage_{stage}_success_rate")
        processed = getattr(aggregate, f"stage_{stage}_total_processed")

        # Determine color
        if success_rate >= 95:
            color = "🟢"
        elif success_rate >= 70:
            color = "🟡"
        else:
            color = "🔴"

        st.metric(
            label=f"Stage {stage}",
            value=f"{success_rate:.1f}%",
        )
        st.caption(f"{color} {processed} processed")
        st.progress(success_rate / 100)

st.markdown("---")

# === DATA GROWTH METRICS ===
st.subheader("📊 Data Growth Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="New Jobs",
        value=aggregate.total_new_jobs,
    )

with col2:
    st.metric(
        label="Jobs Deactivated",
        value=aggregate.total_jobs_deactivated,
    )

with col3:
    st.metric(
        label="Active Jobs",
        value=f"{aggregate.total_active_jobs:,}",
    )

with col4:
    st.metric(
        label="Inactive Jobs",
        value=f"{aggregate.total_inactive_jobs:,}",
    )

st.markdown("---")

# === METADATA ===
with st.expander("Metadata"):
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Pipeline Runs:** {aggregate.pipeline_run_count}")
        st.write(
            f"**Calculation Time:** {aggregate.calculation_timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    with col2:
        st.write(
            f"**Created At:** {aggregate.created_at_local.strftime('%Y-%m-%d %H:%M:%S')}"
        )

st.caption("📊 Pipeline Health Dashboard - Overview")
