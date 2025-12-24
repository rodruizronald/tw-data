"""
Issues & Alerts Page.

Displays failed and partial company runs with error details.
"""

from typing import cast

import pandas as pd
import streamlit as st

from dashboard.components.metrics_cards import render_status_badge
from dashboard.components.sidebar import render_sidebar
from services.metrics_service import job_metrics_service

# Configure page
st.set_page_config(
    page_title="Issues & Alerts - Pipeline Health Dashboard",
    page_icon="⚠️",
    layout="wide",
)

# Render sidebar
render_sidebar()

# Main content
st.title("⚠️ Issues & Alerts")

# Check if date is selected
if not st.session_state.get("selected_date"):
    st.warning("⚠️ Please select a date from the calendar in the sidebar.")
    st.stop()

selected_date = st.session_state.selected_date
st.markdown(f"### Date: {selected_date}")
st.markdown("---")

# Fetch data
with st.spinner("Loading issues and alerts..."):
    companies = job_metrics_service.get_companies_by_date(selected_date)

if not companies:
    st.error(f"❌ No company data found for {selected_date}")
    st.stop()

# Filter by status
failed_companies = [c for c in companies if c.overall_status == "failed"]
partial_companies = [c for c in companies if c.overall_status == "partial"]
success_companies = [c for c in companies if c.overall_status == "success"]

# === SUMMARY METRICS ===
st.subheader("📊 Alert Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Companies", len(companies))

with col2:
    st.metric(
        "❌ Failed",
        len(failed_companies),
        delta=f"{len(failed_companies) / len(companies) * 100:.1f}%"
        if companies
        else "0%",
        delta_color="inverse",
    )

with col3:
    st.metric(
        "⚠️ Partial Success",
        len(partial_companies),
        delta=f"{len(partial_companies) / len(companies) * 100:.1f}%"
        if companies
        else "0%",
    )

with col4:
    st.metric(
        "✅ Successful",
        len(success_companies),
        delta=f"{len(success_companies) / len(companies) * 100:.1f}%"
        if companies
        else "0%",
        delta_color="normal",
    )

st.markdown("---")

# === CRITICAL ERRORS ===
st.subheader("🔴 Critical Errors Summary")

# Collect all errors
all_errors: dict[str, dict[str, int | list[str] | list[int]]] = {}
for company in failed_companies + partial_companies:
    for stage in range(1, 6):
        error = getattr(company, f"stage_{stage}_error_message", None)
        if error and error != "None":
            if error not in all_errors:
                all_errors[error] = {
                    "count": 0,
                    "companies": [],
                    "stages": [],
                }
            all_errors[error]["count"] = cast("int", all_errors[error]["count"]) + 1
            cast("list[str]", all_errors[error]["companies"]).append(
                company.company_name
            )
            cast("list[int]", all_errors[error]["stages"]).append(stage)

if all_errors:
    # Sort by count
    sorted_errors = sorted(
        all_errors.items(), key=lambda x: cast("int", x[1]["count"]), reverse=True
    )

    st.warning(
        f"Found {len(sorted_errors)} unique error types affecting {len(failed_companies) + len(partial_companies)} companies"
    )

    # Display error summary table
    error_summary = []
    for error_msg, data in sorted_errors:
        error_summary.append(
            {
                "Error Message": error_msg[:100] + "..."
                if len(error_msg) > 100
                else error_msg,
                "Occurrences": data["count"],
                "Companies Affected": len(set(cast("list", data["companies"]))),
            }
        )

    df_errors = pd.DataFrame(error_summary)
    st.dataframe(df_errors, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Detailed error breakdown
    st.markdown("### 🔍 Detailed Error Breakdown")

    for error_msg, data in sorted_errors[:5]:  # Show top 5 errors
        with st.expander(
            f"🔴 {error_msg[:80]}... ({data['count']} occurrences)", expanded=False
        ):
            st.markdown("**Full Error Message:**")
            st.code(error_msg)

            unique_companies = list(set(cast("list", data["companies"])))
            st.markdown(f"**Affected Companies ({len(unique_companies)}):**")
            for company_name in unique_companies:
                st.write(f"- {company_name}")

            unique_stages = list(set(cast("list", data["stages"])))
            st.markdown(
                f"**Stages Affected:** {', '.join([f'Stage {s}' for s in unique_stages])}"
            )
else:
    st.success("✅ No errors found!")

st.markdown("---")

# === FAILED COMPANIES ===
st.subheader("❌ Failed Companies")

if failed_companies:
    st.error(f"Found {len(failed_companies)} completely failed companies")

    # Create table
    failed_data = []
    for company in failed_companies:
        # Collect all errors for this company
        company_errors = []
        for stage in range(1, 6):
            error = getattr(company, f"stage_{stage}_error_message", None)
            if error and error != "None":
                company_errors.append(f"S{stage}: {error[:50]}...")

        failed_data.append(
            {
                "Company": company.company_name,
                "Errors": "; ".join(company_errors)
                if company_errors
                else "No error message",
                "Updated At": company.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                if company.updated_at
                else "N/A",
            }
        )

    df_failed = pd.DataFrame(failed_data)
    st.dataframe(df_failed, use_container_width=True, hide_index=True)

    # Detailed view
    st.markdown("#### 🔍 Detailed Failed Company View")

    failed_company_names = [c.company_name for c in failed_companies]
    selected_failed = st.selectbox(
        "Select a failed company to view details:",
        options=failed_company_names,
        key="selected_failed_company",
    )

    if selected_failed:
        company = next(c for c in failed_companies if c.company_name == selected_failed)

        st.markdown(f"### {company.company_name}")
        st.markdown(render_status_badge(company.overall_status), unsafe_allow_html=True)

        # Stage status
        st.markdown("#### Stage Status")

        stage_data = []
        for stage in range(1, 6):
            status = getattr(company, f"stage_{stage}_status", "N/A")
            error = getattr(company, f"stage_{stage}_error_message", None)

            stage_data.append(
                {
                    "Stage": f"Stage {stage}",
                    "Status": status,
                    "Error": error or "None",
                }
            )

        df_stages = pd.DataFrame(stage_data)
        st.dataframe(df_stages, use_container_width=True, hide_index=True)

        # Show all errors
        st.markdown("#### 🔴 Error Details")
        for stage in range(1, 6):
            error = getattr(company, f"stage_{stage}_error_message", None)
            if error and error != "None":
                st.error(f"**Stage {stage}:** {error}")
else:
    st.success("✅ No completely failed companies!")

st.markdown("---")

# === PARTIAL SUCCESS COMPANIES ===
st.subheader("⚠️ Partial Success Companies")

if partial_companies:
    st.warning(f"Found {len(partial_companies)} companies with partial success")

    # Create table
    partial_data = []
    for company in partial_companies:
        # Count successful and failed stages
        successful_stages = 0
        failed_stages = 0

        for stage in range(1, 6):
            status = getattr(company, f"stage_{stage}_status", None)
            if status == "success":
                successful_stages += 1
            elif status == "failed":
                failed_stages += 1

        # Collect errors
        company_errors = []
        for stage in range(1, 6):
            error = getattr(company, f"stage_{stage}_error_message", None)
            if error and error != "None":
                company_errors.append(f"S{stage}: {error[:50]}...")

        partial_data.append(
            {
                "Company": company.company_name,
                "Successful Stages": successful_stages,
                "Failed Stages": failed_stages,
                "Errors": "; ".join(company_errors)
                if company_errors
                else "No error message",
                "New Jobs": company.new_jobs_found or 0,
            }
        )

    df_partial = pd.DataFrame(partial_data)
    st.dataframe(df_partial, use_container_width=True, hide_index=True)

    # Detailed view
    st.markdown("#### 🔍 Detailed Partial Success View")

    partial_company_names = [c.company_name for c in partial_companies]
    selected_partial = st.selectbox(
        "Select a partially successful company to view details:",
        options=partial_company_names,
        key="selected_partial_company",
    )

    if selected_partial:
        company = next(
            c for c in partial_companies if c.company_name == selected_partial
        )

        st.markdown(f"### {company.company_name}")
        st.markdown(render_status_badge(company.overall_status), unsafe_allow_html=True)

        # Stage status
        st.markdown("#### Stage Status")

        stage_data = []
        for stage in range(1, 6):
            status = getattr(company, f"stage_{stage}_status", "N/A")
            processed = getattr(company, f"stage_{stage}_jobs_processed", 0)
            completed = getattr(company, f"stage_{stage}_jobs_completed", 0)
            error = getattr(company, f"stage_{stage}_error_message", None)

            stage_data.append(
                {
                    "Stage": f"Stage {stage}",
                    "Status": status,
                    "Processed": processed or 0,
                    "Completed": completed or 0,
                    "Error": error or "None",
                }
            )

        df_stages = pd.DataFrame(stage_data)
        st.dataframe(df_stages, use_container_width=True, hide_index=True)

        # Show errors from failed stages
        st.markdown("#### ⚠️ Error Details")
        has_errors = False
        for stage in range(1, 6):
            error = getattr(company, f"stage_{stage}_error_message", None)
            if error and error != "None":
                has_errors = True
                st.warning(f"**Stage {stage}:** {error}")

        if not has_errors:
            st.info("No error messages recorded")
else:
    st.success("✅ No partial success companies!")

st.markdown("---")

# === RECOMMENDATIONS ===
st.subheader("💡 Recommendations")

if failed_companies or partial_companies:
    st.markdown("""
    ### Action Items:
    1. **Review Critical Errors**: Focus on the most frequent error types first
    2. **Check Failed Companies**: Investigate completely failed companies to understand systematic issues
    3. **Monitor Partial Success**: Review partial success companies to identify stage-specific problems
    4. **Update Configuration**: If errors are configuration-related, update company settings
    5. **Escalate Issues**: Report persistent errors to the development team
    """)
else:
    st.success("""
    ### ✅ All Systems Operational

    No issues or alerts detected for this date. All companies processed successfully!
    """)

st.caption("⚠️ Pipeline Health Dashboard - Issues & Alerts")
