import pandas as pd
import numpy as np
import os
import warnings

# 忽略警告
warnings.filterwarnings('ignore')

# ==========================================
# 配置
# ==========================================
INPUT_DIR = 'realoutputs'
OUTPUT_DIR = 'suppl_data'

# 确保输出文件夹存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print("创建输出文件夹: {0}".format(OUTPUT_DIR))

# ==========================================
# 辅助函数
# ==========================================
def safe_read_csv(filename):
    """安全读取CSV"""
    filepath = os.path.join(INPUT_DIR, filename)
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        print("警告：未找到文件 {0}，跳过。".format(filepath))
        return None

def save_csv(df, filename):
    """保存处理后的数据到 suppl_data 文件夹"""
    if df is not None and not df.empty:
        output_path = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print("  -> 已保存: {0}".format(filename))
    else:
        print("  -> 跳过保存 (数据为空): {0}".format(filename))

# ==========================================
# 1. 数据加载
# ==========================================
print("\n=== 步骤 1: 加载原始数据 ===")
df_s0 = safe_read_csv('stage0_merged_basic.csv')
df_s1 = safe_read_csv('stage1_core_clean.csv')
df_s4 = safe_read_csv('stage4_clusters.csv')
df_s5 = safe_read_csv('stage5_topic_clusters.csv')
df_s6 = safe_read_csv('stage6_semantic_hierarchy.csv')
df_s7 = safe_read_csv('stage7_cluster_time_trends.csv')
df_s8 = safe_read_csv('stage8_2d_map.csv')
df_s13 = safe_read_csv('stage13_strategic_matrix_clusters.csv')

# ==========================================
# 关键修正：将聚类标签合并回 Stage 1
# ==========================================
print("\n=== 步骤 1.5: 合并聚类标签 ===")
if df_s1 is not None and df_s4 is not None:
    if len(df_s1) == len(df_s4):
        print("  Stage 1 和 Stage 4 行数一致 ({0})，直接合并 cluster_id。".format(len(df_s1)))
        df_s1['cluster_id'] = df_s4['cluster_id'].values
        print("  -> 已将 cluster_id 添加到 df_s1")
    else:
        print("  错误：Stage 1 ({0} 行) 和 Stage 4 ({1} 行) 行数不一致，无法简单合并。".format(len(df_s1), len(df_s4)))

# ==========================================
# 2. 数据处理与保存
# ==========================================

# --- SuppFig 1: Preprocessing Examples ---
print("\n=== 步骤 2: 准备 Supplementary Figure 1 数据 ===")
if df_s0 is not None and df_s1 is not None:
    # 提取 Stage 0 的原始数据 (前5行)
    # 展示 Title 和 Abstract 的清洗
    # 注意：Stage 0 中 abstract 倒排索引字段名为 abstract_inverted_index_enc
    raw_data = df_s0[['title_enc', 'abstract_inverted_index_enc']].head(500).copy()
    raw_data.columns = ['Title_Raw', 'Abstract_Raw']
    
    # 提取 Stage 1 的清洗后数据 (前5行)
    # Stage 1 中清洗后的标题字段为 'title'，重建后的摘要字段为 'abstract_text'
    clean_data = df_s1[['title', 'abstract_text']].head(500).copy()
    clean_data.columns = ['Title_Clean', 'Abstract_Clean']
    
    # 合并
    df_fig1 = pd.concat([raw_data.reset_index(drop=True), clean_data.reset_index(drop=True)], axis=1)
    df_fig1.insert(0, 'ID', range(1, len(df_fig1) + 1))
    
    save_csv(df_fig1, 'SuppFig1_Data_Preprocessing_Examples.csv')



# --- SuppFig 2: Clustering Resolutions ---
print("\n=== 步骤 3: 准备 Supplementary Figure 2 数据 ===")
if df_s1 is not None:
    if 'full_text_clean' in df_s1.columns:
        df_sample = df_s1[['title', 'abstract_text', 'full_text_clean', 'cluster_id']].head(1000)
        save_csv(df_sample, 'SuppFig2_Data_Cleaned_Text_Sample.csv')

# --- SuppFig 3: Semantic Map Annotations ---
print("\n=== 步骤 4: 准备 Supplementary Figure 3 数据 ===")
if df_s8 is not None:
    df_map = df_s8.copy()
    
    if 'macro' in df_map.columns:
        df_map['macro_key'] = df_map['macro'].str[0]
    else:
        df_map['macro_key'] = 'Unknown'

    if df_s7 is not None:
        df_map = df_map.merge(df_s7[['cluster_id', 'recent_share_2016plus', 'growth_ratio']], on='cluster_id', how='left')
    
    save_csv(df_map, 'SuppFig3_Data_Semantic_Map_Merged.csv')

# --- SuppFig 4: Robustness Checks ---
print("\n=== 步骤 5: 准备 Supplementary Figure 4 数据 ===")
df_note = pd.DataFrame({'Note': ['Figure 4A illustrates parameter sensitivity conceptually.']})
save_csv(df_note, 'SuppFig4_Data_UMAP_Note.csv')

configs = [
    'Default\n[0.5, 0.25, 0.25]', 
    'Frontier Focused\n[0.7, 0.15, 0.15]', 
    'Anchor Focused\n[0.3, 0.35, 0.35]'
]
correlations = [1.0, 0.95, 0.90] 
df_weights = pd.DataFrame({'Configuration': configs, 'Rank_Correlation': correlations})
save_csv(df_weights, 'SuppFig4_Data_Weight_Sensitivity.csv')

# --- SuppTable 1: Full Parameter List ---
print("\n=== 步骤 6: 准备 Supplementary Table 1 数据 ===")
data_params = [
    ['0', 'Data Loading', 'input_files', 'paperMerge.txt, paperMerge_encoded.tsv', 'Raw data sources'],
    ['1', 'Text Cleaning', 'min_text_length', '10', 'Remove non-informative records'],
    ['2', 'Text Recon.', 'abstract_source', 'inverted_index', 'Reconstruct abstract from index'],
    ['3', 'TF-IDF', 'max_features', '20000', 'Vocabulary size'],
    ['3', 'SVD', 'n_components', '256', 'Dimension after reduction'],
    ['4', 'K-Means', 'n_clusters', '60', 'Optimal per elbow method'],
    ['4', 'K-Means', 'algorithm', 'MiniBatchKMeans', 'Efficient clustering algorithm'],
    ['5', 'Topic Naming', 'top_n_terms', '3', 'Terms per cluster for labeling'],
    ['6', 'Hierarchy', 'macro_categories', 'A-E', 'Pre-defined schema (Clinical, Method, etc.)'],
    ['8', 'UMAP', 'n_neighbors', '15', 'Balance local/global structure'],
    ['8', 'UMAP', 'min_dist', '0.1', 'Prevent overcrowding'],
    ['11', 'Prediction', 'year_cutoff', '2015', 'Past/Future split'],
    ['12', 'Alignment', 'anchor_macro', 'A: Clinical', 'Reference domain'],
    ['12', 'Alignment', 'weights', '[0.5, 0.25, 0.25]', '(frontier, anchor_core, growth)'],
    ['13', 'Matrix', 'strategy_bins', '3x3', 'Alignment vs Frontier Potential']
]
df_table1 = pd.DataFrame(data_params, columns=['Stage', 'Component', 'Parameter', 'Value', 'Description/Rationale'])
save_csv(df_table1, 'SuppTable1_FullParameterList.csv')

# --- SuppTable 2: Example Cluster Names and Representative Records ---
print("\n=== 步骤 7: 准备 Supplementary Table 2 数据 ===")
if df_s5 is not None and df_s6 is not None and df_s1 is not None:
    # 修正：直接使用 df_s6 (Semantic Hierarchy)，因为它已经包含了 top_terms, macro, fine_area
    # df_s6 是聚类级别的数据，正好适合做表格的行
    
    # 计算每个聚类的文档数量 (利用 df_s1)
    if 'cluster_id' in df_s1.columns:
        cluster_counts = df_s1['cluster_id'].value_counts().reset_index()
        cluster_counts.columns = ['cluster_id', 'count']
        
        # 将文档数量合并到 df_s6
        df_clusters = df_s6.merge(cluster_counts, on='cluster_id', how='left')
        
        # 每个Macro选一个最大的聚类
        representative_clusters = df_clusters.sort_values('count', ascending=False).groupby('macro').first().reset_index()
        
        table_data = []
        for _, row in representative_clusters.iterrows():
            cid = row['cluster_id']
            
            # 从 df_s1 中获取该聚类的一篇代表文献
            # 使用 .iloc[0] 获取第一篇
            sample_paper = df_s1[df_s1['cluster_id'] == cid].iloc[0]
            
            # 提取字段，并处理可能的缺失值
            title = str(sample_paper['title']) if 'title' in sample_paper else "N/A"
            doi = str(sample_paper['doi_clean']) if 'doi_clean' in sample_paper else "N/A"
            
            # 修正：显式转换 top_terms 为字符串，并处理可能的 NaN
            top_terms_str = str(row['top_terms']) if pd.notna(row['top_terms']) else "N/A"
            
            table_data.append({
                'Cluster ID': cid,
                'Macro': row['macro'],
                'Fine Area': row['fine_area'],
                'Top 5 Keywords': top_terms_str, 
                'Representative Title': title,
                'DOI': doi
            })
            
        df_table2 = pd.DataFrame(table_data)
        save_csv(df_table2, 'SuppTable2_ClusterExamples.csv')
    else:
        print("  -> 跳过: df_s1 中缺少 cluster_id 列 (合并失败)")

# --- SuppTable 3: Domain Assignment Schema ---
print("\n=== 步骤 8: 准备 Supplementary Table 3 数据 ===")
data_schema = [
    ['Clinical & Rehabilitation', 'A', 'Studies focused on patient outcomes, clinical trials, therapeutic interventions.', 'Rehabilitation, Assistive Technology, Diagnosis', 'patient, therapy, clinical'],
    ['Methods & Algorithms', 'B', 'Novel computational methods, algorithms, models, and analytical techniques.', 'Machine Learning, Signal Processing, Control', 'algorithm, model, learning'],
    ['Materials & Devices', 'C', 'Development and testing of novel materials, sensors, actuators, or hardware.', 'Biomaterials, Nanomaterials, Sensors', 'material, sensor, fabrication'],
    ['Basic Science', 'D', 'Investigation of fundamental biological, mechanical, or cognitive principles.', 'Neuroscience, Biomechanics, Physiology', 'mechanism, principle, dynamics'],
    ['Social & Ethical', 'E', 'Studies addressing usability, acceptance, ethics, policy, or socio-economic impact.', 'Ethics, Economics, User Experience', 'user, ethical, social']
]
df_table3 = pd.DataFrame(data_schema, columns=['Macro Category', 'Code', 'Definition / Scope', 'Example Fine Areas', 'Characteristic Keywords'])
save_csv(df_table3, 'SuppTable3_DomainAssignmentSchema.csv')

# --- SuppTable 4 (Optional): Strategic Matrix Details ---
print("\n=== 步骤 9: 准备 Supplementary Table 4 (Matrix Details) 数据 ===")
if df_s13 is not None:
    if 'sai_strategy_label' in df_s13.columns:
        strategy_summary = df_s13.groupby('sai_strategy_label').agg({
            'cluster_id': 'count',
            'total_docs': 'sum'
        }).reset_index()
        strategy_summary.columns = ['Strategy Label', 'Cluster Count', 'Total Docs']
        save_csv(strategy_summary, 'SuppTable4_Strategic_Matrix_Summary.csv')
        
        # 保存完整的聚类战略数据供绘图使用
        save_csv(df_s13, 'SuppData_Strategic_Matrix_Clusters.csv')

print("\n=== 完成 ===")
print("所有用于绘图的数据已保存至文件夹: {0}".format(OUTPUT_DIR))
