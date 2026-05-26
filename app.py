from universe import build_universe


if st.button("🚀 產生 Top 10 訊號"):

    # 🧠 動態流動性股票池（已經是300檔）
    stocks = build_universe()

    st.write(f"📦 動態股票池數量：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        df = get_data(s)

        if df is None:
            continue

        s_score = score(df)

        if s_score is None:
            continue

        results.append({
            "股票": s,
            "Score": s_score
        })

        progress.progress((i + 1) / len(stocks))

    df = pd.DataFrame(results)

    df = df.sort_values("Score", ascending=False)

    top10 = df.head(10)

    st.dataframe(top10)
