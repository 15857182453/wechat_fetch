# ========== TAB 11: 用户行为分析 ==========
with tab11:
    st.markdown('<div class="card fade-in"><h3>📊 用户行为分析 · 医院运营月报</h3></div>', unsafe_allow_html=True)

    import json
    from pathlib import Path as Path2

    DATA_DIR = Path2(__file__).parent

    @st.cache_data(ttl=3600)
    def load_fenxiti_data():
        data = {}
        for name, fname in [
            ('monthly_4', 'data_fenxiti_monthly_4.json'),
            ('monthly_5', 'data_fenxiti_monthly_5.json'),
            ('rx_4', 'data_fenxiti_rx_4.json'),
            ('rx_5', 'data_fenxiti_rx_5.json'),
        ]:
            fpath = DATA_DIR / fname
            if fpath.exists():
                with open(fpath, 'r') as f:
                    data[name] = json.load(f)
        return data

    try:
        fx_data = load_fenxiti_data()
        if not all(k in fx_data for k in ['monthly_4', 'monthly_5', 'rx_4', 'rx_5']):
            st.warning("⚠️ 数据未加载，请检查数据文件")
        else:
            d4 = fx_data['monthly_4']
            d5 = fx_data['monthly_5']

            hospitals_4 = {r[1]: r for r in d4['resultRows']}
            hospitals_5 = {r[1]: r for r in d5['resultRows']}
            all_hospitals = sorted(set(hospitals_4.keys()) | set(hospitals_5.keys()))

            # 医院选择器
            st.markdown('<div style="text-align:center;font-size:15px;color:#94A3B8;margin-bottom:8px;">选择一家医院，查看该院专属运营数据报告（仅显示该院数据，无其他医院信息）</div>', unsafe_allow_html=True)
            selected_hospital = st.selectbox(
                "🏥 选择医院",
                ["— 请选择医院 —"] + all_hospitals,
                index=0
            )

            if selected_hospital == "— 请选择医院 —":
                st.info("👆 请先选择一家医院，查看该院的专属运营数据报告")
                st.markdown(
                    '<div style="text-align:center;padding:50px 20px;color:#94A3B8;">'
                    '<p style="font-size:64px;margin:0;">🏥</p>'
                    '<p style="font-size:16px;margin-top:16px;">选择医院后，将显示该院的：</p>'
                    '<p style="margin:4px 0;">• 4月 vs 5月核心指标对比</p>'
                    '<p style="margin:4px 0;">• 用户转化漏斗</p>'
                    '<p style="margin:4px 0;">• 复购率趋势分析</p>'
                    '<p style="margin:4px 0;">• 药方维度详细数据</p>'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                r4 = hospitals_4.get(selected_hospital)
                r5 = hospitals_5.get(selected_hospital)

                st.markdown(
                    f'<div style="text-align:center;font-size:22px;font-weight:bold;padding:16px;background:linear-gradient(90deg,#0EA5E9,#3B82F6);color:white;border-radius:10px;margin-bottom:16px;">'
                    f'📋 {selected_hospital} · 运营数据报告</div>',
                    unsafe_allow_html=True
                )

                if r5:
                    g5 = float(r5[2]); v5 = int(r5[3]); pv5 = int(r5[4]); q5 = int(r5[5])
                    o5 = int(r5[6]); p5_cnt = int(r5[7]); avg5 = float(r5[8])
                    order5 = int(r5[9]); conv5 = float(r5[10]) if r5[10] else 0
                    r60_5 = float(r5[11]) if r5[11] and str(r5[11]) != 'nan' else 0
                    r30_5 = float(r5[12]) if r5[12] and str(r5[12]) != 'nan' else 0
                    r14_5 = float(r5[13]) if r5[13] and str(r5[13]) != 'nan' else 0
                else:
                    st.warning(f"⚠️ 暂无 {selected_hospital} 的5月数据")
                    st.stop()

                if r4:
                    g4 = float(r4[2]); v4 = int(r4[3]); pv4 = int(r4[4]); q4 = int(r4[5])
                    o4 = int(r4[6]); p4_cnt = int(r4[7]); avg4 = float(r4[8])
                    order4 = int(r4[9]); conv4 = float(r4[10]) if r4[10] else 0
                    r60_4 = float(r4[11]) if r4[11] and str(r4[11]) != 'nan' else 0
                    r30_4 = float(r4[12]) if r4[12] and str(r4[12]) != 'nan' else 0
                    r14_4 = float(r4[13]) if r4[13] and str(r4[13]) != 'nan' else 0
                else:
                    g4 = v4 = pv4 = q4 = o4 = p4_cnt = order4 = 0
                    avg4 = conv4 = r60_4 = r30_4 = r14_4 = 0

                def fmt_chg(curr, prev):
                    if prev == 0: return None
                    return f"{(curr - prev) / prev * 100:+.1f}%"

                # 核心指标
                st.subheader("📈 4月 vs 5月(1-14日) 核心指标对比")

                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.metric("💰 GMV", f"¥{g5:,.0f}", fmt_chg(g5, g4) if r4 else None)
                c2.metric("👥 访问人数", f"{v5:,}", fmt_chg(v5, v4) if r4 else None)
                c3.metric("📦 支付订单", f"{order5:,}", fmt_chg(order5, order4) if r4 else None)
                c4.metric("💲 客单价", f"¥{avg5:.2f}", fmt_chg(avg5, avg4) if r4 else None)
                c5.metric("🔄 转化率", f"{conv5*100:.1f}%", fmt_chg(conv5*100, conv4*100) if r4 else None)
                c6.metric("🔁 60天复购", f"{r60_5*100:.1f}%", fmt_chg(r60_5*100, r60_4*100) if r4 else None)

                st.info("📅 数据周期：4月(4/1~5/1) vs 5月(5/1~5/14)")
                st.divider()

                # 转化漏斗
                st.subheader("🔻 用户转化漏斗 (5月)")
                funnel_labels = ['访问总人数', '药方详情页浏览', '问卷提交成功', '订单创建', '订单支付成功']
                funnel_vals = [v5, pv5, q5, o5, p5_cnt]
                fig_funnel = go.Figure(go.Funnel(
                    y=funnel_labels, x=funnel_vals,
                    textposition="inside",
                    textinfo="value+percent initial+percent previous",
                    marker=dict(color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A"]),
                ))
                fig_funnel.update_layout(height=350, template='plotly_white')
                st.plotly_chart(fig_funnel, use_container_width=True)
                st.divider()

                # 复购率
                st.subheader("🔁 复购率分析")
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("近14天复购率", f"{r14_5*100:.1f}%")
                col_r2.metric("近30天复购率", f"{r30_5*100:.1f}%")
                col_r3.metric("近60天复购率", f"{r60_5*100:.1f}%")

                if r4:
                    fig_ret = go.Figure()
                    fig_ret.add_trace(go.Bar(
                        x=['近14天', '近30天', '近60天'],
                        y=[r14_4*100, r30_4*100, r60_4*100],
                        name='4月', marker_color='rgba(99,110,250,0.6)'
                    ))
                    fig_ret.add_trace(go.Bar(
                        x=['近14天', '近30天', '近60天'],
                        y=[r14_5*100, r30_5*100, r60_5*100],
                        name='5月', marker_color='rgba(0,204,150,0.8)'
                    ))
                    fig_ret.update_layout(
                        barmode='group', height=300, template='plotly_white',
                        yaxis=dict(title='复购率(%)', ticksuffix='%')
                    )
                    st.plotly_chart(fig_ret, use_container_width=True)
                st.divider()

                # 药方维度
                st.subheader("💊 药方维度数据 (5月)")
                rx5 = fx_data['rx_5']
                rx5_rows = [{
                    '药方名称': r[1],
                    '是否需问卷': r[5],
                    '详情页浏览': int(r[6]) if r[6] else 0,
                    '加购人数': int(r[7]) if r[7] else 0,
                    '订单提交': int(r[8]) if r[8] else 0,
                    '支付成功': int(r[9]) if r[9] else 0,
                    '转化率': round(float(r[10]), 1) if r[10] else 0,
                    '支付金额': round(float(r[11]), 2) if r[11] else 0,
                } for r in rx5['resultRows'] if r[3] == selected_hospital]

                if rx5_rows:
                    df_rx5 = pd.DataFrame(rx5_rows).sort_values('支付金额', ascending=False)
                    st.dataframe(df_rx5, use_container_width=True, hide_index=True,
                                column_config={
                                    '支付金额': st.column_config.NumberColumn("支付金额", format="¥%.2f"),
                                    '转化率': st.column_config.NumberColumn("转化率", format="%.1f%%"),
                                })
                    rx_top = df_rx5.head(10)
                    fig_rx = px.bar(
                        rx_top, x='支付金额', y='药方名称', orientation='h',
                        title='药方 GMV TOP 10',
                        color='支付金额', color_continuous_scale='Blues'
                    )
                    fig_rx.update_layout(height=400, template='plotly_white')
                    st.plotly_chart(fig_rx, use_container_width=True)
                else:
                    st.info("💊 暂无该院的药方数据")

    except Exception as e:
        st.error(f"❌ 加载失败：{e}")
        import traceback
        st.code(traceback.format_exc())

