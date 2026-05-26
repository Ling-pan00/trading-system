import streamlit as st
from universe import build_three_tier_universe

st.set_page_config(page_title="法人三層股票池", layout="wide")

st.title("🏛️ 法人三層股票池系統")

if st.button("🚀 建立股票池"):

    tiers = build_three_tier_universe()

    st.subheader("🟢 Tier 1（核心法人）")
    st.write(tiers["Tier 1（核心法人）"])

    st.subheader("🟡 Tier 2（成長動能）")
    st.write(tiers["Tier 2（成長動能）"])

    st.subheader("🔵 Tier 3（防守穩定）")
    st.write(tiers["Tier 3（防守穩定）"])
