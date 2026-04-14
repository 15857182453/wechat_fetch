# 修复Pandas列重命名错误
# 原始错误代码：
# growth_df = top5_growth.reset_index()
# growth_df.columns = ['药品名称', f'{month1}销量', f'{month2}销量', '增长率 (%)']

# 修复后的代码：
if len(top5_growth) > 0:
    growth_df = top5_growth.reset_index()
    
    # 获取实际的列数并动态适配列名
    actual_col_count = len(growth_df.columns)
    target_columns = ['药品名称', f'{month1}销量', f'{month2}销量', '增长率 (%)']
    
    # 确保列名数量与实际列数一致
    if actual_col_count <= len(target_columns):
        # 实际列数小于等于期望列数时，截取相应数量的列名
        growth_df.columns = target_columns[:actual_col_count]
    else:
        # 实际列数多余期望时，为多余列命名
        growth_df.columns = target_columns + [f'Extra_Col_{i}' for i in range(actual_col_count - len(target_columns))]
else:
    # 如果top5_growth为空，则创建空DataFrame但有正确的列名
    growth_df = pd.DataFrame(columns=['药品名称', f'{month1}销量', f'{month2}销量', '增长率 (%)'])

# 或者更简洁的修复：
growth_df = top5_growth.reset_index()
n_actual_cols = len(growth_df.columns)
expected_cols = ['药品名称', f'{month1}销量', f'{month2}销量', '增长率 (%)']
growth_df.columns = expected_cols[:n_actual_cols] if n_actual_cols <= len(expected_cols) else \
                    expected_cols + [f'Col_{i}' for i in range(n_actual_cols-len(expected_cols))]