import pandas as pd
import matplotlib.pyplot as plt
import os

# ==========================================
# 配置
# ==========================================
INPUT_DIR = 'suppl_data'
OUTPUT_DIR = 'visualization_suppl'

# 设置表格字体稍大一点，保证清晰度
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 7 

def calculate_column_widths(df, max_width_ratio=0.8):
    """
    根据每列内容的最大长度计算列宽。
    """
    # 初始化一个列表来存储每列的最大长度
    max_lengths = []
    
    # 1. 计算表头长度
    for col in df.columns:
        max_lengths.append(len(str(col)))
    
    # 2. 计算数据内容长度
    # 注意：这里只遍历前100行以加快计算速度，避免全表扫描耗时过长
    # 如果数据量不大，可以去掉 .head(100)
    sample_df = df.head(100) 
    for i in range(len(sample_df)):
        for j, col in enumerate(df.columns):
            val = str(sample_df.iloc[i][col])
            # 如果文本被截断了（如上一步逻辑中的...），这里计算的是截断后的长度
            # 如果需要更精确，可以去掉截断逻辑，或者在此处还原原始数据
            current_len = len(val)
            if current_len > max_lengths[j]:
                max_lengths[j] = current_len
    
    # 3. 转换为相对宽度比例
    total_length = sum(max_lengths)
    if total_length == 0:
        return [1.0 / len(df.columns)] * len(df.columns)
        
    # 计算每列的比例
    widths = [l / total_length for l in max_lengths]
    
    # 4. 微调：防止某一列过宽或过窄
    # 设置最小宽度为 5% (0.05)，防止内容极少的列消失
    # 设置最大宽度为 max_width_ratio (默认 0.8)，防止某一列占据整个表格
    final_widths = []
    for w in widths:
        w = max(w, 0.05) # 最小宽度
        w = min(w, max_width_ratio) # 最大宽度
        final_widths.append(w)
        
    # 重新归一化，确保总和为 1
    total_final = sum(final_widths)
    final_widths = [w / total_final for w in final_widths]
    
    return final_widths

def save_table_as_png(filename, output_filename, col_widths=None, drop_cols=None, extra_width_factor=1.0, truncate_text=True):
    """读取CSV并保存为PNG表格（无标题，自适应列宽）"""
    filepath = os.path.join(INPUT_DIR, filename)
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print("警告：未找到文件 {0}，跳过。".format(filename))
        return

    # 删除指定的列
    if drop_cols is not None:
        # 处理列索引（从0开始）
        if isinstance(drop_cols[0], int):
            cols_to_drop = [df.columns[i] for i in drop_cols]
            df = df.drop(columns=cols_to_drop)
        # 处理列名
        else:
            df = df.drop(columns=drop_cols)

    # 计算合适的图形大小
    n_rows = len(df)
    n_cols = len(df.columns)
    
    # 基础高度 + 每行高度
    fig_height = 1.0 + n_rows * 0.25
    # 基础宽度 + 每列宽度 (稍微放宽一点宽度以容纳文本)
    # 使用extra_width_factor来增加整体宽度
    fig_width = (1.0 + n_cols * 1.5) * extra_width_factor
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('tight')
    ax.axis('off')

    # 准备表格数据
    cell_text = []
    for i in range(n_rows):
        row = []
        for col in df.columns:
            # 截断过长的文本，防止表格撑爆
            val = str(df.iloc[i][col])
            # 只有当truncate_text为True时才截断文本
            if truncate_text and len(val) > 50:
                val = val[:47] + "..."
            row.append(val)
        cell_text.append(row)

    # 绘制表格
    # 如果没有指定列宽，则根据内容自动计算
    if col_widths is None:
        col_widths = calculate_column_widths(df)
    else:
        # 确保列宽数量与列数匹配
        if len(col_widths) != n_cols:
            print(f"警告：指定的列宽数量({len(col_widths)})与表格列数({n_cols})不匹配，将使用自动计算。")
            col_widths = calculate_column_widths(df)

    table = ax.table(cellText=cell_text,
                     colLabels=df.columns,
                     cellLoc='left',
                     loc='center',
                     colWidths=col_widths)
    
    table.auto_set_font_size(False)
    table.set_fontsize(6) # 表格内容字体大小
    table.scale(1, 1.2) # 稍微拉伸行高

    # 设置表头样式
    for i in range(n_cols):
        table[(0, i)].set_facecolor('#EAEAEA')
        table[(0, i)].set_text_props(weight='bold')

    # 保存
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    plt.savefig(output_path, format='png', dpi=300, bbox_inches='tight')
    print("均保存表格图片: {0}".format(output_path))
    plt.close(fig)

# ==========================================
# 绘制 4 个表格
# ==========================================
print("\n正在将 Supplementary Tables 渲染为 PNG...")

# Table 1: Full Parameter List
save_table_as_png(
    'SuppTable1_FullParameterList.csv', 
    'SuppTable1_FullParameterList.png'
)

# Table 2: Cluster Examples - 只保留第0、2、4列
save_table_as_png(
    'SuppTable2_ClusterExamples.csv', 
    'SuppTable2_ClusterExamples.png',
    col_widths=[0.1, 0.2, 0.7],  # 第一列15%，第二列35%，第三列50%
    drop_cols=[1, 3, 5]  # 删除第1、3、5列（索引从0开始），保留第0、2、4列
)

# Table 3: Domain Assignment Schema - 只保留第0、3、4列
save_table_as_png(
    'SuppTable3_DomainAssignmentSchema.csv', 
    'SuppTable3_DomainAssignmentSchema.png',
    col_widths=[0.23, 0.46, 0.31],  # 各列列宽占比
    drop_cols=[1, 2]  # 删除第1列和第2列（索引从0开始），保留第0、3、4列
)

# Table 4: Strategic Matrix Summary
save_table_as_png(
    'SuppTable4_Strategic_Matrix_Summary.csv', 
    'SuppTable4_Strategic_Matrix_Summary.png'
)

print("\n=== 表格渲染完成 ===")
